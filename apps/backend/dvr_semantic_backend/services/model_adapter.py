"""Multimodal model adapter for dashcam frame analysis.

Provides a uniform interface over:
- MockAdapter: deterministic, filename/hash based, no network.
- OpenAICompatibleAdapter: serves both DeepSeek-VL and Qwen-VL through the
  OpenAI-compatible /v1/chat/completions multimodal protocol.

The adapter only converts a frame image into a structured FrameLabel.
It does NOT touch the database; the caller decides what to persist.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Protocol

from . import retry

logger = logging.getLogger(__name__)

# The five business event categories plus "normal".
EVENT_TYPES: tuple[str, ...] = (
    "scratch",
    "illegal_parking",
    "road_obstacle",
    "abnormal_stop",
    "pedestrian_risk",
    "normal",
)
_VALID_EVENTS = frozenset(EVENT_TYPES)

# Mapping from event_type -> a small bag of canonical Chinese tags / objects
# used by MockAdapter to emit reasonable looking labels.
_MOCK_PROFILES: dict[str, dict[str, tuple[str, ...]]] = {
    "scratch": {
        "tags": ("剐蹭", "车身刮擦", "右侧接触"),
        "objects": ("白色轿车", "黑色SUV"),
        "summary": "画面中出现疑似车身剐蹭，右侧车辆距离过近。",
    },
    "illegal_parking": {
        "tags": ("违停", "占道停车", "黄线"),
        "objects": ("路侧轿车", "禁停标志"),
        "summary": "前方车道边出现违章停放车辆，占用通行车道。",
    },
    "road_obstacle": {
        "tags": ("道路障碍", "落物", "锥桶"),
        "objects": ("锥桶", "纸箱"),
        "summary": "前方车道存在道路障碍物，需注意避让。",
    },
    "abnormal_stop": {
        "tags": ("急刹", "异常停车", "刹车灯"),
        "objects": ("前车", "刹车灯"),
        "summary": "前车出现疑似急刹或异常停车，建议保持车距。",
    },
    "pedestrian_risk": {
        "tags": ("行人风险", "横穿马路", "鬼探头"),
        "objects": ("行人", "电动车"),
        "summary": "画面中行人靠近车道，存在潜在碰撞风险。",
    },
    "normal": {
        "tags": ("正常行驶",),
        "objects": ("前车",),
        "summary": "画面正常，未检测到风险事件。",
    },
}

# Keyword -> forced event_type for MockAdapter filename hints.
_KEYWORD_MAP: tuple[tuple[str, str], ...] = (
    ("scratch", "scratch"),
    ("剐蹭", "scratch"),
    ("parking", "illegal_parking"),
    ("violation", "illegal_parking"),
    ("违停", "illegal_parking"),
    ("obstacle", "road_obstacle"),
    ("障碍", "road_obstacle"),
    ("stop", "abnormal_stop"),
    ("brake", "abnormal_stop"),
    ("急刹", "abnormal_stop"),
    ("pedestrian", "pedestrian_risk"),
    ("行人", "pedestrian_risk"),
)


@dataclass(frozen=True)
class FrameLabel:
    event_type: str            # one of EVENT_TYPES
    tags: tuple[str, ...]      # Chinese tag strings
    summary: str               # 1-2 sentence Chinese description
    objects: tuple[str, ...]   # detected object names
    confidence: float          # 0.0 - 1.0
    anomaly: bool              # whether this looks like a real event
    provider: str              # mock | deepseek | qwen
    raw: dict = field(default_factory=dict)  # raw provider response for debug


class ModelAdapter(Protocol):
    name: str

    def analyze_frame(self, image_path: Path, hint: str = "") -> FrameLabel:
        ...


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------


class MockAdapter:
    """Deterministic rule-based labeler.

    Strategy:
    * If the filename contains an event keyword, force that event_type.
    * Otherwise hash (filename + hint) to pick from EVENT_TYPES.
      ~60% of frames fall back to "normal", ~40% spread across the five
      business events.
    """

    name = "mock"

    def analyze_frame(self, image_path: Path, hint: str = "") -> FrameLabel:
        key = f"{image_path.name}|{hint}"
        forced = self._match_keyword(image_path.name)
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        # Deterministic RNG seeded by the digest so repeated calls are stable.
        rng = random.Random(int.from_bytes(digest[:8], "big"))

        if forced is not None:
            event_type = forced
        else:
            # bucket 0..9; 0..5 -> normal, 6..9 -> the five business events.
            bucket = digest[0] % 10
            if bucket < 6:
                event_type = "normal"
            else:
                event_type = EVENT_TYPES[bucket - 6]  # indices 0..4

        profile = _MOCK_PROFILES[event_type]
        anomaly = event_type != "normal"
        confidence = (
            round(0.55 + rng.random() * 0.4, 3)
            if anomaly
            else round(0.6 + rng.random() * 0.3, 3)
        )

        return FrameLabel(
            event_type=event_type,
            tags=tuple(profile["tags"]),
            summary=profile["summary"],
            objects=tuple(profile["objects"]),
            confidence=confidence,
            anomaly=anomaly,
            provider=self.name,
            raw={
                "source": "mock",
                "image": str(image_path),
                "hint": hint,
                "bucket": digest[0] % 10,
            },
        )

    @staticmethod
    def _match_keyword(name: str) -> str | None:
        lowered = name.lower()
        for keyword, event in _KEYWORD_MAP:
            if keyword in lowered or keyword in name:
                return event
        return None


# ---------------------------------------------------------------------------
# OpenAI-compatible adapter (DeepSeek-VL / Qwen-VL)
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT = (
    "你是一个行车记录仪画面分析助手。请判断该画面是否包含以下事件之一："
    "剐蹭/碰撞、违停、道路障碍、异常停车或急刹、行人风险。"
    "严格用 JSON 返回 "
    '{"event_type": "scratch|illegal_parking|road_obstacle|abnormal_stop|pedestrian_risk|normal", '
    '"tags": ["..."], "summary": "...", "objects": ["..."], '
    '"confidence": 0.0-1.0, "anomaly": true|false}。'
    "不要添加任何 JSON 之外的内容。"
)

_USER_PROMPT_TEMPLATE = (
    "请分析这一帧画面。补充提示（可能为空）：{hint}。"
    "只返回符合 schema 的 JSON。"
)

_DEFAULT_TIMEOUT = 15.0

# Map image suffix -> mime type for base64 data URLs.
_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


class OpenAICompatibleAdapter:
    """Adapter for OpenAI-compatible vision endpoints (DeepSeek-VL, Qwen-VL)."""

    def __init__(
        self,
        provider: str,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.name = provider
        self._base_url = base_url
        self._api_key = api_key
        self._model_name = model_name
        self._timeout = timeout
        self._client: Any = None  # lazy-initialised
        self._lock = Lock()
        # Auto-retry transient model API failures before falling back (NFR-02).
        self._max_retries = retry.default_attempts()
        self._retry_base_delay = retry.default_base_delay()

    # -- public API ------------------------------------------------------

    def analyze_frame(self, image_path: Path, hint: str = "") -> FrameLabel:
        try:
            data_url = self._encode_image(image_path)
        except OSError as exc:
            logger.warning("model_adapter: failed to read %s: %s", image_path, exc)
            return self._fallback_label({"error": f"read_failed: {exc}"})

        try:
            client = self._get_client()
        except Exception as exc:  # pragma: no cover - depends on env
            logger.warning("model_adapter: client init failed: %s", exc)
            return self._fallback_label({"error": f"client_init_failed: {exc}"})

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _USER_PROMPT_TEMPLATE.format(hint=hint or "无")},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]

        try:
            response = retry.call_with_retry(
                lambda: client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    timeout=self._timeout,
                ),
                attempts=self._max_retries,
                base_delay=self._retry_base_delay,
            )
        except Exception as exc:
            logger.warning("model_adapter: request failed after retries: %s", exc)
            return self._fallback_label({"error": f"request_failed: {exc}"})

        content = self._extract_content(response)
        parsed = self._parse_json(content)
        if parsed is None:
            return self._fallback_label({"error": "json_parse_failed", "content": content})

        return self._coerce_label(parsed, raw_content=content)

    # -- helpers ---------------------------------------------------------

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        with self._lock:
            if self._client is None:
                # Import lazily so the module is usable without openai installed
                # as long as the OpenAI adapter is never instantiated->called.
                from openai import OpenAI

                kwargs: dict[str, Any] = {"api_key": self._api_key}
                if self._base_url:
                    kwargs["base_url"] = self._base_url
                self._client = OpenAI(**kwargs)
        return self._client

    @staticmethod
    def _encode_image(image_path: Path) -> str:
        mime = _MIME_MAP.get(image_path.suffix.lower(), "image/jpeg")
        with image_path.open("rb") as fh:
            payload = base64.b64encode(fh.read()).decode("ascii")
        return f"data:{mime};base64,{payload}"

    @staticmethod
    def _extract_content(response: Any) -> str:
        try:
            choice = response.choices[0]
            message = choice.message
            content = getattr(message, "content", None)
            if isinstance(content, list):
                # some providers send a list of parts
                parts = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        parts.append(item["text"])
                    elif hasattr(item, "text"):
                        parts.append(item.text)
                return "".join(parts)
            return content or ""
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("model_adapter: malformed response: %s", exc)
            return ""

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any] | None:
        if not content:
            return None
        text = content.strip()
        # Strip common ```json fences.
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            # try to grab the first {...} block
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                return None
            try:
                obj = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return obj if isinstance(obj, dict) else None

    def _coerce_label(self, data: dict[str, Any], raw_content: str) -> FrameLabel:
        event_type = str(data.get("event_type") or "normal").strip()
        if event_type not in _VALID_EVENTS:
            event_type = "normal"

        tags = _to_str_tuple(data.get("tags"))
        objects = _to_str_tuple(data.get("objects"))
        summary = str(data.get("summary") or "").strip()
        try:
            confidence = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        anomaly = bool(data.get("anomaly", event_type != "normal"))

        return FrameLabel(
            event_type=event_type,
            tags=tags,
            summary=summary,
            objects=objects,
            confidence=confidence,
            anomaly=anomaly,
            provider=self.name,
            raw={"parsed": data, "content": raw_content},
        )

    def _fallback_label(self, raw: dict[str, Any]) -> FrameLabel:
        return FrameLabel(
            event_type="normal",
            tags=(),
            summary="",
            objects=(),
            confidence=0.0,
            anomaly=False,
            provider=self.name,
            raw=raw,
        )


def _to_str_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    return ()


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------


_ADAPTER_SINGLETON: ModelAdapter | None = None
_SINGLETON_LOCK = Lock()


def get_adapter() -> ModelAdapter:
    """Return a process-wide adapter chosen from environment variables.

    Resolution order:
    * MODEL_PROVIDER unset / "mock" -> MockAdapter
    * provider in {"deepseek", "qwen"} but MODEL_API_KEY empty -> MockAdapter
    * else -> OpenAICompatibleAdapter
    """

    global _ADAPTER_SINGLETON
    if _ADAPTER_SINGLETON is not None:
        return _ADAPTER_SINGLETON

    with _SINGLETON_LOCK:
        if _ADAPTER_SINGLETON is None:
            _ADAPTER_SINGLETON = _build_adapter_from_env()
        return _ADAPTER_SINGLETON


def reset_adapter() -> None:
    """Drop the cached singleton. Mainly used in tests."""

    global _ADAPTER_SINGLETON
    with _SINGLETON_LOCK:
        _ADAPTER_SINGLETON = None


def _build_adapter_from_env() -> ModelAdapter:
    provider = (os.environ.get("MODEL_PROVIDER") or "mock").strip().lower()
    api_key = (os.environ.get("MODEL_API_KEY") or "").strip()
    base_url = (os.environ.get("MODEL_BASE_URL") or "").strip()
    model_name = (os.environ.get("MODEL_NAME") or "").strip()

    if provider in ("", "mock") or not api_key:
        if provider not in ("", "mock"):
            logger.info(
                "model_adapter: provider=%s but MODEL_API_KEY empty; using mock.",
                provider,
            )
        return MockAdapter()

    if provider not in ("deepseek", "qwen"):
        logger.warning(
            "model_adapter: unknown MODEL_PROVIDER=%s; falling back to mock.",
            provider,
        )
        return MockAdapter()

    if not model_name:
        model_name = "qwen-vl-plus" if provider == "qwen" else "deepseek-vl"

    return OpenAICompatibleAdapter(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model_name=model_name,
    )


__all__ = [
    "EVENT_TYPES",
    "FrameLabel",
    "ModelAdapter",
    "MockAdapter",
    "OpenAICompatibleAdapter",
    "get_adapter",
    "reset_adapter",
]

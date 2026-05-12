"""Tests for the multimodal model adapter layer.

The OpenAI-compatible test patches the SDK client so no real network or
API token is consumed.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from dvr_semantic_backend.services.model_adapter import (
    EVENT_TYPES,
    FrameLabel,
    MockAdapter,
    OpenAICompatibleAdapter,
    get_adapter,
    reset_adapter,
)


VALID_EVENTS = frozenset(EVENT_TYPES)


@pytest.fixture
def fake_jpg(tmp_path: Path) -> Path:
    # Minimal placeholder bytes; the adapter only base64-encodes blindly so
    # we don't need a real JPEG.
    path = tmp_path / "drive_segment_01.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0fakejpegbytes\xff\xd9")
    return path


def _assert_valid_label(label: FrameLabel, provider: str) -> None:
    assert isinstance(label, FrameLabel)
    assert label.event_type in VALID_EVENTS
    assert isinstance(label.tags, tuple)
    assert isinstance(label.objects, tuple)
    assert isinstance(label.summary, str)
    assert 0.0 <= label.confidence <= 1.0
    assert isinstance(label.anomaly, bool)
    assert label.provider == provider
    assert isinstance(label.raw, dict)


# ---------------------------------------------------------------------------
# MockAdapter
# ---------------------------------------------------------------------------


class TestMockAdapter:
    def test_returns_valid_label_three_times(self, fake_jpg: Path) -> None:
        adapter = MockAdapter()
        for hint in ("first", "second", "third"):
            label = adapter.analyze_frame(fake_jpg, hint=hint)
            _assert_valid_label(label, provider="mock")

    def test_deterministic_for_same_input(self, fake_jpg: Path) -> None:
        adapter = MockAdapter()
        a = adapter.analyze_frame(fake_jpg, hint="x")
        b = adapter.analyze_frame(fake_jpg, hint="x")
        assert a == b

    def test_keyword_forces_event_type(self, tmp_path: Path) -> None:
        adapter = MockAdapter()
        cases = {
            "clip_scratch_001.jpg": "scratch",
            "front_pedestrian_22.jpg": "pedestrian_risk",
            "illegal_parking_xy.jpg": "illegal_parking",
            "road_obstacle_5.jpg": "road_obstacle",
            "sudden_brake_now.jpg": "abnormal_stop",
        }
        for name, expected in cases.items():
            path = tmp_path / name
            path.write_bytes(b"x")
            label = adapter.analyze_frame(path)
            assert label.event_type == expected, name
            assert label.anomaly is True

    def test_neutral_filename_can_yield_normal(self, tmp_path: Path) -> None:
        adapter = MockAdapter()
        seen = set()
        for i in range(50):
            path = tmp_path / f"frame_{i:04d}.jpg"
            path.write_bytes(b"x")
            label = adapter.analyze_frame(path)
            seen.add(label.event_type)
        # Mock distribution should produce both normal and at least one event.
        assert "normal" in seen
        assert seen - {"normal"}, "expected at least one event_type besides normal"


# ---------------------------------------------------------------------------
# OpenAICompatibleAdapter (mocked)
# ---------------------------------------------------------------------------


def _make_response(content: str) -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


class TestOpenAICompatibleAdapter:
    def test_parses_json_response(self, fake_jpg: Path) -> None:
        payload = {
            "event_type": "scratch",
            "tags": ["剐蹭", "右侧车辆"],
            "summary": "画面中疑似车身剐蹭。",
            "objects": ["白色轿车"],
            "confidence": 0.82,
            "anomaly": True,
        }
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = _make_response(
            json.dumps(payload, ensure_ascii=False)
        )

        with patch("openai.OpenAI", return_value=fake_client) as openai_ctor:
            adapter = OpenAICompatibleAdapter(
                provider="qwen",
                base_url="https://example.invalid/v1",
                api_key="test-key",
                model_name="qwen-vl-plus",
            )
            label = adapter.analyze_frame(fake_jpg, hint="测试")

        openai_ctor.assert_called_once()
        fake_client.chat.completions.create.assert_called_once()
        call_kwargs = fake_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "qwen-vl-plus"
        assert call_kwargs["timeout"] == 15.0
        # image must be passed as a data URL in the user message
        user_msg = call_kwargs["messages"][1]
        image_part = user_msg["content"][1]
        assert image_part["type"] == "image_url"
        assert image_part["image_url"]["url"].startswith("data:image/jpeg;base64,")

        _assert_valid_label(label, provider="qwen")
        assert label.event_type == "scratch"
        assert label.tags == ("剐蹭", "右侧车辆")
        assert label.objects == ("白色轿车",)
        assert label.confidence == pytest.approx(0.82)
        assert label.anomaly is True

    def test_strips_markdown_fences(self, fake_jpg: Path) -> None:
        payload = {
            "event_type": "pedestrian_risk",
            "tags": ["行人"],
            "summary": "行人靠近车道。",
            "objects": ["行人"],
            "confidence": 0.91,
            "anomaly": True,
        }
        fenced = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = _make_response(fenced)

        with patch("openai.OpenAI", return_value=fake_client):
            adapter = OpenAICompatibleAdapter(
                provider="deepseek",
                base_url="https://example.invalid/v1",
                api_key="k",
                model_name="deepseek-vl",
            )
            label = adapter.analyze_frame(fake_jpg)
        assert label.event_type == "pedestrian_risk"
        assert label.provider == "deepseek"

    def test_invalid_event_type_coerced_to_normal(self, fake_jpg: Path) -> None:
        payload = {
            "event_type": "ufo_sighting",
            "tags": [],
            "summary": "",
            "objects": [],
            "confidence": 0.3,
            "anomaly": False,
        }
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = _make_response(
            json.dumps(payload)
        )

        with patch("openai.OpenAI", return_value=fake_client):
            adapter = OpenAICompatibleAdapter(
                provider="qwen",
                base_url="",
                api_key="k",
                model_name="qwen-vl-plus",
            )
            label = adapter.analyze_frame(fake_jpg)
        assert label.event_type == "normal"

    def test_request_failure_falls_back_without_raising(self, fake_jpg: Path) -> None:
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = RuntimeError("boom")

        with patch("openai.OpenAI", return_value=fake_client):
            adapter = OpenAICompatibleAdapter(
                provider="qwen",
                base_url="",
                api_key="k",
                model_name="qwen-vl-plus",
            )
            label = adapter.analyze_frame(fake_jpg)
        assert label.event_type == "normal"
        assert label.confidence == 0.0
        assert "request_failed" in label.raw.get("error", "")

    def test_garbage_response_falls_back(self, fake_jpg: Path) -> None:
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = _make_response("hello world")

        with patch("openai.OpenAI", return_value=fake_client):
            adapter = OpenAICompatibleAdapter(
                provider="qwen",
                base_url="",
                api_key="k",
                model_name="qwen-vl-plus",
            )
            label = adapter.analyze_frame(fake_jpg)
        assert label.event_type == "normal"
        assert label.confidence == 0.0


# ---------------------------------------------------------------------------
# get_adapter() environment routing
# ---------------------------------------------------------------------------


class TestGetAdapter:
    def setup_method(self) -> None:
        reset_adapter()

    def teardown_method(self) -> None:
        reset_adapter()

    def test_defaults_to_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MODEL_PROVIDER", raising=False)
        monkeypatch.delenv("MODEL_API_KEY", raising=False)
        adapter = get_adapter()
        assert isinstance(adapter, MockAdapter)

    def test_empty_api_key_falls_back_to_mock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL_PROVIDER", "qwen")
        monkeypatch.setenv("MODEL_API_KEY", "")
        adapter = get_adapter()
        assert isinstance(adapter, MockAdapter)

    def test_qwen_with_key_picks_openai_adapter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL_PROVIDER", "qwen")
        monkeypatch.setenv("MODEL_API_KEY", "sk-fake")
        monkeypatch.setenv("MODEL_BASE_URL", "https://example.invalid/v1")
        monkeypatch.setenv("MODEL_NAME", "qwen-vl-plus")
        adapter = get_adapter()
        assert isinstance(adapter, OpenAICompatibleAdapter)
        assert adapter.name == "qwen"

    def test_singleton_is_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MODEL_PROVIDER", raising=False)
        a = get_adapter()
        b = get_adapter()
        assert a is b

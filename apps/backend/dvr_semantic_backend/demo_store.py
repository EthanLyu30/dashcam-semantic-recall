from __future__ import annotations


DEMO_VIDEOS: list[dict[str, object]] = [
    {
        "id": "vid-20260327-1422",
        "title": "VID_20260327_1422 南山区巡查",
        "duration_sec": 1830,
        "status": "searchable",
        "thumbnail_url": "",
        "source_path": "",
    },
    {
        "id": "vid-20260328-0908",
        "title": "VID_20260328_0908 滨河大道早高峰",
        "duration_sec": 2160,
        "status": "searchable",
        "thumbnail_url": "",
        "source_path": "",
    },
]


DEMO_EVENTS: list[dict[str, object]] = [
    {
        "id": "evt-scratch-001",
        "video_id": "vid-20260327-1422",
        "event_type": "scratch",
        "title": "疑似侧向剐蹭",
        "summary": "右侧车辆贴近并出现急促制动，建议人工复核车身侧面画面。",
        "start_sec": 342,
        "end_sec": 361,
        "confidence": 0.88,
        "tags": ["剐蹭", "急刹", "右侧车辆"],
        "thumbnail_url": "",
        "review_status": "pending",
    },
    {
        "id": "evt-parking-002",
        "video_id": "vid-20260327-1422",
        "event_type": "illegal_parking",
        "title": "非机动车道违停车辆",
        "summary": "白色轿车停靠在非机动车道边缘，后方车辆出现绕行。",
        "start_sec": 716,
        "end_sec": 752,
        "confidence": 0.82,
        "tags": ["违停", "白色轿车", "绕行"],
        "thumbnail_url": "",
        "review_status": "pending",
    },
    {
        "id": "evt-obstacle-003",
        "video_id": "vid-20260327-1422",
        "event_type": "road_obstacle",
        "title": "施工围挡占道",
        "summary": "右前方出现临时施工围挡，占用部分车道并影响车辆通行。",
        "start_sec": 1038,
        "end_sec": 1084,
        "confidence": 0.79,
        "tags": ["道路障碍", "施工", "围挡"],
        "thumbnail_url": "",
        "review_status": "reviewing",
    },
    {
        "id": "evt-stop-004",
        "video_id": "vid-20260328-0908",
        "event_type": "abnormal_stop",
        "title": "异常停车与连续鸣笛",
        "summary": "前车在无明显红灯情况下短暂停车，后车出现连续鸣笛与变道。",
        "start_sec": 128,
        "end_sec": 154,
        "confidence": 0.74,
        "tags": ["异常停车", "鸣笛", "变道"],
        "thumbnail_url": "",
        "review_status": "reviewing",
    },
    {
        "id": "evt-pedestrian-005",
        "video_id": "vid-20260328-0908",
        "event_type": "pedestrian_risk",
        "title": "行人横穿导致急刹",
        "summary": "行人从车辆右侧快速横穿，车辆明显减速并停顿。",
        "start_sec": 934,
        "end_sec": 958,
        "confidence": 0.91,
        "tags": ["行人", "急刹", "风险"],
        "thumbnail_url": "",
        "review_status": "pending",
    },
]


def get_event(event_id: str) -> dict[str, object] | None:
    return next((event for event in DEMO_EVENTS if event["id"] == event_id), None)


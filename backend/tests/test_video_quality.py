import base64
import json

from app.services.video_quality import pick_best_play_url


def test_selects_highest_resolution_item() -> None:
    payload = {
        "video_list": [
            {"definition": "480p", "main_url": "https://media.example/480.mp4"},
            {
                "definition": "1080p",
                "main_url": "https://media.example/1080.mp4",
                "video_meta": {"width": 1920, "height": 1080},
            },
            {"definition": "720p", "main_url": "https://media.example/720.mp4"},
        ]
    }

    url, metadata = pick_best_play_url(payload)

    assert url == "https://media.example/1080.mp4"
    assert metadata["from"] == "video_list"
    assert metadata["height"] == 1080


def test_decodes_base64_video_model() -> None:
    inner = {"play_addr": [{"quality": "720p", "url": "https://media.example/a.mp4"}]}
    payload = {"video_model": base64.b64encode(json.dumps(inner).encode()).decode()}

    url, metadata = pick_best_play_url(payload)

    assert url == "https://media.example/a.mp4"
    assert metadata["from"] == "play_addr"


def test_ignores_invalid_candidates_and_falls_back_to_direct_url() -> None:
    payload = {
        "video_list": [None, "not-a-mapping", {"main_url": "file:///tmp/video.mp4"}],
        "main_url": "https://media.example/direct.mp4",
    }

    assert pick_best_play_url(payload) == (
        "https://media.example/direct.mp4",
        {"from": "main_url"},
    )


def test_malformed_video_model_does_not_raise() -> None:
    assert pick_best_play_url({"video_model": "%%%"}) == (None, {})

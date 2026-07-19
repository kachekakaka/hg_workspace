import json

import pytest

from app.sources.novelquick import (
    EpisodeSeed,
    SourceParseError,
    episodes_from_detail,
    player_info_from_html,
    player_page_url,
    series_detail_from_html,
)


def _html(payload: dict) -> str:
    return f"<html><script>window._ROUTER_DATA = {json.dumps(payload)};</script></html>"


def test_extracts_series_detail_and_normalizes_episodes() -> None:
    payload = {
        "loaderData": {
            "detail_page": {
                "seriesDetail": {
                    "series_id": "series-1",
                    "series_name": "示例作品",
                    "vid_list": [
                        "episode-1",
                        {"video_id": "episode-2", "index": 2, "title": "第二集"},
                        {"item_id": "episode-3", "index": "bad"},
                        " ",
                    ],
                }
            }
        }
    }

    detail = series_detail_from_html(_html(payload))

    assert episodes_from_detail(detail) == [
        EpisodeSeed("episode-1", 1, "第 1 集"),
        EpisodeSeed("episode-2", 2, "第二集"),
        EpisodeSeed("episode-3", 3, "第 3 集"),
    ]


def test_extracts_player_information_without_network_access() -> None:
    payload = {
        "loaderData": {
            "player_page": {
                "video_player_info": {
                    "main_url": "https://media.example/video.mp4",
                    "duration": 42,
                }
            }
        }
    }

    assert player_info_from_html(_html(payload)) == {
        "main_url": "https://media.example/video.mp4",
        "duration": 42,
    }


def test_missing_router_data_has_clear_error() -> None:
    with pytest.raises(SourceParseError, match="window._ROUTER_DATA"):
        series_detail_from_html("<html></html>")


def test_player_url_quotes_path_segments() -> None:
    assert player_page_url("series/a", "episode b").endswith("/series%2Fa/episode%20b")

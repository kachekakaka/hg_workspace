from __future__ import annotations
import json
from urllib.parse import parse_qs, urlsplit
import pytest
from app.sources.novelquick_adapter import (
    NovelQuickSourceAdapter,
    SourceRequestError,
    UrlLibTextFetcher,
)


def html(payload: dict) -> str:
    return f'<html><script>window._ROUTER_DATA = {json.dumps(payload, ensure_ascii=False)};</script></html>'


def homepage_payload() -> dict:
    return {
        "loaderData": {
            "page": {
                "videoList": [
                    {"series_id": "2", "series_name": "二号剧", "episode_cnt": 12, "vid_list": ["secret-media-id"]},
                    {"series_id": "1", "series_name": "一号剧", "series_intro": "短简介", "episode_cnt": 8},
                ],
                "bannerList": [{"series_id": "3", "series_name": "三号剧", "episode_cnt": 5}],
                "mBannerList": [],
            }
        }
    }


def category_payload(selected: str = "") -> dict:
    recommendation = [
        {"series_id": "1", "series_name": "一号剧", "series_intro": "更完整的作品简介", "episode_cnt": 8},
        {"series_id": f"c{selected or '0'}", "series_name": f"分类作品{selected or '0'}", "episode_cnt": 3},
    ]
    return {
        "loaderData": {
            "category_page": {
                "recommendList": recommendation,
                "selectorList": [
                    {
                        "row_name": "全部时间",
                        "items": [
                            {"selector_item_id": "7", "show_name": "7天"},
                            {"selector_item_id": "14", "show_name": "14天"},
                            {"selector_item_id": "30", "show_name": "30天"},
                            {"selector_item_id": "90", "show_name": "90天"},
                        ],
                    },
                    {
                        "row_name": "全部推荐",
                        "items": [
                            {"selector_item_id": "new", "show_name": "最新"},
                            {"selector_item_id": "hot", "show_name": "最热"},
                        ],
                    },
                    {
                        "row_name": "全部主题",
                        "items": [
                            {"selector_item_id": "city", "show_name": "都市"},
                        ],
                    },
                ],
            }
        }
    }


class FakeFetcher:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str) -> str:
        self.urls.append(url)
        parsed = urlsplit(url)
        if parsed.path == "/":
            return html(homepage_payload())
        selected = next(iter(parse_qs(parsed.query).values()), [""])[0]
        return html(category_payload(selected))


def test_incremental_discovery_is_bounded_and_strips_media_fields() -> None:
    fetcher = FakeFetcher()
    progress: list[tuple[int, int, str]] = []
    adapter = NovelQuickSourceAdapter(fetch_text=fetcher, delay=0, sleep=lambda _: None)

    result = adapter.discover("incremental", progress=lambda *args: progress.append(args))

    # homepage + default category + 3 time selectors + 1 sort selector
    assert result.request_count == 6
    assert len(fetcher.urls) == 6
    assert not any("topic=" in url for url in fetcher.urls)
    assert not any("sort_type=hot" in url for url in fetcher.urls)
    by_id = {work.source_work_id: work for work in result.works}
    assert by_id["1"].series_intro == "更完整的作品简介"
    assert by_id["2"].episodes is None
    assert by_id["2"].episode_count == 12
    assert all(work.source == "novelquick" for work in result.works)
    assert progress[-1][0] == progress[-1][1] == 6


def test_full_discovery_uses_all_supported_selector_rows() -> None:
    fetcher = FakeFetcher()
    adapter = NovelQuickSourceAdapter(fetch_text=fetcher, delay=0, sleep=lambda _: None)

    result = adapter.discover("full")

    assert result.request_count == 9
    assert any("time=90" in url for url in fetcher.urls)
    assert any("sort_type=hot" in url for url in fetcher.urls)
    assert any("topic=city" in url for url in fetcher.urls)
    assert result.works == sorted(result.works, key=lambda item: item.source_work_id)


def test_discovery_rejects_empty_or_malformed_source() -> None:
    adapter = NovelQuickSourceAdapter(
        fetch_text=lambda _: html({"loaderData": {}}), delay=0, sleep=lambda _: None
    )
    with pytest.raises(SourceRequestError, match="no valid works"):
        adapter.discover("incremental")

    malformed = NovelQuickSourceAdapter(fetch_text=lambda _: "<html></html>", delay=0)
    with pytest.raises(SourceRequestError, match="valid SSR metadata"):
        malformed.discover("full")


def test_network_fetcher_restricts_origin_and_credentials() -> None:
    fetcher = UrlLibTextFetcher(retries=1)
    with pytest.raises(SourceRequestError, match="configured HTTPS origin"):
        fetcher("http://novelquickapp.com/")
    with pytest.raises(SourceRequestError, match="configured HTTPS origin"):
        fetcher("https://example.com/")
    with pytest.raises(SourceRequestError, match="credentials"):
        fetcher("https://user:pass@novelquickapp.com/")

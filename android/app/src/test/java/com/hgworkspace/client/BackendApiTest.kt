package com.hgworkspace.client

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull
import kotlin.test.assertTrue

class BackendApiTest {
    @Test
    fun normalizesPrivateLanAddressWithoutScheme() {
        assertEquals(
            "http://192.168.1.10:8000",
            ServerUrlValidator.normalize("192.168.1.10:8000/"),
        )
    }

    @Test
    fun acceptsHttpsPublicHostAndPathPrefix() {
        assertEquals(
            "https://nas.example/hg",
            ServerUrlValidator.normalize("https://nas.example/hg/"),
        )
    }

    @Test
    fun rejectsUnsafeServerUrls() {
        assertFailsWith<InvalidServerUrlException> {
            ServerUrlValidator.normalize("http://example.com")
        }
        assertFailsWith<InvalidServerUrlException> {
            ServerUrlValidator.normalize("https://user:pass@nas.example")
        }
        assertFailsWith<InvalidServerUrlException> {
            ServerUrlValidator.normalize("https://nas.example?token=value")
        }
        assertFailsWith<InvalidServerUrlException> {
            ServerUrlValidator.normalize("https://nas.example/a/../b")
        }
    }

    @Test
    fun parsesStatusAndLegacyWorksPayload() {
        val status = BackendJsonParser.parseStatus(
            """{"version":"0.7.1","catalog_total":3,"catalog_active":2}"""
        )
        assertEquals("0.7.1", status.version)
        assertEquals(3, status.catalogTotal)
        assertEquals(2, status.catalogActive)

        val works = BackendJsonParser.parseWorks(
            """
            {
              "total": 1,
              "works": [
                {
                  "id": 7,
                  "series_id": "source-7",
                  "series_name": "测试作品",
                  "series_intro": "简介",
                  "episode_cnt": 12,
                  "tags": ["剧情", "短剧"],
                  "status": "active"
                }
              ]
            }
            """.trimIndent()
        )
        assertEquals(1, works.size)
        assertEquals(7, works.single().id)
        assertEquals("source-7", works.single().sourceWorkId)
        assertEquals(12, works.single().episodeCount)
        assertEquals(listOf("剧情", "短剧"), works.single().tags)
    }

    @Test
    fun parsesWorkDetailAndCelebrityShapes() {
        val detail = BackendJsonParser.parseWorkDetail(
            """
            {
              "id": 7,
              "source": "novelquick",
              "series_id": "source-7",
              "series_name": "测试作品",
              "series_cover": "https://images.example/cover.jpg",
              "series_intro": "完整简介",
              "detail_url": "https://source.example/detail/7",
              "episode_right_text": "已完结",
              "episode_cnt": 2,
              "tags": ["剧情", "短剧"],
              "celebrities": [
                "演员甲",
                {"nickname": "演员乙"},
                {"name": "演员丙"},
                {"celebrity_name": "演员丁"},
                {"name": "演员乙"}
              ],
              "status": "active"
            }
            """.trimIndent()
        )

        assertEquals(7, detail.id)
        assertEquals("novelquick", detail.source)
        assertEquals("source-7", detail.sourceWorkId)
        assertEquals("测试作品", detail.name)
        assertEquals("已完结", detail.episodeRightText)
        assertEquals(listOf("演员甲", "演员乙", "演员丙", "演员丁"), detail.celebrities)
    }

    @Test
    fun parsesAndSortsEpisodePayload() {
        val episodes = BackendJsonParser.parseEpisodes(
            """
            [
              {
                "id": 102,
                "work_id": 7,
                "source_episode_id": "ep-2",
                "episode_index": 2,
                "title": "第二集",
                "duration_ms": null
              },
              {
                "id": 101,
                "work_id": 7,
                "source_episode_id": "ep-1",
                "episode_index": 1,
                "title": "第一集",
                "duration_ms": 65000
              },
              {
                "id": -1,
                "work_id": 7,
                "source_episode_id": "invalid",
                "episode_index": 3
              }
            ]
            """.trimIndent()
        )

        assertEquals(listOf(101L, 102L), episodes.map { it.id })
        assertEquals("第一集", episodes.first().title)
        assertEquals(65_000L, episodes.first().durationMs)
        assertNull(episodes.last().durationMs)
    }

    @Test
    fun parsesPlaybackProvidersAndDirectResolution() {
        val providers = BackendJsonParser.parsePlaybackProviders(
            """{"sources":["novelquick","manual","novelquick",""]}"""
        )
        assertEquals(setOf("novelquick", "manual"), providers)

        val direct = BackendJsonParser.parsePlayback(
            """
            {
              "episode_id": 101,
              "provider": "synthetic",
              "delivery": "direct",
              "url": "https://media.example/video.mp4?token=short",
              "mime_type": "video/mp4",
              "expires_at": "2026-07-20T05:30:00+00:00",
              "cached": false
            }
            """.trimIndent(),
            expectedEpisodeId = 101,
        )
        assertEquals(PlaybackDelivery.DIRECT, direct.delivery)
        assertEquals("https://media.example/video.mp4?token=short", direct.url)
        assertTrue(!direct.cached)
    }

    @Test
    fun parsesExternalProxyResolutionWithoutLeakingUrl() {
        val external = BackendJsonParser.parsePlayback(
            """
            {
              "episode_id": 102,
              "provider": "synthetic",
              "delivery": "external_proxy_required",
              "url": null,
              "mime_type": "video/mp4",
              "expires_at": "2026-07-20T05:30:00+00:00",
              "cached": true
            }
            """.trimIndent(),
            expectedEpisodeId = 102,
        )
        assertEquals(PlaybackDelivery.EXTERNAL_PROXY_REQUIRED, external.delivery)
        assertNull(external.url)
        assertTrue(external.cached)
    }

    @Test
    fun rejectsUnsafeOrLegacyPlaybackResponses() {
        assertFailsWith<BackendApiException> {
            BackendJsonParser.parsePlayback(
                """{"episode_id":1,"provider":"x","delivery":"direct","url":"http://media.example/a.mp4","expires_at":"later","cached":false}""",
                1,
            )
        }
        assertFailsWith<BackendApiException> {
            BackendJsonParser.parsePlayback(
                """{"episode_id":1,"provider":"x","delivery":"proxy_required","url":null,"expires_at":"later","cached":false}""",
                1,
            )
        }
        assertFailsWith<BackendApiException> {
            BackendJsonParser.parsePlayback(
                """{"episode_id":1,"provider":"x","delivery":"external_proxy_required","url":"https://secret.example/a.mp4","expires_at":"later","cached":false}""",
                1,
            )
        }
        assertFailsWith<BackendApiException> {
            BackendJsonParser.parsePlayback(
                """{"episode_id":2,"provider":"x","delivery":"direct","url":"https://media.example/a.mp4","expires_at":"later","cached":false}""",
                1,
            )
        }
    }

    @Test
    fun rejectsWorkDetailWithoutStableIdentity() {
        assertFailsWith<BackendApiException> {
            BackendJsonParser.parseWorkDetail(
                """{"id":7,"series_name":"缺少来源 ID"}"""
            )
        }
    }
}

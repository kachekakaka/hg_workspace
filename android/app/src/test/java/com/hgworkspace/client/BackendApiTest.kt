package com.hgworkspace.client

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

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
}

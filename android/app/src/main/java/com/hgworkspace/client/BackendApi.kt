package com.hgworkspace.client

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI


data class BackendStatus(
    val version: String,
    val catalogTotal: Int,
    val catalogActive: Int,
)

data class WorkSummary(
    val id: Long,
    val sourceWorkId: String,
    val name: String,
    val intro: String,
    val episodeCount: Int,
    val tags: List<String>,
    val status: String,
)

data class WorkDetail(
    val id: Long,
    val source: String,
    val sourceWorkId: String,
    val name: String,
    val coverUrl: String,
    val intro: String,
    val detailUrl: String,
    val episodeRightText: String,
    val episodeCount: Int,
    val tags: List<String>,
    val celebrities: List<String>,
    val status: String,
)

data class EpisodeSummary(
    val id: Long,
    val workId: Long,
    val sourceEpisodeId: String,
    val episodeIndex: Int,
    val title: String,
    val durationMs: Long?,
)

data class HomePayload(
    val status: BackendStatus,
    val works: List<WorkSummary>,
)

data class WorkDetailsPayload(
    val work: WorkDetail,
    val episodes: List<EpisodeSummary>,
)

class InvalidServerUrlException(message: String) : IllegalArgumentException(message)

object ServerUrlValidator {
    fun normalize(raw: String): String {
        val candidate = raw.trim().let { value ->
            if (value.contains("://")) value else "http://$value"
        }
        val parsed = try {
            URI(candidate)
        } catch (error: Exception) {
            throw InvalidServerUrlException("服务地址格式无效")
        }
        if (parsed.path.split('/').any { it == ".." }) {
            throw InvalidServerUrlException("服务地址路径不能包含上级目录")
        }
        val uri = parsed.normalize()
        val scheme = uri.scheme?.lowercase()
        if (scheme !in setOf("http", "https")) {
            throw InvalidServerUrlException("服务地址只支持 HTTP 或 HTTPS")
        }
        if (uri.userInfo != null) {
            throw InvalidServerUrlException("服务地址不能包含用户名或密码")
        }
        if (uri.query != null || uri.fragment != null) {
            throw InvalidServerUrlException("服务地址不能包含查询参数或片段")
        }
        val host = uri.host?.trim('[', ']')?.lowercase()
            ?: throw InvalidServerUrlException("服务地址缺少主机名")
        if (uri.port !in -1..65535) {
            throw InvalidServerUrlException("服务端口无效")
        }
        if (scheme == "http" && !isLocalOrPrivateHost(host)) {
            throw InvalidServerUrlException("公网服务地址必须使用 HTTPS")
        }
        return candidate.trimEnd('/')
    }

    private fun isLocalOrPrivateHost(host: String): Boolean {
        if (host == "localhost" || host.endsWith(".local") || !host.contains('.')) {
            return true
        }
        if (host.contains(':')) {
            return host == "::1" ||
                host.startsWith("fc") ||
                host.startsWith("fd") ||
                host.startsWith("fe8") ||
                host.startsWith("fe9") ||
                host.startsWith("fea") ||
                host.startsWith("feb")
        }
        val octets = host.split('.').mapNotNull { it.toIntOrNull() }
        if (octets.size != 4 || octets.any { it !in 0..255 }) return false
        return octets[0] == 10 ||
            octets[0] == 127 ||
            (octets[0] == 192 && octets[1] == 168) ||
            (octets[0] == 172 && octets[1] in 16..31)
    }
}

object BackendJsonParser {
    fun parseStatus(raw: String): BackendStatus {
        val json = JSONObject(raw)
        return BackendStatus(
            version = json.optString("version", "--"),
            catalogTotal = json.optInt("catalog_total", 0),
            catalogActive = json.optInt("catalog_active", 0),
        )
    }

    fun parseWorks(raw: String): List<WorkSummary> {
        val root = JSONObject(raw)
        val works = root.optJSONArray("works") ?: JSONArray()
        return buildList {
            for (index in 0 until works.length()) {
                val item = works.optJSONObject(index) ?: continue
                val id = item.optLong("id", -1)
                val sourceId = item.optString("series_id", item.optString("source_work_id"))
                val name = item.optString("series_name").trim()
                if (id < 0 || sourceId.isBlank() || name.isBlank()) continue
                add(
                    WorkSummary(
                        id = id,
                        sourceWorkId = sourceId,
                        name = name,
                        intro = item.optString("series_intro"),
                        episodeCount = episodeCount(item),
                        tags = stringList(item.optJSONArray("tags")),
                        status = item.optString("status", "active"),
                    )
                )
            }
        }
    }

    fun parseWorkDetail(raw: String): WorkDetail {
        val item = JSONObject(raw)
        val id = item.optLong("id", -1)
        val sourceId = item.optString("series_id", item.optString("source_work_id")).trim()
        val name = item.optString("series_name").trim()
        if (id < 0 || sourceId.isBlank() || name.isBlank()) {
            throw BackendApiException("作品详情响应缺少必要字段")
        }
        return WorkDetail(
            id = id,
            source = item.optString("source"),
            sourceWorkId = sourceId,
            name = name,
            coverUrl = item.optString("series_cover"),
            intro = item.optString("series_intro"),
            detailUrl = item.optString("detail_url"),
            episodeRightText = item.optString("episode_right_text"),
            episodeCount = episodeCount(item),
            tags = stringList(item.optJSONArray("tags")),
            celebrities = celebrityList(item.optJSONArray("celebrities")),
            status = item.optString("status", "active"),
        )
    }

    fun parseEpisodes(raw: String): List<EpisodeSummary> {
        val episodes = JSONArray(raw)
        return buildList {
            for (index in 0 until episodes.length()) {
                val item = episodes.optJSONObject(index) ?: continue
                val id = item.optLong("id", -1)
                val workId = item.optLong("work_id", -1)
                val sourceId = item.optString("source_episode_id").trim()
                val episodeIndex = item.optInt("episode_index", 0)
                if (id < 0 || workId < 0 || sourceId.isBlank() || episodeIndex < 1) continue
                val duration = if (item.has("duration_ms") && !item.isNull("duration_ms")) {
                    item.optLong("duration_ms", -1).takeIf { it >= 0 }
                } else {
                    null
                }
                add(
                    EpisodeSummary(
                        id = id,
                        workId = workId,
                        sourceEpisodeId = sourceId,
                        episodeIndex = episodeIndex,
                        title = item.optString("title").trim(),
                        durationMs = duration,
                    )
                )
            }
        }.sortedWith(compareBy(EpisodeSummary::episodeIndex, EpisodeSummary::id))
    }

    private fun episodeCount(item: JSONObject): Int = if (item.has("episode_cnt")) {
        item.optInt("episode_cnt", 0)
    } else {
        item.optInt("episode_count", 0)
    }

    private fun stringList(array: JSONArray?): List<String> = buildList {
        if (array == null) return@buildList
        for (index in 0 until array.length()) {
            val value = array.optString(index).trim()
            if (value.isNotEmpty()) add(value)
        }
    }

    private fun celebrityList(array: JSONArray?): List<String> = buildList {
        if (array == null) return@buildList
        for (index in 0 until array.length()) {
            val raw = array.opt(index)
            val name = when (raw) {
                is String -> raw
                is JSONObject -> raw.optString(
                    "nickname",
                    raw.optString("name", raw.optString("celebrity_name")),
                )
                else -> ""
            }.trim()
            if (name.isNotEmpty()) add(name)
        }
    }.distinct()
}

class BackendApiException(message: String, cause: Throwable? = null) : RuntimeException(message, cause)

class BackendApiClient(
    private val connectTimeoutMs: Int = 10_000,
    private val readTimeoutMs: Int = 15_000,
    private val maxResponseBytes: Int = 4 * 1024 * 1024,
) {
    fun loadHome(baseUrl: String): HomePayload {
        val status = BackendJsonParser.parseStatus(get(baseUrl, "/api/status"))
        val works = BackendJsonParser.parseWorks(
            get(baseUrl, "/api/works?page=1&page_size=60&status=active")
        )
        return HomePayload(status, works)
    }

    fun loadWorkDetails(baseUrl: String, work: WorkSummary): WorkDetailsPayload {
        val detail = BackendJsonParser.parseWorkDetail(
            get(baseUrl, "/api/v1/works/${work.id}")
        )
        val episodes = BackendJsonParser.parseEpisodes(
            get(baseUrl, "/api/v1/works/${work.id}/episodes")
        )
        if (detail.id != work.id || detail.sourceWorkId != work.sourceWorkId) {
            throw BackendApiException("作品详情与列表身份不一致")
        }
        if (episodes.any { it.workId != work.id }) {
            throw BackendApiException("分集响应包含其他作品的数据")
        }
        return WorkDetailsPayload(detail, episodes)
    }

    private fun get(baseUrl: String, path: String): String {
        val connection = try {
            (URI.create(baseUrl + path).toURL().openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = connectTimeoutMs
                readTimeout = readTimeoutMs
                instanceFollowRedirects = false
                setRequestProperty("Accept", "application/json")
                setRequestProperty("User-Agent", "HGClient/0.2")
            }
        } catch (error: Exception) {
            throw BackendApiException("无法创建后端连接", error)
        }
        return try {
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val body = stream?.use { input ->
                BufferedInputStream(input).readLimited(maxResponseBytes)
            }.orEmpty()
            if (code !in 200..299) {
                throw BackendApiException("后端请求失败（HTTP $code）")
            }
            body
        } catch (error: BackendApiException) {
            throw error
        } catch (error: Exception) {
            throw BackendApiException("无法读取后端响应", error)
        } finally {
            connection.disconnect()
        }
    }
}

private fun BufferedInputStream.readLimited(maxBytes: Int): String {
    val output = ByteArrayOutputStream(minOf(maxBytes, 64 * 1024))
    val buffer = ByteArray(8192)
    var total = 0
    while (true) {
        val count = read(buffer)
        if (count < 0) break
        total += count
        if (total > maxBytes) throw BackendApiException("后端响应超过大小限制")
        output.write(buffer, 0, count)
    }
    return output.toString(Charsets.UTF_8.name())
}

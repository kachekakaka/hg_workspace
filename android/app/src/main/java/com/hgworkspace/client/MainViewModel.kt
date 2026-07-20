package com.hgworkspace.client

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext


data class MainUiState(
    val serverInput: String = "",
    val normalizedServerUrl: String = "",
    val loading: Boolean = false,
    val status: BackendStatus? = null,
    val works: List<WorkSummary> = emptyList(),
    val error: String = "",
    val selectedWork: WorkSummary? = null,
    val workDetail: WorkDetail? = null,
    val episodes: List<EpisodeSummary> = emptyList(),
    val detailLoading: Boolean = false,
    val detailError: String = "",
    val playbackSources: Set<String> = emptySet(),
    val playbackLoading: Boolean = false,
    val playbackResolution: PlaybackResolution? = null,
    val playbackError: String = "",
)

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val settings = ServerSettingsRepository(application)
    private val api = BackendApiClient()
    private val _state = MutableStateFlow(MainUiState(serverInput = settings.loadServerUrl()))
    val state: StateFlow<MainUiState> = _state.asStateFlow()
    private var loadJob: Job? = null
    private var detailJob: Job? = null
    private var playbackJob: Job? = null

    init {
        if (_state.value.serverInput.isNotBlank()) connect()
    }

    fun updateServerInput(value: String) {
        _state.update { it.copy(serverInput = value) }
    }

    fun connect() {
        val normalized = try {
            ServerUrlValidator.normalize(_state.value.serverInput)
        } catch (error: IllegalArgumentException) {
            _state.update { it.copy(error = error.message ?: "服务地址无效") }
            return
        }
        settings.saveServerUrl(normalized)
        loadJob?.cancel()
        detailJob?.cancel()
        playbackJob?.cancel()
        loadJob = viewModelScope.launch {
            _state.update {
                it.copy(
                    serverInput = normalized,
                    normalizedServerUrl = normalized,
                    loading = true,
                    error = "",
                    selectedWork = null,
                    workDetail = null,
                    episodes = emptyList(),
                    detailLoading = false,
                    detailError = "",
                    playbackSources = emptySet(),
                    playbackLoading = false,
                    playbackResolution = null,
                    playbackError = "",
                )
            }
            try {
                val payload = withContext(Dispatchers.IO) { api.loadHome(normalized) }
                _state.update {
                    it.copy(
                        loading = false,
                        status = payload.status,
                        works = payload.works,
                        playbackSources = payload.playbackSources,
                        error = "",
                    )
                }
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                _state.update {
                    it.copy(
                        loading = false,
                        status = null,
                        works = emptyList(),
                        playbackSources = emptySet(),
                        error = error.message ?: "连接后端失败",
                    )
                }
            }
        }
    }

    fun openWork(work: WorkSummary) {
        val baseUrl = _state.value.normalizedServerUrl
        if (baseUrl.isBlank()) {
            _state.update { it.copy(error = "请先连接后端或 NAS 服务") }
            return
        }
        detailJob?.cancel()
        playbackJob?.cancel()
        _state.update {
            it.copy(
                selectedWork = work,
                workDetail = null,
                episodes = emptyList(),
                detailLoading = true,
                detailError = "",
                playbackLoading = false,
                playbackResolution = null,
                playbackError = "",
            )
        }
        detailJob = viewModelScope.launch {
            try {
                val payload = withContext(Dispatchers.IO) {
                    api.loadWorkDetails(baseUrl, work)
                }
                _state.update { current ->
                    if (current.selectedWork?.id != work.id) current else current.copy(
                        workDetail = payload.work,
                        episodes = payload.episodes,
                        detailLoading = false,
                        detailError = "",
                    )
                }
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                _state.update { current ->
                    if (current.selectedWork?.id != work.id) current else current.copy(
                        detailLoading = false,
                        detailError = error.message ?: "作品详情加载失败",
                    )
                }
            }
        }
    }

    fun closeWork() {
        detailJob?.cancel()
        playbackJob?.cancel()
        _state.update {
            it.copy(
                selectedWork = null,
                workDetail = null,
                episodes = emptyList(),
                detailLoading = false,
                detailError = "",
                playbackLoading = false,
                playbackResolution = null,
                playbackError = "",
            )
        }
    }

    fun resolvePlayback(episode: EpisodeSummary) {
        val baseUrl = _state.value.normalizedServerUrl
        val source = _state.value.workDetail?.source.orEmpty()
        if (source !in _state.value.playbackSources) {
            _state.update { it.copy(playbackError = "后端未配置该来源的播放 provider") }
            return
        }
        playbackJob?.cancel()
        playbackJob = viewModelScope.launch {
            _state.update {
                it.copy(
                    playbackLoading = true,
                    playbackResolution = null,
                    playbackError = "",
                )
            }
            try {
                val resolution = withContext(Dispatchers.IO) {
                    api.resolvePlayback(baseUrl, episode.id)
                }
                _state.update { current ->
                    if (current.selectedWork?.id != episode.workId) current else current.copy(
                        playbackLoading = false,
                        playbackResolution = resolution,
                        playbackError = "",
                    )
                }
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                _state.update { current ->
                    if (current.selectedWork?.id != episode.workId) current else current.copy(
                        playbackLoading = false,
                        playbackResolution = null,
                        playbackError = error.message ?: "播放能力检查失败",
                    )
                }
            }
        }
    }

    fun clearPlaybackCheck() {
        playbackJob?.cancel()
        _state.update {
            it.copy(
                playbackLoading = false,
                playbackResolution = null,
                playbackError = "",
            )
        }
    }
}

private class ServerSettingsRepository(context: Context) {
    private val preferences = context.getSharedPreferences("hg_client_settings", Context.MODE_PRIVATE)

    fun loadServerUrl(): String = preferences.getString(KEY_SERVER_URL, "").orEmpty()

    fun saveServerUrl(value: String) {
        preferences.edit().putString(KEY_SERVER_URL, value).apply()
    }

    private companion object {
        const val KEY_SERVER_URL = "server_url"
    }
}

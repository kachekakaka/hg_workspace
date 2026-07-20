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
)

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val settings = ServerSettingsRepository(application)
    private val api = BackendApiClient()
    private val _state = MutableStateFlow(MainUiState(serverInput = settings.loadServerUrl()))
    val state: StateFlow<MainUiState> = _state.asStateFlow()
    private var loadJob: Job? = null
    private var detailJob: Job? = null

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
                )
            }
            try {
                val payload = withContext(Dispatchers.IO) { api.loadHome(normalized) }
                _state.update {
                    it.copy(
                        loading = false,
                        status = payload.status,
                        works = payload.works,
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
        _state.update {
            it.copy(
                selectedWork = work,
                workDetail = null,
                episodes = emptyList(),
                detailLoading = true,
                detailError = "",
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
        _state.update {
            it.copy(
                selectedWork = null,
                workDetail = null,
                episodes = emptyList(),
                detailLoading = false,
                detailError = "",
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

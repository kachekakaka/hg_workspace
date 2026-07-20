package com.hgworkspace.client

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

private val HgColors = lightColorScheme(
    primary = Color(0xFFB42318),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFFFDAD6),
    onPrimaryContainer = Color(0xFF410002),
    secondary = Color(0xFF775651),
    background = Color(0xFFF9F7F7),
    surface = Color.White,
)

@Composable
fun HgTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = HgColors, content = content)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HgApp(viewModel: MainViewModel, isTv: Boolean) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val selectedWork = state.selectedWork
    BackHandler(enabled = selectedWork != null, onBack = viewModel::closeWork)

    Scaffold(
        topBar = {
            TopAppBar(
                navigationIcon = {
                    if (selectedWork != null) {
                        TextButton(onClick = viewModel::closeWork) { Text("返回") }
                    }
                },
                title = {
                    Text(
                        text = selectedWork?.name ?: if (isTv) "HG Client · TV" else "HG Client",
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                },
            )
        }
    ) { innerPadding ->
        if (selectedWork == null) {
            HomeScreen(
                state = state,
                isTv = isTv,
                modifier = Modifier.padding(innerPadding),
                onServerChange = viewModel::updateServerInput,
                onConnect = viewModel::connect,
                onOpenWork = viewModel::openWork,
            )
        } else {
            WorkDetailsScreen(
                state = state,
                selectedWork = selectedWork,
                isTv = isTv,
                modifier = Modifier.padding(innerPadding),
                onResolvePlayback = viewModel::resolvePlayback,
                onClearPlayback = viewModel::clearPlaybackCheck,
            )
        }
    }
}

@Composable
private fun HomeScreen(
    state: MainUiState,
    isTv: Boolean,
    modifier: Modifier = Modifier,
    onServerChange: (String) -> Unit,
    onConnect: () -> Unit,
    onOpenWork: (WorkSummary) -> Unit,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = if (isTv) 28.dp else 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        ServerPanel(
            value = state.serverInput,
            loading = state.loading,
            onValueChange = onServerChange,
            onConnect = onConnect,
        )
        StatusPanel(state)
        Text(
            text = "作品 (${state.works.size})",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
        )
        Box(modifier = Modifier.fillMaxWidth().weight(1f)) {
            when {
                state.loading && state.works.isEmpty() -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                state.works.isEmpty() -> {
                    Text(
                        text = if (state.normalizedServerUrl.isBlank()) {
                            "填写后端或 NAS 服务地址后连接。"
                        } else {
                            "当前没有上架作品。"
                        },
                        modifier = Modifier.align(Alignment.Center),
                    )
                }
                isTv -> {
                    LazyVerticalGrid(
                        columns = GridCells.Adaptive(260.dp),
                        modifier = Modifier.fillMaxSize(),
                        horizontalArrangement = Arrangement.spacedBy(14.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp),
                    ) {
                        gridItems(state.works, key = { it.id }) { work ->
                            WorkCard(work, onClick = { onOpenWork(work) })
                        }
                    }
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        items(state.works, key = { it.id }) { work ->
                            WorkCard(work, onClick = { onOpenWork(work) })
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun WorkDetailsScreen(
    state: MainUiState,
    selectedWork: WorkSummary,
    isTv: Boolean,
    modifier: Modifier = Modifier,
    onResolvePlayback: (EpisodeSummary) -> Unit,
    onClearPlayback: () -> Unit,
) {
    var selectedEpisode by remember(selectedWork.id) { mutableStateOf<EpisodeSummary?>(null) }
    val detail = state.workDetail

    if (isTv) {
        Row(
            modifier = modifier
                .fillMaxSize()
                .padding(horizontal = 28.dp, vertical = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            WorkMetadataCard(
                selectedWork = selectedWork,
                detail = detail,
                modifier = Modifier.width(340.dp),
            )
            EpisodePanel(
                state = state,
                isTv = true,
                modifier = Modifier.weight(1f),
                onEpisodeClick = { episode ->
                    onClearPlayback()
                    selectedEpisode = episode
                },
            )
        }
    } else {
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            WorkMetadataCard(
                selectedWork = selectedWork,
                detail = detail,
                modifier = Modifier.fillMaxWidth(),
            )
            EpisodePanel(
                state = state,
                isTv = false,
                modifier = Modifier.weight(1f),
                onEpisodeClick = { episode ->
                    onClearPlayback()
                    selectedEpisode = episode
                },
            )
        }
    }

    selectedEpisode?.let { episode ->
        val source = state.workDetail?.source.orEmpty()
        val providerConfigured = source.isNotBlank() && source in state.playbackSources
        val closeDialog = {
            onClearPlayback()
            selectedEpisode = null
        }
        AlertDialog(
            onDismissRequest = closeDialog,
            confirmButton = {
                if (providerConfigured) {
                    TextButton(
                        onClick = { onResolvePlayback(episode) },
                        enabled = !state.playbackLoading,
                    ) {
                        Text(if (state.playbackLoading) "检查中" else "检查播放能力")
                    }
                } else {
                    TextButton(onClick = closeDialog) { Text("关闭") }
                }
            },
            dismissButton = {
                if (providerConfigured) {
                    TextButton(onClick = closeDialog) { Text("关闭") }
                }
            },
            title = { Text(episode.title.ifBlank { "第 ${episode.episodeIndex} 集" }) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("第 ${episode.episodeIndex} 集")
                    Text("来源分集 ID：${episode.sourceEpisodeId}")
                    episode.durationMs?.let { Text("时长：${formatDuration(it)}") }
                    if (!providerConfigured) {
                        Text("后端未配置 ${source.ifBlank { "该来源" }} 的播放 provider。")
                    }
                    if (state.playbackLoading) {
                        Text("正在向后端检查短期播放解析…")
                    }
                    if (state.playbackError.isNotBlank()) {
                        Text(state.playbackError, color = MaterialTheme.colorScheme.error)
                    }
                    state.playbackResolution
                        ?.takeIf { it.episodeId == episode.id }
                        ?.let { resolution ->
                            when (resolution.delivery) {
                                PlaybackDelivery.DIRECT -> Text(
                                    "后端已返回 direct 短期 HTTPS 地址。Media3 播放器尚未接入。"
                                )
                                PlaybackDelivery.EXTERNAL_PROXY_REQUIRED -> Text(
                                    "该分集需要 NAS external_proxy_required handoff；当前尚未配置。"
                                )
                            }
                            Text(
                                "provider：${resolution.provider} · ${if (resolution.cached) "缓存命中" else "新解析"}",
                                style = MaterialTheme.typography.bodySmall,
                            )
                            if (resolution.mimeType.isNotBlank()) {
                                Text("类型：${resolution.mimeType}", style = MaterialTheme.typography.bodySmall)
                            }
                            Text("过期：${resolution.expiresAt}", style = MaterialTheme.typography.bodySmall)
                        }
                    Text("本批次只检查交付契约，不启动播放器或下载。")
                }
            },
        )
    }
}

@Composable
private fun WorkMetadataCard(
    selectedWork: WorkSummary,
    detail: WorkDetail?,
    modifier: Modifier = Modifier,
) {
    Card(modifier = modifier) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            Text(
                text = detail?.name ?: selectedWork.name,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            val episodeText = buildString {
                append(detail?.episodeCount ?: selectedWork.episodeCount)
                append(" 集")
                val rightText = detail?.episodeRightText.orEmpty().trim()
                if (rightText.isNotEmpty()) append(" · ").append(rightText)
            }
            Text(episodeText)
            val tags = detail?.tags ?: selectedWork.tags
            if (tags.isNotEmpty()) Text("标签：${tags.joinToString("、")}")
            val celebrities = detail?.celebrities.orEmpty()
            if (celebrities.isNotEmpty()) Text("演员：${celebrities.joinToString("、")}")
            Text((detail?.intro ?: selectedWork.intro).ifBlank { "暂无简介" })
            Text(
                text = "来源：${detail?.source.orEmpty().ifBlank { "--" }} · ${selectedWork.sourceWorkId}",
                style = MaterialTheme.typography.bodySmall,
            )
            if (!detail?.detailUrl.isNullOrBlank()) {
                Text(
                    text = "详情地址：${detail?.detailUrl}",
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun EpisodePanel(
    state: MainUiState,
    isTv: Boolean,
    modifier: Modifier = Modifier,
    onEpisodeClick: (EpisodeSummary) -> Unit,
) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("分集 (${state.episodes.size})", style = MaterialTheme.typography.titleLarge)
        if (state.detailError.isNotBlank()) {
            Text(state.detailError, color = MaterialTheme.colorScheme.error)
        }
        Box(modifier = Modifier.fillMaxWidth().weight(1f)) {
            when {
                state.detailLoading && state.episodes.isEmpty() -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                state.episodes.isEmpty() -> {
                    Text(
                        text = if (state.detailError.isBlank()) {
                            "尚未导入分集明细。可先在 Web 管理页刷新公开详情与分集。"
                        } else {
                            "分集加载失败，可返回后重试。"
                        },
                        modifier = Modifier.align(Alignment.Center),
                    )
                }
                isTv -> {
                    LazyVerticalGrid(
                        columns = GridCells.Adaptive(170.dp),
                        modifier = Modifier.fillMaxSize(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        gridItems(state.episodes, key = { it.id }) { episode ->
                            EpisodeCard(episode, onClick = { onEpisodeClick(episode) })
                        }
                    }
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        items(state.episodes, key = { it.id }) { episode ->
                            EpisodeCard(episode, onClick = { onEpisodeClick(episode) })
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ServerPanel(
    value: String,
    loading: Boolean,
    onValueChange: (String) -> Unit,
    onConnect: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("服务地址", fontWeight = FontWeight.SemiBold)
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = value,
                    onValueChange = onValueChange,
                    modifier = Modifier.weight(1f),
                    label = { Text("例如 192.168.1.10:8000 或 https://nas.example") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                )
                Spacer(Modifier.width(10.dp))
                Button(onClick = onConnect, enabled = !loading) {
                    Text(if (loading) "连接中" else "保存并连接")
                }
            }
        }
    }
}

@Composable
private fun StatusPanel(state: MainUiState) {
    val message = when {
        state.error.isNotBlank() -> state.error
        state.status != null -> "后端 ${state.status.version} · ${state.status.catalogActive}/${state.status.catalogTotal} 部上架"
        else -> "尚未连接"
    }
    val color = if (state.error.isNotBlank()) MaterialTheme.colorScheme.error else Color.Unspecified
    Text(message, color = color, style = MaterialTheme.typography.bodyMedium)
}

@Composable
private fun WorkCard(work: WorkSummary, onClick: () -> Unit) {
    FocusCard(onClick = onClick) {
        Text(
            text = work.name,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Text("${work.episodeCount} 集 · ${if (work.status == "active") "上架" else "下架"}")
        if (work.tags.isNotEmpty()) {
            Text(
                text = work.tags.take(4).joinToString(" · "),
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        if (work.intro.isNotBlank()) {
            Spacer(Modifier.height(2.dp))
            Text(
                text = work.intro,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun EpisodeCard(episode: EpisodeSummary, onClick: () -> Unit) {
    FocusCard(onClick = onClick) {
        Text(
            text = episode.title.ifBlank { "第 ${episode.episodeIndex} 集" },
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Text("第 ${episode.episodeIndex} 集", style = MaterialTheme.typography.bodySmall)
        episode.durationMs?.let {
            Text(formatDuration(it), style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun FocusCard(onClick: () -> Unit, content: @Composable () -> Unit) {
    var focused by remember { mutableStateOf(false) }
    Card(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .onFocusChanged { focused = it.isFocused }
            .then(
                if (focused) Modifier.border(
                    3.dp,
                    MaterialTheme.colorScheme.primary,
                    MaterialTheme.shapes.medium,
                ) else Modifier
            ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            content()
        }
    }
}

private fun formatDuration(durationMs: Long): String {
    val totalSeconds = durationMs / 1000
    val hours = totalSeconds / 3600
    val minutes = (totalSeconds % 3600) / 60
    val seconds = totalSeconds % 60
    return if (hours > 0) {
        "%d:%02d:%02d".format(hours, minutes, seconds)
    } else {
        "%02d:%02d".format(minutes, seconds)
    }
}

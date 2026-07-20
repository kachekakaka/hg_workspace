package com.hgworkspace.client

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.material3.lightColorScheme
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
    var selectedWork by remember { mutableStateOf<WorkSummary?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(if (isTv) "HG Client · TV" else "HG Client")
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = if (isTv) 28.dp else 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            ServerPanel(
                value = state.serverInput,
                loading = state.loading,
                onValueChange = viewModel::updateServerInput,
                onConnect = viewModel::connect,
            )
            StatusPanel(state)
            Text(
                text = "作品 (${state.works.size})",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            Box(modifier = Modifier.fillMaxWidth().weight(1f)) {
                if (state.loading && state.works.isEmpty()) {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                } else if (state.works.isEmpty()) {
                    Text(
                        text = if (state.normalizedServerUrl.isBlank()) {
                            "填写后端或 NAS 服务地址后连接。"
                        } else {
                            "当前没有上架作品。"
                        },
                        modifier = Modifier.align(Alignment.Center),
                    )
                } else if (isTv) {
                    LazyVerticalGrid(
                        columns = GridCells.Adaptive(260.dp),
                        modifier = Modifier.fillMaxSize(),
                        horizontalArrangement = Arrangement.spacedBy(14.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp),
                    ) {
                        gridItems(state.works, key = { it.id }) { work ->
                            WorkCard(work, onClick = { selectedWork = work })
                        }
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        items(state.works, key = { it.id }) { work ->
                            WorkCard(work, onClick = { selectedWork = work })
                        }
                    }
                }
            }
        }
    }

    selectedWork?.let { work ->
        AlertDialog(
            onDismissRequest = { selectedWork = null },
            confirmButton = {
                TextButton(onClick = { selectedWork = null }) { Text("关闭") }
            },
            title = { Text(work.name) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("共 ${work.episodeCount} 集")
                    if (work.tags.isNotEmpty()) Text("标签：${work.tags.joinToString("、")}")
                    Text(work.intro.ifBlank { "暂无简介" })
                    Text("来源 ID：${work.sourceWorkId}", style = MaterialTheme.typography.bodySmall)
                }
            },
        )
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
    var focused by remember { mutableStateOf(false) }
    Card(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .onFocusChanged { focused = it.isFocused }
            .then(
                if (focused) Modifier.border(3.dp, MaterialTheme.colorScheme.primary, MaterialTheme.shapes.medium)
                else Modifier
            ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
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
}

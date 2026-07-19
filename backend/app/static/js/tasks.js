import { getTasks, importCatalog, retryTask } from './api.js';
import { clear, errorMessage, formatDate, setStatus, text } from './common.js';

const MAX_FILE_SIZE = 20 * 1024 * 1024;
const statusLabels = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  interrupted: '已中断',
};

function taskTypeLabel(type) {
  return type === 'catalog_import' ? 'catalog 导入' : type;
}

function resultSummary(task) {
  if (task.status === 'completed') {
    const result = task.result || {};
    return `总计 ${result.total || 0}，新增 ${result.added || 0}，更新 ${result.updated || 0}`;
  }
  if (task.status === 'failed' || task.status === 'interrupted') {
    return task.result?.error || task.message || '';
  }
  return task.message || '';
}

function statusNode(status) {
  return text('span', statusLabels[status] || status, `task-status ${status}`);
}

function progressNode(task) {
  const wrapper = document.createElement('div');
  const label = text('div', `${Math.round(Number(task.progress || 0) * 100)}%`, 'text-muted');
  const bar = document.createElement('div');
  bar.className = 'progress';
  const fill = document.createElement('span');
  fill.style.width = `${Math.min(Math.max(Number(task.progress || 0) * 100, 0), 100)}%`;
  bar.append(fill);
  wrapper.append(label, bar);
  return wrapper;
}

async function handleRetry(taskId, button) {
  button.disabled = true;
  try {
    await retryTask(taskId);
    await loadTasks();
  } catch (error) {
    setStatus(document.querySelector('#tasksMessage'), errorMessage(error), 'error');
    button.disabled = false;
  }
}

function renderTasks(tasks) {
  const container = document.querySelector('#tasksContainer');
  clear(container);
  if (!tasks.length) {
    container.append(text('div', '暂无任务记录。', 'empty-state'));
    return;
  }

  const table = document.createElement('table');
  const head = document.createElement('thead');
  const headRow = document.createElement('tr');
  ['ID', '类型', '状态', '进度', '创建时间', '详情', '操作'].forEach((label) => {
    headRow.append(text('th', label));
  });
  head.append(headRow);

  const body = document.createElement('tbody');
  tasks.forEach((task) => {
    const row = document.createElement('tr');
    const id = text('td', `${task.task_id.slice(0, 8)}…`, 'mono');
    id.title = task.task_id;
    row.append(id);
    row.append(text('td', taskTypeLabel(task.type)));
    const statusCell = document.createElement('td');
    statusCell.append(statusNode(task.status));
    row.append(statusCell);
    const progressCell = document.createElement('td');
    progressCell.append(progressNode(task));
    row.append(progressCell);
    row.append(text('td', formatDate(task.created_at)));
    row.append(text('td', resultSummary(task), 'task-detail'));

    const actionCell = document.createElement('td');
    if (task.status === 'failed' || task.status === 'interrupted') {
      const retry = text('button', '重试', 'btn btn-default btn-small');
      retry.type = 'button';
      retry.addEventListener('click', () => handleRetry(task.task_id, retry));
      actionCell.append(retry);
    } else {
      actionCell.textContent = '--';
    }
    row.append(actionCell);
    body.append(row);
  });

  table.append(head, body);
  container.append(table);
}

async function loadTasks() {
  const message = document.querySelector('#tasksMessage');
  try {
    const data = await getTasks({ limit: 100 });
    renderTasks(data.tasks || []);
    setStatus(message, `共 ${Number(data.total || 0).toLocaleString('zh-CN')} 条任务`, 'success');
  } catch (error) {
    clear(document.querySelector('#tasksContainer'));
    setStatus(message, errorMessage(error), 'error');
  }
}

document.querySelector('#importForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = document.querySelector('#catalogFile').files[0];
  const source = document.querySelector('#sourceInput').value.trim();
  const message = document.querySelector('#importMessage');
  const button = document.querySelector('#importButton');

  if (!file) {
    setStatus(message, '请选择 JSON 文件。', 'error');
    return;
  }
  if (!source) {
    setStatus(message, '来源名不能为空。', 'error');
    return;
  }
  if (file.size > MAX_FILE_SIZE) {
    setStatus(message, '文件超过 20 MiB 的管理页限制。请使用 API 或先拆分数据。', 'error');
    return;
  }

  button.disabled = true;
  setStatus(message, '正在读取并验证 JSON…');
  try {
    const raw = await file.text();
    let payload;
    try {
      payload = JSON.parse(raw);
    } catch (error) {
      throw new Error(`JSON 解析失败：${error.message}`);
    }
    setStatus(message, '正在创建持久化导入任务…');
    const task = await importCatalog(payload, source);
    setStatus(message, `任务已创建：${task.task_id}`, 'success');
    document.querySelector('#catalogFile').value = '';
    await loadTasks();
  } catch (error) {
    setStatus(message, errorMessage(error), 'error');
  } finally {
    button.disabled = false;
  }
});

document.querySelector('#refreshButton').addEventListener('click', loadTasks);
loadTasks();
window.setInterval(loadTasks, 5_000);

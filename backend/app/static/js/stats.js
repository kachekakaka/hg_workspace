import { getStats, getStatus } from './api.js';
import { errorMessage, formatDate, formatNumber, setStatus } from './common.js';

async function refresh() {
  const message = document.querySelector('#statusMessage');
  const table = document.querySelector('#serviceTable');
  setStatus(message, '正在刷新…');

  try {
    const [stats, status] = await Promise.all([getStats(), getStatus()]);
    document.querySelector('#statTotal').textContent = formatNumber(stats.total);
    document.querySelector('#statActive').textContent = formatNumber(stats.active);
    document.querySelector('#statRemoved').textContent = formatNumber(stats.removed);

    document.querySelector('#serviceVersion').textContent = status.version || '--';
    document.querySelector('#servicePort').textContent = status.http_port ?? '--';
    document.querySelector('#serviceTotal').textContent = formatNumber(status.catalog_total);
    document.querySelector('#serviceActive').textContent = formatNumber(status.catalog_active);
    document.querySelector('#lastUpdated').textContent = `更新于 ${formatDate(new Date().toISOString())}`;
    table.classList.remove('hidden');
    setStatus(message, '服务连接正常', 'success');
  } catch (error) {
    table.classList.add('hidden');
    setStatus(message, errorMessage(error), 'error');
  }
}

document.querySelector('#refreshButton').addEventListener('click', refresh);
refresh();
window.setInterval(refresh, 30_000);

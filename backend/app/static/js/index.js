import { getEpisodes, getStatus, getWork, getWorks } from './api.js';
import { clear, errorMessage, formatDate, safeHttpUrl, setStatus, text } from './common.js';

const PAGE_SIZE = 60;
let currentPage = 1;
let totalWorks = 0;
let currentQuery = '';
let currentStatus = 'active';
let currentTag = '';

const grid = document.querySelector('#worksGrid');
const totalLabel = document.querySelector('#totalLabel');
const pagination = document.querySelector('#pagination');
const message = document.querySelector('#message');
const modal = document.querySelector('#detailModal');
const detailContent = document.querySelector('#detailContent');

function statusBadge(status) {
  return text(
    'span',
    status === 'active' ? '上架' : '下架',
    `badge badge-${status === 'active' ? 'active' : 'removed'}`,
  );
}

function coverNode(url, title, className = 'work-cover') {
  const safeUrl = safeHttpUrl(url);
  if (!safeUrl) return text('div', '暂无封面', 'cover-placeholder');
  const image = document.createElement('img');
  image.className = className;
  image.src = safeUrl;
  image.alt = `${title} 封面`;
  image.loading = 'lazy';
  image.addEventListener('error', () => {
    image.replaceWith(text('div', '封面加载失败', 'cover-placeholder'));
  }, { once: true });
  return image;
}

function renderWorks(works) {
  clear(grid);
  if (!works.length) {
    grid.append(text('div', '没有找到匹配作品。', 'empty-state'));
    return;
  }

  works.forEach((work) => {
    const card = document.createElement('article');
    card.className = 'work-card';
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `查看 ${work.series_name}`);
    card.append(coverNode(work.series_cover, work.series_name));

    const body = document.createElement('div');
    body.className = 'work-card-body';
    const title = text('h2', work.series_name, 'work-title');
    title.title = work.series_name;
    const meta = document.createElement('div');
    meta.className = 'work-meta';
    meta.append(text('span', `${work.episode_cnt ?? work.episode_count ?? 0} 集`));
    meta.append(statusBadge(work.status));
    body.append(title, meta);
    card.append(body);

    const open = () => openDetail(work.series_id);
    card.addEventListener('click', open);
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open();
      }
    });
    grid.append(card);
  });
}

function renderPagination() {
  clear(pagination);
  const pages = Math.ceil(totalWorks / PAGE_SIZE);
  if (pages <= 1) return;

  const previous = text('button', '‹ 上一页', 'btn btn-default btn-small');
  previous.type = 'button';
  previous.disabled = currentPage <= 1;
  previous.addEventListener('click', () => loadWorks(currentPage - 1));

  const info = text('span', `${currentPage} / ${pages}`, 'page-info');

  const next = text('button', '下一页 ›', 'btn btn-default btn-small');
  next.type = 'button';
  next.disabled = currentPage >= pages;
  next.addEventListener('click', () => loadWorks(currentPage + 1));
  pagination.append(previous, info, next);
}

async function loadWorks(page = 1) {
  currentPage = page;
  clear(grid);
  grid.append(text('div', '正在加载作品…', 'loading'));
  clear(pagination);
  setStatus(message, '');

  try {
    const data = await getWorks({
      q: currentQuery,
      status: currentStatus,
      tag: currentTag,
      page,
      pageSize: PAGE_SIZE,
    });
    totalWorks = data.total;
    totalLabel.textContent = `共 ${totalWorks.toLocaleString('zh-CN')} 部`;
    renderWorks(data.works || []);
    renderPagination();
  } catch (error) {
    clear(grid);
    grid.append(text('div', '作品加载失败。', 'empty-state'));
    setStatus(message, errorMessage(error), 'error');
  }
}

function addDetailRow(list, label, valueNode) {
  const row = document.createElement('div');
  row.className = 'detail-row';
  row.append(text('dt', label));
  const value = document.createElement('dd');
  value.append(valueNode);
  row.append(value);
  list.append(row);
}

function celebrityName(value) {
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object') return '';
  return value.nickname || value.name || value.celebrity_name || '';
}

async function openDetail(seriesId) {
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  clear(detailContent);
  detailContent.append(text('div', '正在加载详情…', 'loading'));

  try {
    const work = await getWork(seriesId);
    const episodes = await getEpisodes(work.id).catch(() => []);
    clear(detailContent);

    const layout = document.createElement('div');
    layout.className = 'detail-layout';
    layout.append(coverNode(work.series_cover, work.series_name, 'detail-cover'));

    const body = document.createElement('div');
    const title = text('h2', work.series_name, 'detail-title');
    title.id = 'detailTitle';
    body.append(title);

    const list = document.createElement('dl');
    list.className = 'detail-list';
    addDetailRow(list, '状态', statusBadge(work.status));
    addDetailRow(list, '集数', text('span', `${work.episode_cnt ?? work.episode_count ?? 0} 集 ${work.episode_right_text || ''}`.trim()));

    const names = (work.celebrities || []).map(celebrityName).filter(Boolean);
    if (names.length) addDetailRow(list, '演员', text('span', names.join('、')));

    if ((work.tags || []).length) {
      const tags = document.createElement('div');
      tags.className = 'tags-list';
      work.tags.forEach((tag) => tags.append(text('span', tag, 'tag')));
      addDetailRow(list, '标签', tags);
    }
    addDetailRow(list, '简介', text('span', work.series_intro || '（暂无）'));
    addDetailRow(list, '来源 ID', text('span', work.series_id, 'mono'));
    addDetailRow(list, '最近更新', text('span', formatDate(work.updated_at || work.last_seen_at)));
    body.append(list);

    const detailUrl = safeHttpUrl(work.detail_url);
    if (detailUrl) {
      const actions = document.createElement('div');
      actions.className = 'flex-row mt-16';
      const link = text('a', '打开来源详情', 'btn btn-default');
      link.href = detailUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      actions.append(link);
      body.append(actions);
    }

    layout.append(body);
    detailContent.append(layout);

    const episodeTitle = text('h3', '分集', 'mt-16');
    detailContent.append(episodeTitle);
    if (!episodes.length) {
      detailContent.append(text('p', '尚未导入分集明细。', 'text-muted mt-8'));
    } else {
      const episodeList = document.createElement('div');
      episodeList.className = 'episode-list';
      episodes.slice(0, 200).forEach((episode) => {
        episodeList.append(text('div', episode.title || `第${episode.episode_index}集`, 'episode-item'));
      });
      detailContent.append(episodeList);
      if (episodes.length > 200) {
        detailContent.append(text('p', `仅显示前 200 集，共 ${episodes.length} 集。`, 'text-muted mt-8'));
      }
    }
  } catch (error) {
    clear(detailContent);
    detailContent.append(text('div', `详情加载失败：${errorMessage(error)}`, 'empty-state text-danger'));
  }
}

function closeModal() {
  modal.classList.remove('open');
  document.body.style.overflow = '';
}

document.querySelector('#modalClose').addEventListener('click', closeModal);
modal.addEventListener('click', (event) => {
  if (event.target === modal) closeModal();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && modal.classList.contains('open')) closeModal();
});

document.querySelector('#searchForm').addEventListener('submit', (event) => {
  event.preventDefault();
  currentQuery = document.querySelector('#searchInput').value.trim();
  currentStatus = document.querySelector('#statusFilter').value;
  currentTag = document.querySelector('#tagInput').value.trim();
  loadWorks(1);
});

document.querySelector('#resetButton').addEventListener('click', () => {
  document.querySelector('#searchInput').value = '';
  document.querySelector('#tagInput').value = '';
  document.querySelector('#statusFilter').value = 'active';
  currentQuery = '';
  currentTag = '';
  currentStatus = 'active';
  loadWorks(1);
});

async function checkService() {
  const node = document.querySelector('#serviceStatus');
  try {
    const status = await getStatus();
    setStatus(node, `后端 ${status.version || '--'} · ${Number(status.catalog_total || 0).toLocaleString('zh-CN')} 部`, 'success');
  } catch (error) {
    setStatus(node, `服务不可用：${errorMessage(error)}`, 'error');
  }
}

checkService();
loadWorks(1);

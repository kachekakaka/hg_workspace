export function clear(node) {
  node.replaceChildren();
}

export function text(tag, value, className = '') {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value ?? '';
  return node;
}

export function safeHttpUrl(value) {
  if (!value) return '';
  try {
    const url = new URL(String(value), window.location.origin);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : '';
  } catch {
    return '';
  }
}

export function formatDate(value) {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return String(value);
  return date.toLocaleString('zh-CN', { hour12: false });
}

export function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN');
}

export function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

export function setStatus(node, message, kind = '') {
  node.className = `status-line${kind ? ` ${kind}` : ''}`;
  node.textContent = message;
}

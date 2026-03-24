// Toast notification system
const Toast = {
  show(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${_toastIcon(type)}</span>
      <span class="toast-message">${message}</span>
      <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(toast);
    // Trigger transition
    setTimeout(() => toast.classList.add('toast-visible'), 10);
    // Auto-remove
    setTimeout(() => {
      toast.classList.remove('toast-visible');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  success(msg, duration) { this.show(msg, 'success', duration); },
  error(msg, duration)   { this.show(msg, 'error', duration ?? 6000); },
  warn(msg, duration)    { this.show(msg, 'warn', duration); },
  info(msg, duration)    { this.show(msg, 'info', duration); },
};

function _toastIcon(type) {
  return { success: '✓', error: '✕', warn: '⚠', info: 'ℹ' }[type] || 'ℹ';
}

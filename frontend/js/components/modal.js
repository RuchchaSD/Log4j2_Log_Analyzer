// Modal component
const Modal = {
  show(title, bodyHtml, footerHtml = '') {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    document.getElementById('modal-footer').innerHTML = footerHtml;
    document.getElementById('modal-overlay').classList.add('active');
  },

  hide() {
    document.getElementById('modal-overlay').classList.remove('active');
  },

  // Close on backdrop click (but not when clicking inside the dialog)
  handleOverlayClick(event) {
    if (event.target === document.getElementById('modal-overlay')) {
      Modal.hide();
    }
  },
};

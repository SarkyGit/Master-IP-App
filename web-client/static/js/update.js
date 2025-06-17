function startUpdateSocket() {
  const log = document.getElementById('update-log');
  const status = document.getElementById('update-status');
  let failed = false;
  let finished = false;
  const socket = new WebSocket(`ws://${location.host}/ws/update`);

  function closeModal() {
    if (!finished) {
      finished = true;
      status.textContent = failed ? 'Update failed' : 'Update successful';
      if (!failed) {
        fetch('/admin/check-update')
          .then(r => r.json())
          .then(data => {
            const commitEl = document.getElementById('commit-id');
            const statusEl = document.getElementById('update-status-line');
            if (commitEl) commitEl.textContent = data.commit;
            if (statusEl) {
              statusEl.textContent = data.update_available ?
                `Update available (remote ${data.remote})` :
                'System is up to date.';
              if (data.update_available) {
                statusEl.classList.add('text-green-600');
              } else {
                statusEl.classList.remove('text-green-600');
              }
            }
          })
          .catch(() => {});
      }
      setTimeout(() => {
        const modal = document.getElementById('modal');
        if (modal) modal.innerHTML = '';
      }, 2000);
    }
  }

  socket.addEventListener('message', (evt) => {
    log.textContent += evt.data + '\n';
    log.scrollTop = log.scrollHeight;
    status.textContent = evt.data;
    if (/failed/i.test(evt.data)) {
      failed = true;
    }
    if (evt.data === 'DONE') {
      closeModal();
    }
  });

  socket.addEventListener('close', closeModal);
  socket.addEventListener('error', closeModal);

  setTimeout(closeModal, 60000);
}

function startUpdateSocket() {
  const log = document.getElementById('update-log');
  const status = document.getElementById('update-status');
  const error = document.getElementById('update-error');
  const closeBtn = document.getElementById('update-close-btn');
  const retryBtn = document.getElementById('update-retry-btn');
  const restartBtn = document.getElementById('update-restart-btn');
  let failed = false;
  let finished = false;
  let rebooting = false;
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${scheme}://${location.host}/ws/update`);

  function finish() {
    if (finished) return;
    finished = true;
    closeBtn.disabled = false;
    if (failed) {
      status.textContent = 'Update failed';
      if (retryBtn) retryBtn.classList.remove('hidden');
    } else {
      status.textContent = rebooting ?
        'Update complete. Restarting now...' :
        'Update complete. Reloading...';
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
      setTimeout(() => {
        location.reload();
      }, rebooting ? 5000 : 1000);
    }
    if (restartBtn) restartBtn.classList.remove('hidden');
  }

  socket.addEventListener('message', (evt) => {
    log.textContent += evt.data + '\n';
    log.scrollTop = log.scrollHeight;
    status.textContent = evt.data;
    if (/failed/i.test(evt.data)) {
      failed = true;
      if (error) {
        error.textContent = evt.data;
        error.classList.remove('hidden');
      }
    }
    if (/restart failed/i.test(evt.data) && restartBtn) {
      restartBtn.classList.remove('hidden');
    }
    if (/restarting|rebooting/i.test(evt.data)) {
      rebooting = true;
    }
    if (evt.data === 'DONE') {
      finish();
    }
  });

  socket.addEventListener('close', finish);
  socket.addEventListener('error', finish);
  setTimeout(finish, 60000);

  if (retryBtn) {
    retryBtn.addEventListener('click', () => {
      retryBtn.classList.add('hidden');
      if (error) error.classList.add('hidden');
      closeBtn.disabled = true;
      log.textContent = '';
      status.textContent = 'Retrying update...';
      startUpdateSocket();
    }, { once: true });
  }

  if (restartBtn) {
    restartBtn.addEventListener('click', () => {
      restartBtn.disabled = true;
      restartBtn.textContent = 'Restarting...';
      fetch('/admin/restart', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          if (data.status === 'ok') {
            status.textContent = 'Service restarting...';
            setTimeout(() => location.reload(), 2000);
          } else {
            restartBtn.disabled = false;
            restartBtn.textContent = 'Restart service';
            if (error) {
              error.textContent = data.detail || 'Restart failed';
              error.classList.remove('hidden');
            }
          }
        })
        .catch(() => {
          restartBtn.disabled = false;
          restartBtn.textContent = 'Restart service';
          if (error) {
            error.textContent = 'Restart failed';
            error.classList.remove('hidden');
          }
        });
    });
  }
}

function startUpdateSocket() {
  const log = document.getElementById('update-log');
  const socket = new WebSocket(`ws://${location.host}/ws/update`);
  socket.addEventListener('message', (evt) => {
    log.textContent += evt.data + '\n';
    log.scrollTop = log.scrollHeight;
  });
  socket.addEventListener('close', () => {
    log.textContent += '\nUpdate complete.';
  });
}

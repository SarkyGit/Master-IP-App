document.addEventListener('DOMContentLoaded', () => {
  const term = new Terminal({ theme: { background: '#1e1e1e' } });
  const container = document.getElementById('terminal');
  term.open(container);
  term.write('Connecting...\r\n');

  const socket = new WebSocket(`ws://${location.host}/ws/terminal/${window.deviceId}`);

  socket.addEventListener('open', () => term.clear());
  socket.addEventListener('message', (evt) => term.write(evt.data));
  socket.addEventListener('close', () => term.write('\r\n*** Disconnected ***\r\n'));

  term.onData(data => socket.send(data));
});

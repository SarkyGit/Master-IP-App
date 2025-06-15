const DELAY = 200; // ms between lines

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('welcome-cli');
  if (!container) return;
  const lines = Array.from(container.querySelectorAll('.cli-line'));
  lines.forEach(line => {
    line.style.opacity = 0;
  });
  lines.forEach((line, idx) => {
    setTimeout(() => {
      line.style.opacity = 1;
    }, DELAY * idx);
  });
});

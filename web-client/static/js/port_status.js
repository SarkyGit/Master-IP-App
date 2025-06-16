
document.addEventListener('DOMContentLoaded', () => {
  const deviceId = window.deviceId;

  function formatRate(bps) {
    if (bps >= 1e9) return (bps / 1e9).toFixed(2) + ' Gb';
    if (bps >= 1e6) return (bps / 1e6).toFixed(2) + ' Mb';
    if (bps >= 1e3) return Math.round(bps / 1e3) + ' Kb';
    return bps + ' b';
  }

  async function updateRates() {
    try {
      const resp = await fetch(`/api/devices/${deviceId}/port-rates`);
      if (!resp.ok) return;
      const data = await resp.json();
      for (const [name, vals] of Object.entries(data)) {
        const id = `port-${name.replace(/\//g, '-')}`;
        const el = document.getElementById(id);
        if (!el) continue;
        const rateEl = el.querySelector('.port-rate');
        const rx = formatRate(vals.rx_bps);
        const tx = formatRate(vals.tx_bps);
        rateEl.textContent = `${rx}/${tx}`;
      }
    } catch (err) {
      console.error(err);
    }
  }

  updateRates();
  setInterval(updateRates, 5000);
});


function money(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString();
  if (Math.abs(v) >= 10) return v.toFixed(2);
  return v.toFixed(4);
}

function drawSparkline(el, points, big = false) {
  if (!points || points.length < 2) return;

  const width = Math.max(el.clientWidth || 640, 320);
  const height = big ? 340 : 140;
  const padX = big ? 48 : 16;
  const padY = big ? 30 : 14;

  const values = points.map(p => p.close);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const step = (width - padX * 2) / (points.length - 1);
  const coords = points.map((p, i) => {
    const x = padX + i * step;
    const y = height - padY - ((p.close - min) / range) * (height - padY * 2);
    return [x, y, p.close, p.date];
  });

  const d = coords
    .map((c, i) => `${i === 0 ? "M" : "L"}${c[0].toFixed(2)},${c[1].toFixed(2)}`)
    .join(" ");

  const last = coords[coords.length - 1];
  const high = coords.reduce((a, b) => (b[2] > a[2] ? b : a), coords[0]);
  const low = coords.reduce((a, b) => (b[2] < a[2] ? b : a), coords[0]);

  const grid = big
    ? `
      <line class="grid-line" x1="${padX}" y1="${padY}" x2="${width - padX}" y2="${padY}"></line>
      <line class="grid-line" x1="${padX}" y1="${height / 2}" x2="${width - padX}" y2="${height / 2}"></line>
      <line class="grid-line" x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}"></line>
    `
    : `
      <line class="grid-line" x1="${padX}" y1="${height / 2}" x2="${width - padX}" y2="${height / 2}"></line>
    `;

  const labels = big
    ? `
      <text class="chart-label" x="${padX}" y="${padY - 8}">고점 ${money(max)}</text>
      <text class="chart-label" x="${padX}" y="${height - 8}">저점 ${money(min)}</text>
      <text class="chart-label end" x="${width - padX}" y="${last[1] - 10}">현재 ${money(last[2])}</text>
    `
    : "";

  el.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <linearGradient id="lineGlow" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#22d3ee"></stop>
          <stop offset="50%" stop-color="#8b5cf6"></stop>
          <stop offset="100%" stop-color="#34d399"></stop>
        </linearGradient>
      </defs>

      ${grid}
      <path class="area" d="${d} L ${width - padX},${height - padY} L ${padX},${height - padY} Z"></path>
      <path class="glow" d="${d}"></path>
      <path class="line" d="${d}"></path>

      <circle class="dot high-dot" cx="${high[0]}" cy="${high[1]}" r="${big ? 4 : 3}"></circle>
      <circle class="dot low-dot" cx="${low[0]}" cy="${low[1]}" r="${big ? 4 : 3}"></circle>
      <circle class="dot last-dot" cx="${last[0]}" cy="${last[1]}" r="${big ? 5 : 4}"></circle>

      ${labels}
    </svg>
  `;
}

document.querySelectorAll(".mini-chart").forEach(el => {
  try {
    drawSparkline(el, JSON.parse(el.dataset.points), false);
  } catch (e) {}
});

document.querySelectorAll(".big-chart").forEach(el => {
  try {
    drawSparkline(el, JSON.parse(el.dataset.points), true);
  } catch (e) {}
});

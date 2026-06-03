function money(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString();
  if (Math.abs(v) >= 10) return v.toFixed(2);
  return v.toFixed(4);
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function movingAverage(values, window) {
  const out = [];
  let sum = 0;

  for (let i = 0; i < values.length; i++) {
    sum += values[i];

    if (i >= window) {
      sum -= values[i - window];
    }

    if (i >= window - 1) {
      out.push(sum / window);
    } else {
      out.push(null);
    }
  }

  return out;
}

function pathFromCoords(coords) {
  return coords
    .filter(c => c && Number.isFinite(c[0]) && Number.isFinite(c[1]))
    .map((c, i) => `${i === 0 ? "M" : "L"}${c[0].toFixed(2)},${c[1].toFixed(2)}`)
    .join(" ");
}

function drawSparkline(el, points, big = false) {
  if (!points || points.length < 2) return;

  const width = Math.max(el.clientWidth || 640, 320);
  const height = big ? 380 : 140;

  const padLeft = big ? 48 : 16;
  const padRight = big ? 76 : 16;
  const padTop = big ? 28 : 14;
  const padBottom = big ? 34 : 14;

  const maData = parseJSON(el.dataset.ma, []);
  const fibData = parseJSON(el.dataset.fib, []);

  const showMA = el.dataset.showMa !== "false";
  const showFib = el.dataset.showFib !== "false";
  const showLabels = el.dataset.showLabels !== "false";

  const values = points.map(p => Number(p.close)).filter(v => Number.isFinite(v));

  const overlayValues = [];
  maData.forEach(item => {
    const v = Number(item.value);
    if (Number.isFinite(v)) overlayValues.push(v);
  });
  fibData.forEach(item => {
    const v = Number(item.price);
    if (Number.isFinite(v)) overlayValues.push(v);
  });

  const minRaw = Math.min(...values, ...(big ? overlayValues : []));
  const maxRaw = Math.max(...values, ...(big ? overlayValues : []));
  const extra = (maxRaw - minRaw || 1) * 0.08;
  const min = minRaw - extra;
  const max = maxRaw + extra;
  const range = max - min || 1;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const xFor = i => padLeft + (i / (points.length - 1)) * chartW;
  const yFor = value => padTop + (1 - ((value - min) / range)) * chartH;

  const coords = points.map((p, i) => [xFor(i), yFor(Number(p.close)), Number(p.close), p.date]);
  const d = pathFromCoords(coords);

  const last = coords[coords.length - 1];
  const high = coords.reduce((a, b) => (b[2] > a[2] ? b : a), coords[0]);
  const low = coords.reduce((a, b) => (b[2] < a[2] ? b : a), coords[0]);

  const gridCount = big ? 5 : 2;
  const gridLines = [];
  const axisLabels = [];

  for (let i = 0; i < gridCount; i++) {
    const ratio = i / (gridCount - 1);
    const y = padTop + ratio * chartH;
    const price = max - ratio * range;

    gridLines.push(`<line class="grid-line" x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}"></line>`);

    if (big) {
      axisLabels.push(`
        <text class="axis-label" x="${width - padRight + 12}" y="${y + 4}">${money(price)}</text>
      `);
    }
  }

  const maOverlays = [];
  if (big && showMA) {
    const closeValues = points.map(p => Number(p.close));

    [20, 60, 200].forEach(window => {
      if (closeValues.length >= Math.min(window, 10)) {
        const maValues = movingAverage(closeValues, Math.min(window, closeValues.length));
        const maCoords = maValues.map((v, i) => v === null ? null : [xFor(i), yFor(v)]);
        const maPath = pathFromCoords(maCoords);

        if (maPath) {
          maOverlays.push(`<path class="ma-line ma-${window}" d="${maPath}"></path>`);
        }
      }
    });

    maData.forEach(item => {
      const price = Number(item.value);
      if (!Number.isFinite(price)) return;

      const y = yFor(price);
      maOverlays.push(`
        <line class="ma-level" x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}"></line>
        <text class="overlay-label ma-label" x="${width - padRight - 6}" y="${y - 6}">${item.label} ${money(price)}</text>
      `);
    });
  }

  const fibOverlays = [];
  if (big && showFib) {
    fibData.forEach(item => {
      const price = Number(item.price);
      if (!Number.isFinite(price)) return;

      const y = yFor(price);
      fibOverlays.push(`
        <line class="fib-overlay" x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}"></line>
        <text class="overlay-label fib-label" x="${padLeft + 8}" y="${y - 6}">피보 ${item.label} · ${money(price)}</text>
      `);
    });
  }

  const labels = big && showLabels
    ? `
      <text class="chart-label" x="${padLeft}" y="${padTop - 8}">고점 ${money(high[2])}</text>
      <text class="chart-label" x="${padLeft}" y="${height - 10}">저점 ${money(low[2])}</text>
      <text class="chart-label end" x="${width - padRight}" y="${last[1] - 10}">현재 ${money(last[2])}</text>
    `
    : "";

  const hoverLayer = big
    ? `
      <line class="crosshair-x" x1="${padLeft}" y1="${padTop}" x2="${padLeft}" y2="${height - padBottom}"></line>
      <line class="crosshair-y" x1="${padLeft}" y1="${padTop}" x2="${width - padRight}" y2="${padTop}"></line>
      <circle class="hover-dot" cx="${padLeft}" cy="${padTop}" r="5"></circle>
      <rect class="tooltip-bg" x="${padLeft + 12}" y="${padTop + 12}" width="160" height="54" rx="10"></rect>
      <text class="tooltip-date" x="${padLeft + 24}" y="${padTop + 34}"></text>
      <text class="tooltip-price" x="${padLeft + 24}" y="${padTop + 54}"></text>
      <rect class="hover-capture" x="${padLeft}" y="${padTop}" width="${chartW}" height="${chartH}"></rect>
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

      ${gridLines.join("")}
      ${axisLabels.join("")}

      <path class="area" d="${d} L ${width - padRight},${height - padBottom} L ${padLeft},${height - padBottom} Z"></path>
      <path class="glow" d="${d}"></path>
      <path class="line" d="${d}"></path>

      ${fibOverlays.join("")}
      ${maOverlays.join("")}

      <circle class="dot high-dot" cx="${high[0]}" cy="${high[1]}" r="${big ? 4 : 3}"></circle>
      <circle class="dot low-dot" cx="${low[0]}" cy="${low[1]}" r="${big ? 4 : 3}"></circle>
      <circle class="dot last-dot" cx="${last[0]}" cy="${last[1]}" r="${big ? 5 : 4}"></circle>

      ${labels}
      ${hoverLayer}
    </svg>
  `;

  if (big) {
    attachHover(el, points, coords, { padLeft, padTop, padRight, padBottom, width, height, chartW, chartH });
  }
}

function attachHover(el, points, coords, dims) {
  const svg = el.querySelector("svg");
  const capture = el.querySelector(".hover-capture");
  if (!svg || !capture) return;

  const cx = el.querySelector(".crosshair-x");
  const cy = el.querySelector(".crosshair-y");
  const dot = el.querySelector(".hover-dot");
  const bg = el.querySelector(".tooltip-bg");
  const dateText = el.querySelector(".tooltip-date");
  const priceText = el.querySelector(".tooltip-price");

  const hoverEls = [cx, cy, dot, bg, dateText, priceText];

  function setVisible(show) {
    hoverEls.forEach(x => {
      if (x) x.style.opacity = show ? "1" : "0";
    });
  }

  setVisible(false);

  capture.addEventListener("mousemove", event => {
    const rect = svg.getBoundingClientRect();
    const ratioX = (event.clientX - rect.left) / rect.width;
    const svgX = ratioX * dims.width;

    const clampedX = clamp(svgX, dims.padLeft, dims.width - dims.padRight);
    const index = Math.round(((clampedX - dims.padLeft) / dims.chartW) * (points.length - 1));
    const safeIndex = clamp(index, 0, points.length - 1);
    const c = coords[safeIndex];

    if (!c) return;

    const x = c[0];
    const y = c[1];

    cx.setAttribute("x1", x);
    cx.setAttribute("x2", x);
    cy.setAttribute("y1", y);
    cy.setAttribute("y2", y);
    dot.setAttribute("cx", x);
    dot.setAttribute("cy", y);

    let tooltipX = x + 14;
    let tooltipY = y - 70;

    if (tooltipX > dims.width - dims.padRight - 170) tooltipX = x - 176;
    if (tooltipY < dims.padTop + 8) tooltipY = y + 18;

    bg.setAttribute("x", tooltipX);
    bg.setAttribute("y", tooltipY);
    dateText.setAttribute("x", tooltipX + 12);
    dateText.setAttribute("y", tooltipY + 22);
    priceText.setAttribute("x", tooltipX + 12);
    priceText.setAttribute("y", tooltipY + 43);

    dateText.textContent = c[3];
    priceText.textContent = `가격 ${money(c[2])}`;

    setVisible(true);
  });

  capture.addEventListener("mouseleave", () => setVisible(false));
}

function parseJSON(value, fallback) {
  try {
    if (!value) return fallback;
    return JSON.parse(value);
  } catch (e) {
    return fallback;
  }
}

function redrawInteractiveChart(container) {
  const chart = container.closest(".panel").querySelector(".interactive-chart");
  if (!chart) return;

  const points = parseJSON(chart.dataset.points, []);
  drawSparkline(chart, points, true);
}

document.querySelectorAll(".mini-chart").forEach(el => {
  try {
    drawSparkline(el, parseJSON(el.dataset.points, []), false);
  } catch (e) {}
});

document.querySelectorAll(".big-chart").forEach(el => {
  try {
    drawSparkline(el, parseJSON(el.dataset.points, []), true);
  } catch (e) {}
});

document.querySelectorAll(".chart-toggle").forEach(button => {
  button.addEventListener("click", () => {
    button.classList.toggle("active");

    const toolbar = button.closest(".chart-toolbar");
    const panel = button.closest(".panel");
    const chart = panel.querySelector(".interactive-chart");
    if (!chart) return;

    const overlay = button.dataset.overlay;
    const active = button.classList.contains("active");

    if (overlay === "ma") chart.dataset.showMa = String(active);
    if (overlay === "fib") chart.dataset.showFib = String(active);
    if (overlay === "labels") chart.dataset.showLabels = String(active);

    drawSparkline(chart, parseJSON(chart.dataset.points, []), true);
  });
});

window.addEventListener("resize", () => {
  document.querySelectorAll(".mini-chart").forEach(el => {
    drawSparkline(el, parseJSON(el.dataset.points, []), false);
  });

  document.querySelectorAll(".big-chart").forEach(el => {
    drawSparkline(el, parseJSON(el.dataset.points, []), true);
  });
});

function money(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString();
  if (Math.abs(v) >= 10) return v.toFixed(2);
  return v.toFixed(4);
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function parseJSON(value, fallback) {
  try {
    if (!value) return fallback;
    return JSON.parse(value);
  } catch (e) {
    return fallback;
  }
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

function getWindowedPoints(el, points) {
  if (!points || points.length < 2) return points || [];

  let start = Number(el.dataset.windowStart);
  let end = Number(el.dataset.windowEnd);

  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) {
    start = 0;
    end = points.length - 1;
    el.dataset.windowStart = String(start);
    el.dataset.windowEnd = String(end);
  }

  start = clamp(Math.round(start), 0, points.length - 2);
  end = clamp(Math.round(end), start + 1, points.length - 1);

  el.dataset.windowStart = String(start);
  el.dataset.windowEnd = String(end);

  return points.slice(start, end + 1);
}

function setRange(el, days) {
  const points = parseJSON(el.dataset.points, []);
  if (!points.length) return;

  if (days === "all") {
    el.dataset.windowStart = "0";
    el.dataset.windowEnd = String(points.length - 1);
  } else {
    const n = Number(days);
    const length = Math.min(points.length, n);
    el.dataset.windowStart = String(Math.max(0, points.length - length));
    el.dataset.windowEnd = String(points.length - 1);
  }

  drawSparkline(el, points, true);
}

function drawSparkline(el, rawPoints, big = false) {
  if (!rawPoints || rawPoints.length < 2) return;

  const allPoints = rawPoints;
  const points = big ? getWindowedPoints(el, allPoints) : allPoints;

  if (!points || points.length < 2) return;

  const width = Math.max(el.clientWidth || 640, 320);
  const height = big ? 420 : 140;

  const padLeft = big ? 54 : 16;
  const padRight = big ? 82 : 16;
  const padTop = big ? 30 : 14;
  const padBottom = big ? 46 : 14;

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

  const gridCount = big ? 6 : 2;
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

  if (big) {
    const dateLabels = [
      { i: 0, anchor: "start" },
      { i: Math.floor(points.length / 2), anchor: "middle" },
      { i: points.length - 1, anchor: "end" },
    ];

    dateLabels.forEach(x => {
      const c = coords[x.i];
      if (!c) return;
      axisLabels.push(`
        <text class="date-axis-label" text-anchor="${x.anchor}" x="${c[0]}" y="${height - 12}">${c[3]}</text>
      `);
    });
  }

  const startIndex = Number(el.dataset.windowStart || 0);

  const maOverlays = [];
  if (big && showMA) {
    const closeValuesAll = allPoints.map(p => Number(p.close));

    [20, 60, 200].forEach(window => {
      if (closeValuesAll.length >= Math.min(window, 10)) {
        const allMaValues = movingAverage(closeValuesAll, Math.min(window, closeValuesAll.length));
        const visibleMaValues = allMaValues.slice(startIndex, startIndex + points.length);
        const maCoords = visibleMaValues.map((v, i) => v === null ? null : [xFor(i), yFor(v)]);
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
      if (y < padTop || y > height - padBottom) return;

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
      if (y < padTop || y > height - padBottom) return;

      fibOverlays.push(`
        <line class="fib-overlay" x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}"></line>
        <text class="overlay-label fib-label" x="${padLeft + 8}" y="${y - 6}">피보 ${item.label} · ${money(price)}</text>
      `);
    });
  }

  const labels = big && showLabels
    ? `
      <text class="chart-label" x="${padLeft}" y="${padTop - 8}">구간 고점 ${money(high[2])}</text>
      <text class="chart-label" x="${padLeft}" y="${height - 26}">구간 저점 ${money(low[2])}</text>
      <text class="chart-label end" x="${width - padRight}" y="${last[1] - 10}">현재 ${money(last[2])}</text>
    `
    : "";

  const hoverLayer = big
    ? `
      <line class="crosshair-x" x1="${padLeft}" y1="${padTop}" x2="${padLeft}" y2="${height - padBottom}"></line>
      <line class="crosshair-y" x1="${padLeft}" y1="${padTop}" x2="${width - padRight}" y2="${padTop}"></line>
      <circle class="hover-dot" cx="${padLeft}" cy="${padTop}" r="5"></circle>
      <rect class="tooltip-bg" x="${padLeft + 12}" y="${padTop + 12}" width="168" height="56" rx="10"></rect>
      <text class="tooltip-date" x="${padLeft + 24}" y="${padTop + 34}"></text>
      <text class="tooltip-price" x="${padLeft + 24}" y="${padTop + 55}"></text>
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
    attachHoverAndZoom(el, allPoints, points, coords, { padLeft, padTop, padRight, padBottom, width, height, chartW, chartH });
  }
}

function attachHoverAndZoom(el, allPoints, points, coords, dims) {
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

  let dragging = false;
  let dragStartX = 0;
  let dragStartStart = 0;
  let dragStartEnd = 0;

  capture.addEventListener("mousemove", event => {
    const rect = svg.getBoundingClientRect();
    const ratioX = (event.clientX - rect.left) / rect.width;
    const svgX = ratioX * dims.width;

    if (dragging) {
      const currentX = event.clientX;
      const dx = currentX - dragStartX;
      const visibleCount = dragStartEnd - dragStartStart + 1;
      const shift = Math.round((-dx / rect.width) * visibleCount * 1.6);

      let nextStart = dragStartStart + shift;
      let nextEnd = dragStartEnd + shift;

      if (nextStart < 0) {
        nextEnd -= nextStart;
        nextStart = 0;
      }

      if (nextEnd > allPoints.length - 1) {
        const overflow = nextEnd - (allPoints.length - 1);
        nextStart -= overflow;
        nextEnd = allPoints.length - 1;
      }

      nextStart = clamp(nextStart, 0, Math.max(0, allPoints.length - 2));
      nextEnd = clamp(nextEnd, nextStart + 1, allPoints.length - 1);

      el.dataset.windowStart = String(nextStart);
      el.dataset.windowEnd = String(nextEnd);
      drawSparkline(el, allPoints, true);
      return;
    }

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
    let tooltipY = y - 72;

    if (tooltipX > dims.width - dims.padRight - 180) tooltipX = x - 186;
    if (tooltipY < dims.padTop + 8) tooltipY = y + 18;

    bg.setAttribute("x", tooltipX);
    bg.setAttribute("y", tooltipY);
    dateText.setAttribute("x", tooltipX + 12);
    dateText.setAttribute("y", tooltipY + 23);
    priceText.setAttribute("x", tooltipX + 12);
    priceText.setAttribute("y", tooltipY + 45);

    dateText.textContent = c[3];
    priceText.textContent = `가격 ${money(c[2])}`;

    setVisible(true);
  });

  capture.addEventListener("mouseleave", () => {
    if (!dragging) setVisible(false);
  });

  capture.addEventListener("mousedown", event => {
    event.preventDefault();
    dragging = true;
    dragStartX = event.clientX;
    dragStartStart = Number(el.dataset.windowStart || 0);
    dragStartEnd = Number(el.dataset.windowEnd || allPoints.length - 1);
    capture.classList.add("dragging");
  });

  window.addEventListener("mouseup", () => {
    dragging = false;
    capture.classList.remove("dragging");
  }, { once: true });

  capture.addEventListener("wheel", event => {
    event.preventDefault();

    const total = allPoints.length;
    let start = Number(el.dataset.windowStart || 0);
    let end = Number(el.dataset.windowEnd || total - 1);

    const visible = end - start + 1;
    const minVisible = Math.min(30, total);
    const zoomIn = event.deltaY < 0;
    const factor = zoomIn ? 0.82 : 1.22;
    let nextVisible = Math.round(visible * factor);

    nextVisible = clamp(nextVisible, minVisible, total);

    const rect = svg.getBoundingClientRect();
    const ratio = clamp((event.clientX - rect.left) / rect.width, 0, 1);
    const center = start + ratio * visible;

    let nextStart = Math.round(center - nextVisible * ratio);
    let nextEnd = nextStart + nextVisible - 1;

    if (nextStart < 0) {
      nextEnd -= nextStart;
      nextStart = 0;
    }

    if (nextEnd > total - 1) {
      const overflow = nextEnd - (total - 1);
      nextStart -= overflow;
      nextEnd = total - 1;
    }

    nextStart = clamp(nextStart, 0, Math.max(0, total - 2));
    nextEnd = clamp(nextEnd, nextStart + 1, total - 1);

    el.dataset.windowStart = String(nextStart);
    el.dataset.windowEnd = String(nextEnd);
    drawSparkline(el, allPoints, true);
  }, { passive: false });

  capture.addEventListener("dblclick", event => {
    event.preventDefault();
    el.dataset.windowStart = "0";
    el.dataset.windowEnd = String(allPoints.length - 1);

    const panel = el.closest(".panel");
    panel?.querySelectorAll(".range-button").forEach(btn => btn.classList.remove("active"));

    drawSparkline(el, allPoints, true);
  });
}

document.querySelectorAll(".mini-chart").forEach(el => {
  try {
    drawSparkline(el, parseJSON(el.dataset.points, []), false);
  } catch (e) {}
});

document.querySelectorAll(".big-chart").forEach(el => {
  try {
    const points = parseJSON(el.dataset.points, []);
    if (el.classList.contains("interactive-chart")) {
      setRange(el, "1825");
    } else {
      drawSparkline(el, points, true);
    }
  } catch (e) {}
});

document.querySelectorAll(".chart-toggle").forEach(button => {
  button.addEventListener("click", () => {
    button.classList.toggle("active");

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

document.querySelectorAll(".range-button").forEach(button => {
  button.addEventListener("click", () => {
    const panel = button.closest(".panel");
    const chart = panel.querySelector(".interactive-chart");
    if (!chart) return;

    panel.querySelectorAll(".range-button").forEach(btn => btn.classList.remove("active"));
    button.classList.add("active");

    setRange(chart, button.dataset.range);
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

function money(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString();
  if (Math.abs(v) >= 10) return v.toFixed(2);
  return v.toFixed(4);
}

function parseJSON(value, fallback) {
  try {
    if (!value) return fallback;
    return JSON.parse(value);
  } catch (e) {
    return fallback;
  }
}

function movingAverageData(data, window) {
  const result = [];
  let sum = 0;

  for (let i = 0; i < data.length; i++) {
    sum += data[i].value;

    if (i >= window) {
      sum -= data[i - window].value;
    }

    if (i >= window - 1) {
      result.push({
        time: data[i].time,
        value: sum / window,
      });
    }
  }

  return result;
}

function svgPath(coords) {
  return coords
    .filter(c => c && Number.isFinite(c[0]) && Number.isFinite(c[1]))
    .map((c, i) => `${i === 0 ? "M" : "L"}${c[0].toFixed(2)},${c[1].toFixed(2)}`)
    .join(" ");
}

function drawMiniChart(el, points) {
  if (!points || points.length < 2) return;

  const width = Math.max(el.clientWidth || 360, 220);
  const height = 140;
  const pad = 12;

  const values = points.map(p => Number(p.close)).filter(v => Number.isFinite(v));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const xFor = i => pad + (i / (points.length - 1)) * (width - pad * 2);
  const yFor = value => pad + (1 - ((value - min) / range)) * (height - pad * 2);

  const coords = points.map((p, i) => [xFor(i), yFor(Number(p.close)), Number(p.close)]);
  const d = svgPath(coords);

  const high = coords.reduce((a, b) => (b[2] > a[2] ? b : a), coords[0]);
  const low = coords.reduce((a, b) => (b[2] < a[2] ? b : a), coords[0]);
  const last = coords[coords.length - 1];

  el.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <linearGradient id="miniLineGlow" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#22d3ee"></stop>
          <stop offset="50%" stop-color="#8b5cf6"></stop>
          <stop offset="100%" stop-color="#34d399"></stop>
        </linearGradient>
      </defs>
      <path class="area" d="${d} L ${width - pad},${height - pad} L ${pad},${height - pad} Z"></path>
      <path class="glow" d="${d}"></path>
      <path class="line" d="${d}"></path>
      <circle class="dot high-dot" cx="${high[0]}" cy="${high[1]}" r="3"></circle>
      <circle class="dot low-dot" cx="${low[0]}" cy="${low[1]}" r="3"></circle>
      <circle class="dot last-dot" cx="${last[0]}" cy="${last[1]}" r="4"></circle>
    </svg>
  `;
}

const chartStore = new WeakMap();

function initTradingChart(el) {
  const points = parseJSON(el.dataset.points, []);
  if (!points || points.length < 2) return;

  if (!window.LightweightCharts) {
    el.innerHTML = `<div class="chart-fallback">차트 라이브러리를 불러오지 못했습니다. 인터넷 연결 또는 CDN 차단 여부를 확인해 주세요.</div>`;
    return;
  }

  const maRaw = parseJSON(el.dataset.ma, []);
  const fibRaw = parseJSON(el.dataset.fib, []);

  const data = points
    .map(p => ({
      time: p.date,
      value: Number(p.close),
    }))
    .filter(p => p.time && Number.isFinite(p.value));

  if (data.length < 2) return;

  el.innerHTML = "";

  const chart = LightweightCharts.createChart(el, {
    width: el.clientWidth || 800,
    height: el.clientHeight || 460,
    layout: {
      background: { type: "solid", color: "transparent" },
      textColor: "#94a3b8",
      fontFamily: "Inter, system-ui, sans-serif",
    },
    grid: {
      vertLines: { color: "rgba(148, 163, 184, 0.08)" },
      horzLines: { color: "rgba(148, 163, 184, 0.10)" },
    },
    rightPriceScale: {
      visible: true,
      borderColor: "rgba(148, 163, 184, 0.18)",
      scaleMargins: { top: 0.12, bottom: 0.18 },
    },
    timeScale: {
      visible: true,
      borderColor: "rgba(148, 163, 184, 0.18)",
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 8,
      barSpacing: 6,
      fixLeftEdge: false,
      fixRightEdge: false,
      lockVisibleTimeRangeOnResize: true,
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: {
        color: "rgba(226, 232, 240, 0.42)",
        width: 1,
        style: LightweightCharts.LineStyle.Dashed,
        labelBackgroundColor: "#0f172a",
      },
      horzLine: {
        color: "rgba(226, 232, 240, 0.42)",
        width: 1,
        style: LightweightCharts.LineStyle.Dashed,
        labelBackgroundColor: "#0f172a",
      },
    },
    handleScroll: {
      mouseWheel: true,
      pressedMouseMove: true,
      horzTouchDrag: true,
      vertTouchDrag: true,
    },
    handleScale: {
      axisPressedMouseMove: true,
      mouseWheel: true,
      pinch: true,
    },
    localization: {
      priceFormatter: price => money(price),
    },
  });

  const priceSeries = chart.addAreaSeries({
    lineColor: "#22d3ee",
    topColor: "rgba(34, 211, 238, 0.24)",
    bottomColor: "rgba(34, 211, 238, 0.03)",
    lineWidth: 2,
    priceLineVisible: true,
    lastValueVisible: true,
    crosshairMarkerVisible: true,
    crosshairMarkerRadius: 5,
  });

  priceSeries.setData(data);

  const maSeries = [];

  const ma20 = chart.addLineSeries({
    color: "#22d3ee",
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false,
  });
  ma20.setData(movingAverageData(data, 20));
  maSeries.push(ma20);

  const ma60 = chart.addLineSeries({
    color: "#a78bfa",
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false,
  });
  ma60.setData(movingAverageData(data, 60));
  maSeries.push(ma60);

  const ma200 = chart.addLineSeries({
    color: "#f59e0b",
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false,
  });
  ma200.setData(movingAverageData(data, 200));
  maSeries.push(ma200);

  const fibLines = [];
  fibRaw.forEach(level => {
    const price = Number(level.price);
    if (!Number.isFinite(price)) return;

    const line = priceSeries.createPriceLine({
      price,
      color: "rgba(167, 139, 250, 0.72)",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true,
      title: `피보 ${level.label}`,
    });

    fibLines.push(line);
  });

  const high = data.reduce((a, b) => (b.value > a.value ? b : a), data[0]);
  const low = data.reduce((a, b) => (b.value < a.value ? b : a), data[0]);

  priceSeries.createPriceLine({
    price: high.value,
    color: "rgba(52, 211, 153, 0.7)",
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: "구간 고점",
  });

  priceSeries.createPriceLine({
    price: low.value,
    color: "rgba(251, 113, 133, 0.7)",
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: "구간 저점",
  });

  const state = {
    chart,
    priceSeries,
    maSeries,
    fibLines,
    data,
    maVisible: true,
    fibVisible: true,
  };

  chartStore.set(el, state);
  setChartRange(el, "1825");
}

function setChartRange(el, days) {
  const state = chartStore.get(el);
  if (!state) return;

  const { chart, data } = state;

  if (days === "all") {
    chart.timeScale().fitContent();
    return;
  }

  const n = Number(days);
  const length = Math.min(data.length, n);
  const fromIndex = Math.max(0, data.length - length);
  const from = data[fromIndex].time;
  const to = data[data.length - 1].time;

  chart.timeScale().setVisibleRange({ from, to });
}

function resetTradingChart(el) {
  const state = chartStore.get(el);
  if (!state) return;

  state.chart.timeScale().fitContent();
  state.chart.priceScale("right").applyOptions({
    autoScale: true,
  });
}

function setOverlay(el, overlay, active) {
  const state = chartStore.get(el);
  if (!state) return;

  if (overlay === "ma") {
    state.maVisible = active;

    state.maSeries.forEach(series => {
      series.applyOptions({
        visible: active,
      });
    });
  }

  if (overlay === "fib") {
    state.fibVisible = active;

    state.fibLines.forEach(line => {
      state.priceSeries.removePriceLine(line);
    });

    state.fibLines = [];

    if (active) {
      const fibRaw = parseJSON(el.dataset.fib, []);
      fibRaw.forEach(level => {
        const price = Number(level.price);
        if (!Number.isFinite(price)) return;

        const line = state.priceSeries.createPriceLine({
          price,
          color: "rgba(167, 139, 250, 0.72)",
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Dashed,
          axisLabelVisible: true,
          title: `피보 ${level.label}`,
        });

        state.fibLines.push(line);
      });
    }
  }
}

document.querySelectorAll(".mini-chart").forEach(el => {
  drawMiniChart(el, parseJSON(el.dataset.points, []));
});

document.querySelectorAll(".trading-chart").forEach(el => {
  initTradingChart(el);
});

document.querySelectorAll(".chart-toggle").forEach(button => {
  button.addEventListener("click", () => {
    button.classList.toggle("active");

    const panel = button.closest(".panel");
    const chart = panel.querySelector(".trading-chart");
    if (!chart) return;

    setOverlay(chart, button.dataset.overlay, button.classList.contains("active"));
  });
});

document.querySelectorAll(".range-button").forEach(button => {
  button.addEventListener("click", () => {
    const panel = button.closest(".panel");
    const chart = panel.querySelector(".trading-chart");
    if (!chart) return;

    if (button.dataset.action === "reset-view") {
      panel.querySelectorAll(".range-button").forEach(btn => btn.classList.remove("active"));
      resetTradingChart(chart);
      return;
    }

    panel.querySelectorAll(".range-button").forEach(btn => btn.classList.remove("active"));
    button.classList.add("active");
    setChartRange(chart, button.dataset.range);
  });
});

window.addEventListener("resize", () => {
  document.querySelectorAll(".trading-chart").forEach(el => {
    const state = chartStore.get(el);
    if (!state) return;

    state.chart.applyOptions({
      width: el.clientWidth || 800,
      height: el.clientHeight || 460,
    });
  });

  document.querySelectorAll(".mini-chart").forEach(el => {
    drawMiniChart(el, parseJSON(el.dataset.points, []));
  });
});

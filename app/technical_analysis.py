from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


def _safe_float(value):
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _pct_diff(price, base):
    if price is None or base in (None, 0):
        return None
    return (price / base - 1) * 100


def _fmt_price(value):
    if value is None:
        return "-"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:,.2f}"
    return f"{value:,.4f}"


def moving_average_analysis(df: pd.DataFrame) -> dict[str, Any]:
    """
    이동평균 분석.
    기존 사이클 계산과 분리해서 독립적으로 동작하게 만들었습니다.
    """
    if df.empty or "Close" not in df:
        return {
            "available": False,
            "summary": "이동평균을 계산할 가격 데이터가 부족합니다.",
            "items": [],
            "state": "데이터 부족",
        }

    close = df["Close"].dropna()
    if close.empty:
        return {
            "available": False,
            "summary": "이동평균을 계산할 가격 데이터가 부족합니다.",
            "items": [],
            "state": "데이터 부족",
        }

    current = _safe_float(close.iloc[-1])

    windows = [20, 60, 200]
    items = []

    for window in windows:
        if len(close) >= window:
            ma = _safe_float(close.rolling(window).mean().iloc[-1])
            diff = _pct_diff(current, ma)
            position = "위" if diff is not None and diff >= 0 else "아래"
            items.append(
                {
                    "window": window,
                    "label": f"{window}일선",
                    "value": ma,
                    "diff_pct": diff,
                    "position": position,
                }
            )
        else:
            items.append(
                {
                    "window": window,
                    "label": f"{window}일선",
                    "value": None,
                    "diff_pct": None,
                    "position": "데이터 부족",
                }
            )

    ma20 = next((x["value"] for x in items if x["window"] == 20), None)
    ma60 = next((x["value"] for x in items if x["window"] == 60), None)
    ma200 = next((x["value"] for x in items if x["window"] == 200), None)

    above_count = sum(1 for x in items if x["diff_pct"] is not None and x["diff_pct"] >= 0)

    if ma20 and ma60 and ma200 and current:
        if current > ma20 > ma60 > ma200:
            state = "강한 상승 배열"
            summary = "현재가가 20일선, 60일선, 200일선 위에 있고 단기선이 장기선보다 위에 있습니다. 추세가 비교적 강한 구조입니다."
            score = 90
        elif current > ma200 and above_count >= 2:
            state = "상승 추세 유지"
            summary = "현재가가 장기 기준선 위에 있습니다. 단기 흔들림은 있어도 큰 추세는 아직 유지되는 쪽에 가깝습니다."
            score = 72
        elif current > ma200:
            state = "장기선 위의 혼조"
            summary = "현재가가 200일선 위에 있지만 단기·중기 흐름은 엇갈립니다. 방향 확인이 더 필요한 구간입니다."
            score = 58
        elif current < ma20 < ma60 < ma200:
            state = "강한 하락 배열"
            summary = "현재가가 주요 이동평균 아래에 있고 단기선이 장기선보다 아래에 있습니다. 추세 회복 전까지는 보수적으로 봐야 하는 구조입니다."
            score = 20
        else:
            state = "하락 또는 회복 대기"
            summary = "현재가가 장기 기준선 아래에 있습니다. 반등이 나오더라도 추세 회복 여부를 확인해야 합니다."
            score = 36
    else:
        state = "부분 데이터"
        summary = "일부 이동평균 데이터가 부족합니다. 짧은 기간 기준으로만 참고해야 합니다."
        score = 50

    return {
        "available": True,
        "current": current,
        "items": items,
        "state": state,
        "summary": summary,
        "score": score,
    }


def _find_pivots(close: pd.Series, window: int = 5) -> list[dict[str, Any]]:
    """
    간단한 스윙 고점/저점 탐지.
    하모닉/엘리엇처럼 정교한 카운팅용은 아니고 피보나치 기준점 후보용입니다.
    """
    pivots = []
    values = close.values
    index = close.index

    if len(close) < window * 2 + 1:
        return pivots

    for i in range(window, len(close) - window):
        left = values[i - window:i]
        right = values[i + 1:i + window + 1]
        value = values[i]

        if value >= max(left) and value >= max(right):
            pivots.append(
                {
                    "type": "high",
                    "date": index[i],
                    "price": float(value),
                    "pos": i,
                }
            )
        elif value <= min(left) and value <= min(right):
            pivots.append(
                {
                    "type": "low",
                    "date": index[i],
                    "price": float(value),
                    "pos": i,
                }
            )

    return pivots


def fibonacci_analysis(df: pd.DataFrame) -> dict[str, Any]:
    """
    피보나치 기본 분석.
    최근 주요 스윙 하나를 잡아 되돌림 레벨을 계산합니다.
    """
    if df.empty or "Close" not in df:
        return {
            "available": False,
            "summary": "피보나치 기준점을 계산할 가격 데이터가 부족합니다.",
            "levels": [],
        }

    close = df["Close"].dropna()
    if len(close) < 80:
        return {
            "available": False,
            "summary": "피보나치 분석에는 최소 80개 이상의 가격 데이터가 필요합니다.",
            "levels": [],
        }

    current = _safe_float(close.iloc[-1])

    # 너무 오래된 스윙보다 최근 구조를 우선하기 위해 최근 360개 봉 위주로 탐색
    recent = close.tail(min(len(close), 360))
    pivots = _find_pivots(recent, window=6)

    if len(pivots) < 2:
        # 피벗이 부족하면 단순 최근 고점/저점으로 대체
        low_date = recent.idxmin()
        high_date = recent.idxmax()
        low = {"type": "low", "date": low_date, "price": float(recent.loc[low_date]), "pos": recent.index.get_loc(low_date)}
        high = {"type": "high", "date": high_date, "price": float(recent.loc[high_date]), "pos": recent.index.get_loc(high_date)}
    else:
        # 최근 가격에 가까운 주요 고점/저점 후보를 사용
        last_high = next((p for p in reversed(pivots) if p["type"] == "high"), None)
        last_low = next((p for p in reversed(pivots) if p["type"] == "low"), None)

        if not last_high or not last_low:
            low_date = recent.idxmin()
            high_date = recent.idxmax()
            low = {"type": "low", "date": low_date, "price": float(recent.loc[low_date]), "pos": recent.index.get_loc(low_date)}
            high = {"type": "high", "date": high_date, "price": float(recent.loc[high_date]), "pos": recent.index.get_loc(high_date)}
        else:
            low = last_low
            high = last_high

    low_price = low["price"]
    high_price = high["price"]

    if high_price == low_price:
        return {
            "available": False,
            "summary": "고점과 저점 차이가 너무 작아 피보나치 레벨을 계산하기 어렵습니다.",
            "levels": [],
        }

    # 최근 고점이 최근 저점보다 뒤에 있으면 상승 스윙 뒤 조정으로 본다.
    direction = "상승 스윙" if high["pos"] > low["pos"] else "하락 스윙"

    ratios = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

    levels = []
    diff = high_price - low_price

    if direction == "상승 스윙":
        # 상승 이후 되돌림: 고점에서 아래로 내려오는 가격대
        for ratio in ratios:
            level = high_price - diff * ratio
            levels.append(
                {
                    "ratio": ratio,
                    "label": f"{ratio:.3f}".rstrip("0").rstrip("."),
                    "price": level,
                    "distance_pct": _pct_diff(current, level),
                }
            )
        base_text = "최근 상승 스윙을 기준으로 되돌림 가격대를 계산했습니다."
    else:
        # 하락 이후 반등: 저점에서 위로 올라가는 되돌림 가격대
        for ratio in ratios:
            level = low_price + diff * ratio
            levels.append(
                {
                    "ratio": ratio,
                    "label": f"{ratio:.3f}".rstrip("0").rstrip("."),
                    "price": level,
                    "distance_pct": _pct_diff(current, level),
                }
            )
        base_text = "최근 하락 스윙을 기준으로 반등 되돌림 가격대를 계산했습니다."

    nearest = min(
        levels,
        key=lambda x: abs(x["distance_pct"]) if x["distance_pct"] is not None else 999999,
    )

    nearest_ratio = nearest["ratio"]

    if nearest_ratio in [0.382, 0.5]:
        zone = "중간 되돌림 구간"
        meaning = "일반적인 조정 또는 반등 확인 구간에 가깝습니다."
    elif nearest_ratio in [0.618, 0.786]:
        zone = "깊은 되돌림 구간"
        meaning = "가격이 꽤 깊게 되돌린 구간입니다. 반응이 나올 수 있지만 추세 훼손 여부도 함께 봐야 합니다."
    elif nearest_ratio == 0.236:
        zone = "얕은 되돌림 구간"
        meaning = "가격 되돌림이 아직 얕은 편입니다. 강한 추세에서는 이 정도에서 버티기도 합니다."
    else:
        zone = "완전 되돌림 근처"
        meaning = "스윙의 시작점 근처까지 되돌린 구간입니다. 기존 구조가 약해졌는지 확인해야 합니다."

    summary = f"{base_text} 현재가는 {nearest['label']} 레벨 근처의 {zone}에 있습니다. {meaning}"

    return {
        "available": True,
        "direction": direction,
        "low": {
            "date": low["date"].strftime("%Y-%m-%d"),
            "price": low_price,
        },
        "high": {
            "date": high["date"].strftime("%Y-%m-%d"),
            "price": high_price,
        },
        "levels": levels,
        "nearest": nearest,
        "zone": zone,
        "summary": summary,
    }


def analyze_technical(df: pd.DataFrame) -> dict[str, Any]:
    """
    기술적 분석 모듈의 단일 진입점.
    앞으로 VWAP, 피보 중첩, 하모닉, 엘리엇 후보도 여기에 따로 붙이면 됩니다.
    """
    return {
        "moving_average": moving_average_analysis(df),
        "fibonacci": fibonacci_analysis(df),
    }

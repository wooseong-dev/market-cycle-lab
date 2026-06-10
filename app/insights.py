from __future__ import annotations

from typing import Any


def _num(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def calculate_holding_difficulty(metrics: dict[str, Any], technical: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    버티기 난이도.
    매수/매도 신호가 아니라, 자산을 들고 있을 때 심리적으로 얼마나 피곤한 구간인지 보여주는 점수.
    """
    technical = technical or {}

    drawdown = abs(_num(metrics.get("ath_drawdown"), 0.0))
    current_days = _num(metrics.get("current_dd_days"), 0.0)
    avg_days = _num(metrics.get("avg_dd_duration"), 1.0)
    volatility = _num(metrics.get("volatility_90d"), 0.0)
    one_year_change = _num(metrics.get("one_year_change"), 0.0)

    ma = technical.get("moving_average", {}) if isinstance(technical, dict) else {}
    ma_score = _num(ma.get("score"), 50.0)

    drawdown_score = clamp(drawdown * 1.15, 0, 42)

    if avg_days > 0:
        duration_ratio = current_days / avg_days
    else:
        duration_ratio = 0

    duration_score = clamp(duration_ratio * 18, 0, 24)
    volatility_score = clamp(volatility * 0.22, 0, 18)
    trend_score = clamp((100 - ma_score) * 0.16, 0, 16)

    # 1년 수익률이 높으면 과열 피로, 크게 마이너스면 손실 피로를 조금 더 반영
    if one_year_change > 70:
        momentum_stress = 6
    elif one_year_change < -30:
        momentum_stress = 8
    else:
        momentum_stress = 0

    score = round(clamp(drawdown_score + duration_score + volatility_score + trend_score + momentum_stress))

    if score >= 80:
        label = "극심한 버티기 구간"
        tone = "가격 변동, 조정 기간, 추세 부담이 동시에 큰 구간입니다."
    elif score >= 65:
        label = "상당히 피곤한 구간"
        tone = "싸 보일 수 있지만, 심리적으로 흔들리기 쉬운 구간입니다."
    elif score >= 45:
        label = "중립적 부담 구간"
        tone = "과열도 침체도 한쪽으로 극단적이지 않습니다."
    elif score >= 25:
        label = "비교적 안정 구간"
        tone = "현재 데이터만 보면 버티기 난이도는 높지 않은 편입니다."
    else:
        label = "낮은 부담 구간"
        tone = "가격 위치와 변동성 부담이 비교적 낮은 구간입니다."

    reasons = []
    if drawdown >= 30:
        reasons.append("고점 대비 하락폭이 큽니다.")
    elif drawdown >= 10:
        reasons.append("고점 대비 어느 정도 조정이 진행 중입니다.")
    else:
        reasons.append("고점과 크게 멀지 않은 위치입니다.")

    if current_days > avg_days * 1.4 and avg_days > 0:
        reasons.append("현재 조정 기간이 과거 평균보다 긴 편입니다.")
    elif current_days > 0:
        reasons.append("현재 조정은 아직 진행 중입니다.")
    else:
        reasons.append("현재는 전고점 부근 또는 회복 구간에 가깝습니다.")

    if volatility >= 70:
        reasons.append("최근 변동성이 매우 큽니다.")
    elif volatility >= 35:
        reasons.append("최근 변동성이 낮지 않습니다.")

    if ma_score < 40:
        reasons.append("주요 이동평균 기준 추세 부담이 있습니다.")
    elif ma_score > 70:
        reasons.append("이동평균 기준 추세는 비교적 양호합니다.")

    return {
        "score": score,
        "label": label,
        "tone": tone,
        "reasons": reasons,
        "components": {
            "drawdown_score": round(drawdown_score, 1),
            "duration_score": round(duration_score, 1),
            "volatility_score": round(volatility_score, 1),
            "trend_score": round(trend_score, 1),
            "momentum_stress": momentum_stress,
        },
    }


def calculate_last_year_result(metrics: dict[str, Any], amount: float = 1_000_000) -> dict[str, Any]:
    one_year_change = metrics.get("one_year_change")
    one_year_price = metrics.get("one_year_price")
    current_price = metrics.get("current_price")

    if one_year_change is None or one_year_price in (None, 0) or current_price is None:
        return {
            "available": False,
            "amount": amount,
            "current_value": None,
            "profit": None,
            "return_pct": None,
            "summary": "작년 가격 데이터가 부족해 계산할 수 없습니다.",
        }

    current_value = amount * (1 + one_year_change / 100)
    profit = current_value - amount

    if profit > 0:
        summary = f"작년 이맘때 100만 원을 투자했다면 현재 약 {current_value:,.0f}원입니다."
    elif profit < 0:
        summary = f"작년 이맘때 100만 원을 투자했다면 현재 약 {current_value:,.0f}원입니다."
    else:
        summary = "작년 이맘때 투자했다면 현재 거의 본전 수준입니다."

    return {
        "available": True,
        "amount": amount,
        "current_value": current_value,
        "profit": profit,
        "return_pct": one_year_change,
        "summary": summary,
    }


def build_auto_interpretation(asset: dict[str, Any]) -> dict[str, Any]:
    metrics = asset.get("metrics", {})
    technical = asset.get("technical", {})
    difficulty = asset.get("difficulty") or calculate_holding_difficulty(metrics, technical)

    drawdown = _num(metrics.get("ath_drawdown"), 0.0)
    one_year = _num(metrics.get("one_year_change"), 0.0)
    current_days = _num(metrics.get("current_dd_days"), 0.0)
    ma = technical.get("moving_average", {}) if isinstance(technical, dict) else {}
    ma_state = ma.get("state", "추세 데이터 부족")

    title = "현재 위치 해석"

    bullets = []

    if drawdown > -5:
        bullets.append("고점과 가까운 위치라 강한 흐름이지만, 기대가 이미 반영됐을 가능성도 있습니다.")
    elif drawdown > -20:
        bullets.append("고점 대비 일반적인 조정 구간에 있습니다.")
    elif drawdown > -50:
        bullets.append("고점 대비 깊은 조정 구간입니다. 단순히 싸졌다는 이유만으로 보기보다는 회복 조건을 같이 봐야 합니다.")
    else:
        bullets.append("고점 대비 극단적으로 내려온 구간입니다. 반등 가능성과 추가 하락 위험이 동시에 큽니다.")

    if one_year > 50:
        bullets.append("1년 기준 수익률은 강한 편입니다. 장기 상승 이후 피로감이 쌓였는지 확인해야 합니다.")
    elif one_year < -20:
        bullets.append("1년 기준으로는 약한 흐름입니다. 회복 신호가 나오기 전까지는 보수적인 해석이 필요합니다.")
    else:
        bullets.append("1년 기준 수익률은 극단적이지 않은 편입니다.")

    if current_days > 0:
        bullets.append(f"현재 조정 기간은 약 {int(current_days):,}일입니다. 가격보다 시간 피로도도 함께 봐야 합니다.")

    bullets.append(f"이동평균 기준 상태는 '{ma_state}'입니다.")

    summary = f"{asset.get('symbol', asset.get('ticker', '이 자산'))}의 현재 버티기 난이도는 {difficulty['score']}점입니다. {difficulty['tone']}"

    return {
        "title": title,
        "summary": summary,
        "bullets": bullets,
    }


def attach_insights(asset: dict[str, Any], amount: float = 1_000_000) -> dict[str, Any]:
    metrics = asset.get("metrics", {})
    technical = asset.get("technical", {})

    difficulty = calculate_holding_difficulty(metrics, technical)
    last_year = calculate_last_year_result(metrics, amount=amount)

    enriched = {
        **asset,
        "difficulty": difficulty,
        "last_year_result": last_year,
    }

    enriched["auto_interpretation"] = build_auto_interpretation(enriched)

    return enriched

from __future__ import annotations

from typing import Any


def _num(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


ACCOUNT_LABELS = {
    "core": "장기 핵심 계좌",
    "income": "월분배·현금흐름 계좌",
    "attack": "공격 계좌",
    "trading": "BTC·레버리지·트레이딩 계좌",
}

RISK_LABELS = {
    "low": "낮음",
    "medium": "보통",
    "high": "높음",
}

VIEW_LABELS = {
    "positive": "우호적",
    "neutral": "중립",
    "negative": "비우호적",
}


def account_guide(account_type: str) -> dict[str, Any]:
    guides = {
        "income": {
            "label": ACCOUNT_LABELS["income"],
            "goal": "월세·생활비 압박을 낮추는 현금흐름",
            "tools": ["분배 구조", "NAV 훼손 여부", "기초자산", "분배 지속 가능성", "세금·수수료", "차트는 진입가 참고"],
            "max_hint": 30,
            "warning": "분배율만 보고 사면 위험합니다. 분배금이 어디서 나오는지 봐야 합니다.",
        },
        "attack": {
            "label": ACCOUNT_LABELS["attack"],
            "goal": "작은 비중으로 초과수익 시도",
            "tools": ["산업 테마", "실적 성장", "수급", "차트", "뉴스·재료", "손절 기준"],
            "max_hint": 15,
            "warning": "공격 계좌는 맞히는 것보다 틀렸을 때 덜 죽는 구조가 중요합니다.",
        },
        "trading": {
            "label": ACCOUNT_LABELS["trading"],
            "goal": "생존하면서 변동성 기회를 잡기",
            "tools": ["차트", "펀딩비", "미결제약정", "청산맵", "ETF 수급", "달러·금리·유동성", "포지션 크기"],
            "max_hint": 10,
            "warning": "트레이딩 포지션을 손실 후 장기투자로 바꾸면 기준이 무너집니다.",
        },
        "core": {
            "label": ACCOUNT_LABELS["core"],
            "goal": "크게 안 망하고 오래 불리기",
            "tools": ["자산배분", "지수 ETF 구조", "금리·유동성", "장기 밸류에이션", "리밸런싱", "차트는 과열·공포 확인"],
            "max_hint": 80,
            "warning": "핵심 계좌는 예측보다 지속성과 리밸런싱이 중요합니다.",
        },
    }
    return guides.get(account_type, guides["core"])


def allocation_layer(asset, account_type, allocation_pct, risk_tolerance):
    guide = account_guide(account_type)
    difficulty = _num(asset.get("difficulty", {}).get("score"), 50)
    asset_type = asset.get("type", "Custom")
    max_hint = guide["max_hint"]

    if risk_tolerance == "low":
        max_hint *= 0.75
    elif risk_tolerance == "high":
        max_hint *= 1.25

    if asset_type == "Crypto" and account_type == "core":
        max_hint = min(max_hint, 20)
    if asset_type == "Crypto" and risk_tolerance == "low":
        max_hint = min(max_hint, 8)

    pressure = allocation_pct / max_hint if max_hint else 1
    score = _clamp(100 - max(0, pressure - 1) * 45 - difficulty * 0.15)

    if allocation_pct > max_hint:
        status = "비중 부담"
        summary = f"입력 비중 {allocation_pct:.1f}%는 이 계좌 성격 기준으로 높은 편입니다."
    else:
        status = "비중 양호"
        summary = f"입력 비중 {allocation_pct:.1f}%는 이 계좌 성격 안에서 관리 가능한 범위에 가깝습니다."

    return {
        "name": "자산배분",
        "status": status,
        "score": round(score),
        "summary": summary,
        "points": [
            f"계좌 성격: {guide['label']}",
            f"이 계좌의 목적: {guide['goal']}",
            f"참고 상한 비중: 약 {max_hint:.1f}%",
            "고수들은 종목보다 먼저 자산군과 비중을 봅니다.",
        ],
    }


def macro_layer(asset, macro_view):
    asset_type = asset.get("type", "Custom")
    one_year = _num(asset.get("metrics", {}).get("one_year_change"), 0)
    score = 55 + (18 if macro_view == "positive" else -18 if macro_view == "negative" else 0)

    if asset_type == "Crypto":
        desc = "코인은 달러, 금리, 글로벌 유동성, ETF 수급에 민감합니다."
        if one_year > 80:
            score -= 8
    elif asset_type == "Equity":
        desc = "주식은 금리, 기업이익, 경기 사이클, 밸류에이션에 영향을 받습니다."
    elif asset_type == "Commodity":
        desc = "원자재는 달러, 실질금리, 지정학, 수급에 민감합니다."
    else:
        desc = "이 자산은 매크로 민감도를 별도로 확인해야 합니다."

    return {
        "name": "매크로",
        "status": VIEW_LABELS.get(macro_view, "중립"),
        "score": round(_clamp(score)),
        "summary": desc,
        "points": [
            "금리, 인플레이션, 환율, 유동성은 시장 전체의 날씨입니다.",
            "위험자산은 유동성이 풀릴 때 유리하고, 긴축·달러 강세 때 부담이 커질 수 있습니다.",
            "차트는 결과이고, 매크로는 그 결과가 나온 배경입니다.",
        ],
    }


def fundamentals_layer(asset):
    asset_type = asset.get("type", "Custom")

    if asset_type == "Crypto":
        points = [
            "네트워크 사용량, 장기 보유자, 거래소 보유량, ETF 순유입을 봐야 합니다.",
            "단순 가격보다 유동성과 수급 구조가 더 중요할 수 있습니다.",
            "BTC와 알트코인은 펀더멘털 기준이 다릅니다.",
        ]
        summary = "코인은 전통 재무제표보다 네트워크, 수급, 유동성, 사이클이 중요합니다."
        score = 55
    elif asset_type == "Equity":
        points = [
            "매출 성장, 영업이익률, 현금흐름, 부채, ROE/ROIC를 확인해야 합니다.",
            "ETF라면 구성종목, 보수, 운용규모, 추적오차, 분배 정책을 봐야 합니다.",
            "커버드콜은 분배율보다 NAV 훼손 여부와 상승장 포기 비용이 중요합니다.",
        ]
        summary = "주식·ETF는 이익의 질과 구조를 먼저 확인해야 합니다."
        score = 65
    else:
        points = [
            "이 자산이 무엇으로 가치를 만드는지 먼저 정의해야 합니다.",
            "가격 상승 이유가 구조적 성장인지, 단기 수급인지 구분해야 합니다.",
            "수익의 원천이 불명확하면 비중을 줄이는 편이 안전합니다.",
        ]
        summary = "자산의 수익 원천을 먼저 확인해야 합니다."
        score = 55

    return {"name": "펀더멘털", "status": "체크 필요", "score": score, "summary": summary, "points": points}


def valuation_layer(asset, valuation_view):
    drawdown = _num(asset.get("metrics", {}).get("ath_drawdown"), 0)
    one_year = _num(asset.get("metrics", {}).get("one_year_change"), 0)
    score = 55 + (18 if valuation_view == "positive" else -18 if valuation_view == "negative" else 0)

    if drawdown < -35:
        score += 10
        status = "싸 보이는 구간"
        summary = "고점 대비 많이 내려온 구간입니다. 다만 싼 것과 좋은 것은 다릅니다."
    elif drawdown > -5 and one_year > 40:
        score -= 10
        status = "고점 부근"
        summary = "가격이 강하지만 기대가 이미 반영됐을 가능성도 봐야 합니다."
    else:
        status = "중립 구간"
        summary = "가격만으로 싸다/비싸다를 단정하기 어려운 구간입니다."

    return {
        "name": "밸류에이션",
        "status": status,
        "score": round(_clamp(score)),
        "summary": summary,
        "points": [
            "PER 하나, 배당률 하나로 결론내리면 위험합니다.",
            "좋은 자산도 너무 비싸게 사면 수익률이 나빠질 수 있습니다.",
            "가격, 성장, 질, 사이클을 같이 봐야 합니다.",
        ],
    }


def cycle_layer(asset):
    metrics = asset.get("metrics", {})
    difficulty = asset.get("difficulty", {})
    dd = _num(metrics.get("ath_drawdown"), 0)
    days = _num(metrics.get("current_dd_days"), 0)
    score = 100 - _num(difficulty.get("score"), 50)

    if dd > -5:
        status = "고점·낙관 구간"
    elif dd > -20:
        status = "일반 조정 구간"
    elif dd > -50:
        status = "깊은 조정 구간"
    else:
        status = "공포·침체 구간"

    return {
        "name": "사이클",
        "status": status,
        "score": round(_clamp(score)),
        "summary": f"고점 대비 {dd:.2f}%, 현재 조정 기간은 약 {int(days):,}일입니다.",
        "points": [
            "공포 → 회복 → 낙관 → 탐욕 → 과열 → 붕괴 → 공포의 흐름을 봅니다.",
            "정확한 저점·고점을 맞히는 것보다 어느 국면인지 대략 파악하는 게 중요합니다.",
            "싸 보이는 구간에서도 구조가 무너졌는지 확인해야 합니다.",
        ],
    }


def supply_layer(asset, supply_view):
    note = "거래량, ETF 자금 유입, 외국인 수급, 공매도, 옵션 포지션을 확인해야 합니다."
    if asset.get("type") == "Crypto":
        note = "ETF 순유입, 거래소 보유량, 장기 보유자, 펀딩비, 미결제약정, 청산맵을 확인해야 합니다."

    score = 55 + (20 if supply_view == "positive" else -20 if supply_view == "negative" else 0)

    return {
        "name": "수급",
        "status": VIEW_LABELS.get(supply_view, "중립"),
        "score": round(_clamp(score)),
        "summary": "수급은 누가 사고 누가 파는지 보는 관점입니다.",
        "points": [
            note,
            "차트는 결과이고, 수급은 그 결과를 만든 힘에 가깝습니다.",
            "가격이 오르는데 수급이 약하면 지속성을 의심해야 합니다.",
        ],
    }


def technical_layer(asset):
    ma = asset.get("technical", {}).get("moving_average", {})
    ma_score = _num(ma.get("score"), 50)
    ma_state = ma.get("state", "이동평균 데이터 부족")

    return {
        "name": "차트",
        "status": ma_state,
        "score": round(_clamp(ma_score)),
        "summary": "차트는 예언 도구가 아니라 가격 행동 관찰 도구입니다.",
        "points": [
            "추세 확인, 과열·공포 확인, 진입가 분할, 손절선 설정에 사용합니다.",
            "투자에서는 차트 비중이 낮고, 트레이딩에서는 차트 비중이 높습니다.",
            "피보나치·엘리엇·하모닉은 기준점에 주관이 많이 들어가므로 확정 분석으로 쓰면 위험합니다.",
        ],
    }


def psychology_layer(account_type, allocation_pct, exit_rule):
    score = 70
    if exit_rule != "yes":
        score -= 25
    if account_type in ["attack", "trading"] and allocation_pct > 15:
        score -= 15

    return {
        "name": "투자심리",
        "status": "기준 있음" if exit_rule == "yes" else "기준 부족",
        "score": round(_clamp(score)),
        "summary": "분석보다 무서운 것은 기준 없이 흔들리는 자기 심리입니다.",
        "points": [
            "매수 전에 장기투자인지, 트레이딩인지, 현금흐름용인지 정해야 합니다.",
            "손실 후 갑자기 장기투자로 바꾸면 기준이 무너집니다.",
            "공포 매도, 추격 매수, 물타기, FOMO를 막는 건 사전 기준입니다.",
        ],
    }


def rebalancing_layer(account_type, allocation_pct):
    if account_type == "core":
        summary = "핵심 계좌는 정기 리밸런싱이 중요합니다."
        score = 75
    elif account_type == "income":
        summary = "월분배 계좌는 분배율보다 원금 훼손과 비중 관리를 봐야 합니다."
        score = 68
    else:
        summary = "공격·트레이딩 계좌는 수익이 커지면 일부 회수하는 규칙이 필요합니다."
        score = 62

    if allocation_pct > 30 and account_type != "core":
        score -= 15

    return {
        "name": "리밸런싱",
        "status": "규칙 필요",
        "score": round(_clamp(score)),
        "summary": summary,
        "points": [
            "오른 자산은 일부 줄이고, 빠진 자산은 계획대로 채우는 구조가 감정매매를 줄입니다.",
            "급등해서 비중이 커진 자산은 리스크도 같이 커졌다는 뜻입니다.",
            "리밸런싱은 예측보다 규칙에 가깝습니다.",
        ],
    }


def risk_layer(asset, account_type, allocation_pct, exit_rule):
    difficulty = _num(asset.get("difficulty", {}).get("score"), 50)
    score = 80 - difficulty * 0.25

    if exit_rule != "yes":
        score -= 25
    if account_type in ["attack", "trading"] and allocation_pct > 10:
        score -= 10
    if asset.get("type") == "Crypto" and allocation_pct > 20:
        score -= 15

    score = _clamp(score)

    if score >= 75:
        status = "관리 양호"
    elif score >= 50:
        status = "주의 필요"
    else:
        status = "리스크 과다"

    return {
        "name": "리스크 관리",
        "status": status,
        "score": round(score),
        "summary": "왕은 리스크 관리입니다. 맞히는 능력보다 틀렸을 때 덜 죽는 능력이 중요합니다.",
        "points": [
            "이 돈이 장기투자금인지, 월분배용인지, 공격자금인지 먼저 구분해야 합니다.",
            "틀렸을 때 얼마나 잃을지, 언제 줄일지, 얼마까지 버틸지 정해야 합니다.",
            "좋은 분석도 비중이 틀리면 계좌를 망칠 수 있습니다.",
        ],
    }


def build_framework_analysis(
    asset: dict[str, Any],
    account_type: str = "core",
    allocation_pct: float = 10,
    risk_tolerance: str = "medium",
    valuation_view: str = "neutral",
    macro_view: str = "neutral",
    supply_view: str = "neutral",
    exit_rule: str = "yes",
) -> dict[str, Any]:
    guide = account_guide(account_type)

    layers = [
        allocation_layer(asset, account_type, allocation_pct, risk_tolerance),
        macro_layer(asset, macro_view),
        fundamentals_layer(asset),
        valuation_layer(asset, valuation_view),
        cycle_layer(asset),
        supply_layer(asset, supply_view),
        technical_layer(asset),
        psychology_layer(account_type, allocation_pct, exit_rule),
        rebalancing_layer(account_type, allocation_pct),
        risk_layer(asset, account_type, allocation_pct, exit_rule),
    ]

    weighted = 0
    total_weight = 0
    for layer in layers:
        weight = 2 if layer["name"] == "리스크 관리" else 1
        weighted += layer["score"] * weight
        total_weight += weight

    total_score = round(weighted / total_weight)

    if total_score >= 75:
        verdict = "구조가 비교적 안정적입니다"
        verdict_detail = "그래도 이 점수는 매수 신호가 아닙니다. 비중과 리밸런싱 기준을 유지하는 것이 핵심입니다."
    elif total_score >= 55:
        verdict = "관찰은 가능하지만 기준이 필요합니다"
        verdict_detail = "나쁘지 않지만, 매수·보유·매도 기준을 더 명확히 해야 합니다."
    else:
        verdict = "리스크를 먼저 줄여야 합니다"
        verdict_detail = "아이디어보다 비중, 손실 기준, 계좌 성격을 먼저 정리하는 편이 좋습니다."

    checklist = [
        "이 자산을 왜 사는지 한 문장으로 설명할 수 있는가?",
        "이 돈이 장기투자금, 월분배용, 공격자금, 트레이딩 중 무엇인지 정했는가?",
        "틀렸을 때 얼마까지 잃을 수 있는지 계산했는가?",
        "추가매수와 손절, 리밸런싱 기준이 있는가?",
        "차트가 아니라 자산배분과 리스크 관리가 먼저인가?",
    ]

    return {
        "guide": guide,
        "layers": layers,
        "total_score": total_score,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "checklist": checklist,
    }

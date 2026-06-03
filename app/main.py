from __future__ import annotations

from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.assets import ASSETS, DEFAULT_ASSETS
from app.data import get_history
from app.market_math import calculate_metrics, to_chart_points
from app.technical_analysis import analyze_technical
from app.insights import attach_insights
from app.analysis_content import load_analysis_posts, get_analysis_post, get_related_posts

settings = get_settings()

app = FastAPI(title=settings.site_name)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def fmt_price(value):
    if value is None:
        return "-"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:,.2f}"
    return f"{value:,.4f}"


def fmt_pct(value):
    if value is None:
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def pct_class(value):
    if value is None:
        return ""
    return "up" if value >= 0 else "down"


def money_krw(value):
    if value is None:
        return "-"
    return f"{value:,.0f}원"


def fmt_days(value):
    if value is None:
        return "-"
    value = int(round(value))
    if value == 0:
        return "0일"
    return f"{value:,}일"


def asset_type_ko(value):
    labels = {
        "Crypto": "코인",
        "Equity": "주식",
        "Commodity": "원자재",
        "Macro": "매크로",
        "Custom": "사용자 지정 자산",
    }
    return labels.get(value, value)


def cycle_label_ko(value):
    labels = {
        "Near High": "고점 부근",
        "Cooling": "일반 조정",
        "Deep Drawdown": "깊은 조정",
        "Capitulation Zone": "극단 하락 구간",
    }
    return labels.get(value, value)


def risk_text(score):
    if score >= 80:
        return "위험 신호가 강합니다. 가격이 많이 흔들렸거나 조정이 깊은 구간입니다."
    if score >= 60:
        return "주의 구간입니다. 변동성과 하락폭을 함께 확인해야 합니다."
    if score >= 40:
        return "중립 구간입니다. 과열도, 공포도 한쪽으로 강하지 않습니다."
    return "상대적으로 안정 구간입니다. 다만 낮은 위험이 곧 매수 신호는 아닙니다."


def drawdown_text(value):
    if value is None:
        return "데이터가 부족합니다."
    if value > -5:
        return "전고점과 거의 붙어 있습니다. 강한 흐름이지만 과열 여부도 봐야 합니다."
    if value > -20:
        return "일반적인 눌림 구간입니다. 추세가 유지되는 조정인지 확인해야 합니다."
    if value > -50:
        return "깊은 조정 구간입니다. 회복에는 시간이 걸릴 수 있습니다."
    return "매우 큰 하락 구간입니다. 반등 기대와 추가 하락 위험이 같이 커집니다."


def clean_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().replace(" ", "")

    # 한국 주식 코드 6자리만 입력하면 기본적으로 코스피(.KS)로 처리
    if cleaned.isdigit() and len(cleaned) == 6:
        return f"{cleaned}.KS"

    return cleaned


def custom_asset_info(symbol: str):
    label = symbol
    asset_type = "Custom"
    theme = "growth"

    if symbol.endswith("-USD"):
        asset_type = "Crypto"
        theme = "crypto"
        label = symbol.replace("-USD", "")
    elif symbol.endswith(".KS") or symbol.endswith(".KQ"):
        asset_type = "Equity"
        theme = "stocks"
    elif symbol in ["QQQ", "SPY", "DIA", "IWM"]:
        asset_type = "Equity"
        theme = "growth"
    elif symbol in ["GLD", "SLV", "CL=F", "GC=F"]:
        asset_type = "Commodity"
        theme = "gold" if symbol in ["GLD", "GC=F"] else "oil"

    return {
        "name": label,
        "symbol": label,
        "type": asset_type,
        "theme": theme,
        "description": "사용자가 직접 입력한 자산입니다. 최근 5년 가격 흐름, 고점 대비 하락률, 조정 기간을 계산합니다.",
    }


templates.env.globals["fmt_price"] = fmt_price
templates.env.globals["fmt_pct"] = fmt_pct
templates.env.globals["pct_class"] = pct_class
templates.env.globals["money_krw"] = money_krw
templates.env.globals["fmt_days"] = fmt_days
templates.env.globals["asset_type_ko"] = asset_type_ko
templates.env.globals["cycle_label_ko"] = cycle_label_ko
templates.env.globals["risk_text"] = risk_text
templates.env.globals["drawdown_text"] = drawdown_text


def build_asset(symbol: str, amount: float = 1_000_000):
    symbol = clean_symbol(symbol)

    info = ASSETS.get(symbol) or custom_asset_info(symbol)

    df, fallback = get_history(symbol)
    metrics = calculate_metrics(df)

    if not metrics:
        raise HTTPException(status_code=500, detail="가격 데이터를 계산하지 못했습니다.")

    technical = analyze_technical(df)

    asset = {
        "ticker": symbol,
        **info,
        "metrics": metrics,
        "technical": technical,
        "chart": to_chart_points(df),
        "fallback": fallback,
    }

    return attach_insights(asset, amount=amount)


def build_default_assets(amount: float = 1_000_000):
    return [build_asset(symbol, amount=amount) for symbol in DEFAULT_ASSETS]


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    assets = build_default_assets()
    crypto = [a for a in assets if a["type"] == "Crypto"]
    equity = [a for a in assets if a["type"] == "Equity"]
    macro = [a for a in assets if a["type"] in ["Commodity", "Macro"]]

    stress_ranking = sorted(assets, key=lambda a: a["difficulty"]["score"], reverse=True)[:5]
    drawdown_ranking = sorted(assets, key=lambda a: a["metrics"].get("ath_drawdown") or 0)[:5]
    correction_ranking = sorted(assets, key=lambda a: a["metrics"].get("current_dd_days") or 0, reverse=True)[:5]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "settings": settings,
            "assets": assets,
            "crypto": crypto,
            "equity": equity,
            "macro": macro,
            "stress_ranking": stress_ranking,
            "drawdown_ranking": drawdown_ranking,
            "correction_ranking": correction_ranking,
            "latest_posts": load_analysis_posts()[:3],
            "page_title": settings.site_name,
            "page_description": "코인과 증시의 현재 위치, 버티기 난이도, 작년 대비 수익률, 조정 기간을 쉽게 보여주는 시장 사이클 대시보드.",
            "now": datetime.now(timezone.utc),
        },
    )


@app.get("/analyze")
def analyze(symbol: str = Query(..., min_length=1)):
    cleaned = clean_symbol(symbol)
    return RedirectResponse(url=f"/asset/{cleaned}", status_code=302)


@app.get("/asset/{symbol:path}", response_class=HTMLResponse)
def asset_detail(symbol: str, request: Request):
    asset = build_asset(symbol)
    related_posts = get_related_posts(asset["ticker"], limit=3)

    return templates.TemplateResponse(
        "asset.html",
        {
            "request": request,
            "settings": settings,
            "asset": asset,
            "related_posts": related_posts,
            "page_title": f"{asset['name']} 사이클 분석",
            "page_description": f"{asset['name']}의 버티기 난이도, 작년 이맘때 수익률, 고점 대비 하락률, 평균 조정 기간.",
        },
    )


@app.get("/rankings/{kind}", response_class=HTMLResponse)
def rankings(kind: str, request: Request):
    assets = build_default_assets()

    if kind == "stress":
        title = "시장 스트레스 랭킹"
        description = "버티기 난이도가 높은 자산을 순서대로 보여줍니다."
        assets = sorted(assets, key=lambda a: a["difficulty"]["score"], reverse=True)
    elif kind == "drawdown":
        title = "고점 대비 하락률 랭킹"
        description = "최근 5년 고점 대비 많이 내려온 자산을 보여줍니다."
        assets = sorted(assets, key=lambda a: a["metrics"].get("ath_drawdown") or 0)
    elif kind == "correction":
        title = "현재 조정 기간 랭킹"
        description = "전고점을 회복하지 못한 기간이 긴 자산을 보여줍니다."
        assets = sorted(assets, key=lambda a: a["metrics"].get("current_dd_days") or 0, reverse=True)
    else:
        raise HTTPException(status_code=404, detail="Ranking not found")

    return templates.TemplateResponse(
        "rankings.html",
        {
            "request": request,
            "settings": settings,
            "kind": kind,
            "ranking_title": title,
            "ranking_description": description,
            "assets": assets,
            "page_title": title,
            "page_description": description,
        },
    )


@app.get("/tools/last-year", response_class=HTMLResponse)
def last_year_tool(
    request: Request,
    symbol: str = Query("BTC-USD"),
    amount: float = Query(1_000_000),
):
    asset = build_asset(symbol, amount=amount)

    return templates.TemplateResponse(
        "last_year_tool.html",
        {
            "request": request,
            "settings": settings,
            "asset": asset,
            "symbol": clean_symbol(symbol),
            "amount": amount,
            "page_title": "작년 오늘 샀다면 계산기",
            "page_description": "작년 이맘때 투자했다면 현재 얼마가 되었는지 계산합니다.",
        },
    )


@app.get("/analysis", response_class=HTMLResponse)
def analysis_list(request: Request):
    posts = load_analysis_posts()

    return templates.TemplateResponse(
        "analysis_list.html",
        {
            "request": request,
            "settings": settings,
            "posts": posts,
            "page_title": "분석 노트",
            "page_description": "시장 사이클과 자산별 관찰 기록을 모아둔 분석 노트입니다.",
        },
    )


@app.get("/analysis/{slug}", response_class=HTMLResponse)
def analysis_detail(slug: str, request: Request):
    post = get_analysis_post(slug)

    if not post:
        raise HTTPException(status_code=404, detail="Analysis post not found")

    return templates.TemplateResponse(
        "analysis_detail.html",
        {
            "request": request,
            "settings": settings,
            "post": post,
            "page_title": post["title"],
            "page_description": post.get("summary") or post["title"],
        },
    )


@app.get("/api/assets")
def api_assets():
    assets = build_default_assets()
    return JSONResponse(assets)


@app.get("/api/asset/{symbol:path}")
def api_asset(symbol: str):
    return JSONResponse(build_asset(symbol))


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return f"""User-agent: *
Allow: /

Sitemap: {settings.site_url}/sitemap.xml
"""


@app.get("/sitemap.xml")
def sitemap():
    today = datetime.now(timezone.utc).date().isoformat()

    urls = [
        f"<url><loc>{settings.site_url}/</loc><lastmod>{today}</lastmod></url>",
        f"<url><loc>{settings.site_url}/rankings/stress</loc><lastmod>{today}</lastmod></url>",
        f"<url><loc>{settings.site_url}/rankings/drawdown</loc><lastmod>{today}</lastmod></url>",
        f"<url><loc>{settings.site_url}/rankings/correction</loc><lastmod>{today}</lastmod></url>",
        f"<url><loc>{settings.site_url}/tools/last-year</loc><lastmod>{today}</lastmod></url>",
        f"<url><loc>{settings.site_url}/analysis</loc><lastmod>{today}</lastmod></url>",
    ]

    for symbol in DEFAULT_ASSETS:
        urls.append(
            f"<url><loc>{settings.site_url}/asset/{symbol}</loc><lastmod>{today}</lastmod></url>"
        )

    for post in load_analysis_posts():
        urls.append(
            f"<url><loc>{settings.site_url}/analysis/{post['slug']}</loc><lastmod>{post.get('date') or today}</lastmod></url>"
        )

    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        *urls,
        "</urlset>",
    ]

    return Response("\n".join(xml), media_type="application/xml")

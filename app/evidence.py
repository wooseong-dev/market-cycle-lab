from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


def _is_korean_stock(symbol: str) -> bool:
    return symbol.endswith(".KS") or symbol.endswith(".KQ")


def _is_crypto(symbol: str) -> bool:
    return symbol.endswith("-USD") or symbol.upper() in ["BTC", "ETH", "SOL", "XRP"]


def _is_us_stock_or_etf(symbol: str) -> bool:
    if _is_korean_stock(symbol) or _is_crypto(symbol):
        return False
    return symbol.replace(".", "").replace("-", "").isalnum()


def _display_symbol(symbol: str) -> str:
    return symbol.upper().strip()


def _google_news_rss(query: str) -> str:
    return "https://news.google.com/rss/search?q=" + quote_plus(query) + "&hl=ko&gl=KR&ceid=KR:ko"


def _google_search_url(query: str) -> str:
    return "https://www.google.com/search?q=" + quote_plus(query)


def _naver_search_url(query: str) -> str:
    return "https://search.naver.com/search.naver?query=" + quote_plus(query)


def _resource(title: str, url: str, description: str, tag: str = "원자료") -> dict[str, str]:
    return {
        "title": title,
        "url": url,
        "description": description,
        "tag": tag,
    }


def _group(title: str, description: str, items: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "title": title,
        "description": description,
        "items": items,
    }


def _news_query_for(symbol: str, asset: dict[str, Any] | None = None) -> str:
    symbol = _display_symbol(symbol)
    name = (asset or {}).get("name") or symbol

    if _is_crypto(symbol):
        coin = symbol.replace("-USD", "")
        return f"{coin} ETF inflow funding rate open interest onchain"
    if _is_korean_stock(symbol):
        code = symbol.replace(".KS", "").replace(".KQ", "")
        return f"{code} {name} 실적 수주 공시 증권"
    return f"{symbol} earnings guidance institutional flows SEC filing"


def fetch_google_news(query: str, limit: int = 6) -> list[dict[str, str]]:
    url = _google_news_rss(query)

    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=4) as resp:
            data = resp.read()
        root = ET.fromstring(data)
    except Exception:
        return []

    items: list[dict[str, str]] = []
    for item in root.findall("./channel/item"):
        title = unescape(item.findtext("title") or "").strip()
        link = item.findtext("link") or ""
        pub_date = item.findtext("pubDate") or ""
        source = ""
        source_el = item.find("source")
        if source_el is not None and source_el.text:
            source = source_el.text.strip()

        if not title or not link:
            continue

        items.append(
            {
                "title": title,
                "url": link,
                "source": source or "Google News",
                "published": pub_date,
            }
        )

        if len(items) >= limit:
            break

    return items


def crypto_resources(symbol: str) -> list[dict[str, Any]]:
    coin = symbol.replace("-USD", "").upper()
    search_coin = coin if coin else "BTC"

    return [
        _group(
            "코인 수급·파생",
            "ETF 플로우, 펀딩비, 미결제약정, 청산 데이터처럼 가격 뒤의 힘을 확인합니다.",
            [
                _resource("CoinGlass - ETF Flow", "https://www.coinglass.com/bitcoin-etf", "BTC 현물 ETF 순유입·순유출을 확인합니다.", "ETF"),
                _resource("CoinGlass - Funding Rate", "https://www.coinglass.com/FundingRate", "선물 시장이 롱/숏 어느 쪽으로 쏠렸는지 확인합니다.", "파생"),
                _resource("CoinGlass - Open Interest", "https://www.coinglass.com/BitcoinOpenInterest", "미결제약정 증가·감소로 레버리지 축적 여부를 봅니다.", "파생"),
                _resource("CoinGlass - Liquidation Heatmap", "https://www.coinglass.com/pro/futures/LiquidationHeatMap", "청산 밀집 구간과 포지션 쏠림을 봅니다.", "청산"),
            ],
        ),
        _group(
            "온체인",
            "거래소 보유량, 장기 보유자, 채굴자 매도, 스테이블코인 공급처럼 코인 고유 수급을 봅니다.",
            [
                _resource("CryptoQuant", "https://cryptoquant.com/", "거래소 보유량, 채굴자, 장기 보유자, 스테이블코인 관련 지표를 확인합니다.", "온체인"),
                _resource("Glassnode Studio", "https://studio.glassnode.com/", "장기 보유자, 실현 가격, MVRV 등 온체인 사이클 지표를 봅니다.", "온체인"),
                _resource("Coin Metrics Community", "https://charts.coinmetrics.io/", "네트워크 데이터와 온체인 지표를 차트로 확인합니다.", "온체인"),
                _resource("Whale Alert", "https://whale-alert.io/", "대형 지갑 이동과 거래소 유입·유출 이벤트를 추적합니다.", "고래"),
            ],
        ),
        _group(
            "매크로",
            "코인은 달러, 금리, 유동성에 민감하므로 위험자산 환경을 함께 봅니다.",
            [
                _resource("FRED - 미국 기준금리", "https://fred.stlouisfed.org/series/DFF", "미국 단기금리 흐름을 확인합니다.", "금리"),
                _resource("FRED - 미국 10년물 금리", "https://fred.stlouisfed.org/series/DGS10", "장기금리와 위험자산 할인율 부담을 봅니다.", "금리"),
                _resource("FRED - 달러 지수", "https://fred.stlouisfed.org/series/DTWEXBGS", "달러 강세·약세 환경을 봅니다.", "달러"),
                _resource("FRED - M2", "https://fred.stlouisfed.org/series/M2SL", "광의통화와 유동성 흐름을 참고합니다.", "유동성"),
            ],
        ),
        _group(
            "검색 바로가기",
            "뉴스 헤드라인보다 원자료를 먼저 보고, 뉴스는 보조로 확인합니다.",
            [
                _resource(f"{search_coin} ETF flow 검색", _google_search_url(f"{search_coin} ETF inflow outflow daily"), "ETF 플로우 관련 자료를 검색합니다.", "검색"),
                _resource(f"{search_coin} onchain data 검색", _google_search_url(f"{search_coin} exchange reserve long term holder miner selling stablecoin supply"), "온체인 핵심 지표 자료를 검색합니다.", "검색"),
                _resource(f"{search_coin} funding OI liquidation 검색", _google_search_url(f"{search_coin} funding rate open interest liquidation heatmap"), "파생시장 과열 여부를 검색합니다.", "검색"),
            ],
        ),
    ]


def korean_stock_resources(symbol: str, asset: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    code = symbol.replace(".KS", "").replace(".KQ", "")
    name = (asset or {}).get("name") or code

    return [
        _group(
            "공시·IR",
            "실적, 수주, 증자, 전환사채, 자사주, 내부자 관련 이벤트는 공시에서 먼저 확인합니다.",
            [
                _resource("DART 공시 검색", f"https://dart.fss.or.kr/dsab007/main.do?textCrpNm={quote_plus(code)}", "금감원 전자공시에서 정기보고서·주요사항보고서를 확인합니다.", "공시"),
                _resource("KIND 상장공시", "https://kind.krx.co.kr/", "거래소 공시와 투자유의 관련 정보를 확인합니다.", "공시"),
                _resource("기업 IR 검색", _google_search_url(f"{code} {name} IR 실적발표 컨퍼런스콜"), "기업 IR 자료와 실적 발표 자료를 찾습니다.", "IR"),
                _resource("네이버 종목 검색", f"https://finance.naver.com/item/main.naver?code={code}", "기본 시세, 뉴스, 종목 정보를 빠르게 확인합니다.", "시세"),
            ],
        ),
        _group(
            "수급",
            "외국인·기관 매매, 공매도, 거래량, 증자·락업 이벤트를 확인합니다.",
            [
                _resource("KRX 정보데이터시스템", "https://data.krx.co.kr/", "외국인·기관 거래, 공매도, 거래량 등 원자료를 확인합니다.", "KRX"),
                _resource("공매도 종합 포털", "https://short.krx.co.kr/", "공매도 잔고와 거래대금 관련 데이터를 확인합니다.", "공매도"),
                _resource("외국인 기관 수급 검색", _naver_search_url(f"{code} 외국인 기관 수급"), "외국인·기관 순매수 동향을 빠르게 검색합니다.", "수급"),
                _resource("락업 해제·증자 검색", _google_search_url(f"{code} {name} 보호예수 해제 증자 전환사채"), "공급 증가 이벤트를 검색합니다.", "공급"),
            ],
        ),
        _group(
            "산업·매크로",
            "기업 하나만 보지 말고 속한 산업과 금리·환율·원자재 환경을 같이 봅니다.",
            [
                _resource("한국은행 경제통계시스템", "https://ecos.bok.or.kr/", "금리, 환율, 경기, 통화 관련 국내 지표를 확인합니다.", "매크로"),
                _resource("산업 리포트 검색", _google_search_url(f"{name} 산업 리포트 전망"), "산업 구조와 수요·공급 전망 자료를 찾습니다.", "리포트"),
                _resource("원자재·환율 검색", _google_search_url(f"{name} 원자재 환율 수혜 리스크"), "원가와 환율 민감도를 확인합니다.", "매크로"),
            ],
        ),
    ]


def us_stock_resources(symbol: str, asset: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ticker = symbol.upper()
    name = (asset or {}).get("name") or ticker

    return [
        _group(
            "공시·실적",
            "미국 주식은 SEC 공시, 실적 발표, 컨퍼런스콜, 가이던스를 먼저 확인합니다.",
            [
                _resource("SEC EDGAR Company Search", f"https://www.sec.gov/edgar/search/#/q={quote_plus(ticker)}", "10-K, 10-Q, 8-K 등 원문 공시를 확인합니다.", "SEC"),
                _resource("Nasdaq Earnings", f"https://www.nasdaq.com/market-activity/stocks/{ticker.lower()}/earnings", "실적 발표일과 EPS 관련 정보를 확인합니다.", "실적"),
                _resource("IR 자료 검색", _google_search_url(f"{ticker} investor relations earnings presentation conference call"), "기업 IR, 프레젠테이션, 컨퍼런스콜 자료를 찾습니다.", "IR"),
                _resource("자사주·내부자 검색", _google_search_url(f"{ticker} buyback insider buying Form 4"), "자사주 매입과 내부자 매수·매도를 검색합니다.", "내부자"),
            ],
        ),
        _group(
            "수급·옵션",
            "기관 보유, ETF 편입, 옵션 포지션, 거래량으로 가격 뒤의 힘을 봅니다.",
            [
                _resource("Fintel Institutional Ownership 검색", _google_search_url(f"{ticker} institutional ownership fintel"), "기관 보유와 13F 관련 정보를 검색합니다.", "기관"),
                _resource("ETF 보유 검색", _google_search_url(f"{ticker} ETF holdings flow"), "어떤 ETF가 보유하고 있는지와 펀드 플로우를 검색합니다.", "ETF"),
                _resource("Options 정보 검색", _google_search_url(f"{ticker} options open interest put call ratio"), "옵션 미결제약정과 풋콜 쏠림을 검색합니다.", "옵션"),
                _resource("Short Interest 검색", _google_search_url(f"{ticker} short interest"), "공매도 비중과 숏커버 가능성을 검색합니다.", "공매도"),
            ],
        ),
        _group(
            "매크로·산업",
            "금리, 달러, 경기, 산업 사이클이 밸류에이션과 실적 기대를 바꿉니다.",
            [
                _resource("FRED - 미국 10년물 금리", "https://fred.stlouisfed.org/series/DGS10", "장기금리와 성장주 할인율 부담을 확인합니다.", "금리"),
                _resource("FRED - 달러 지수", "https://fred.stlouisfed.org/series/DTWEXBGS", "달러 강세·약세와 글로벌 매출 영향을 봅니다.", "달러"),
                _resource("산업 리포트 검색", _google_search_url(f"{name} industry report outlook"), "산업 성장률과 경쟁 구도를 검색합니다.", "리포트"),
            ],
        ),
    ]


def generic_resources(symbol: str, asset: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    name = (asset or {}).get("name") or symbol
    return [
        _group(
            "기본 원자료",
            "자산 성격이 불명확하므로 공시, 시세, 수급, 매크로 자료를 직접 확인합니다.",
            [
                _resource("Google 원자료 검색", _google_search_url(f"{name} official data report filing"), "공식 자료와 보고서를 검색합니다.", "검색"),
                _resource("Google 뉴스 검색", _google_search_url(f"{name} latest news market data"), "최근 뉴스와 시장 반응을 검색합니다.", "뉴스"),
                _resource("FRED", "https://fred.stlouisfed.org/", "금리, 환율, 유동성, 경기 지표를 확인합니다.", "매크로"),
            ],
        )
    ]


def build_evidence(symbol: str, asset: dict[str, Any] | None = None, fetch_news: bool = True) -> dict[str, Any]:
    symbol = _display_symbol(symbol)
    name = (asset or {}).get("name") or symbol

    if _is_crypto(symbol):
        category = "crypto"
        title = f"{name} 근거 데이터"
        groups = crypto_resources(symbol)
    elif _is_korean_stock(symbol):
        category = "korean_stock"
        title = f"{name} 공시·수급·뉴스"
        groups = korean_stock_resources(symbol, asset)
    elif _is_us_stock_or_etf(symbol):
        category = "us_stock"
        title = f"{name} 공시·수급·뉴스"
        groups = us_stock_resources(symbol, asset)
    else:
        category = "generic"
        title = f"{name} 근거 자료"
        groups = generic_resources(symbol, asset)

    query = _news_query_for(symbol, asset)
    news = fetch_google_news(query, limit=6) if fetch_news else []

    return {
        "symbol": symbol,
        "name": name,
        "category": category,
        "title": title,
        "query": query,
        "news_rss_url": _google_news_rss(query),
        "news_search_url": _google_search_url(query),
        "groups": groups,
        "news": news,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def build_evidence_index() -> list[dict[str, str]]:
    return [
        {
            "title": "BTC 수급·온체인",
            "symbol": "BTC-USD",
            "description": "ETF 플로우, 펀딩비, 미결제약정, 청산맵, 온체인 데이터를 확인합니다.",
        },
        {
            "title": "ETH 수급·온체인",
            "symbol": "ETH-USD",
            "description": "ETF, 스테이킹, 온체인, 파생시장 데이터를 확인합니다.",
        },
        {
            "title": "QQQ",
            "symbol": "QQQ",
            "description": "미국 성장주 ETF의 금리, 수급, 구성종목, 뉴스 흐름을 봅니다.",
        },
        {
            "title": "SPY",
            "symbol": "SPY",
            "description": "미국 대표지수 ETF의 매크로, 펀드 플로우, 시장 뉴스를 봅니다.",
        },
        {
            "title": "삼성전자",
            "symbol": "005930.KS",
            "description": "공시, 외국인·기관 수급, 반도체 업황, 실적 자료를 확인합니다.",
        },
        {
            "title": "한화에어로스페이스",
            "symbol": "012450.KS",
            "description": "수주, 실적, 방산 산업 리포트, 공시와 수급을 확인합니다.",
        },
    ]

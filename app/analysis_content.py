from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from markupsafe import Markup, escape
import re


CONTENT_DIR = Path("content/analysis")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    text = text.strip()

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    raw_meta = parts[1].strip()
    body = parts[2].strip()

    meta = {}
    for line in raw_meta.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")

    return meta, body


def slug_from_path(path: Path) -> str:
    return path.stem


def simple_markdown_to_html(text: str) -> Markup:
    """
    외부 markdown 의존성을 늘리지 않기 위한 아주 간단한 변환기.
    제목, 목록, 문단 정도만 처리합니다.
    """
    lines = text.strip().splitlines()
    html = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.strip()

        if not line:
            close_list()
            continue

        if line.startswith("### "):
            close_list()
            html.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("## "):
            close_list()
            html.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("# "):
            close_list()
            html.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("- "):
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{escape(line[2:])}</li>")
        else:
            close_list()
            html.append(f"<p>{escape(line)}</p>")

    close_list()
    return Markup("\n".join(html))


def load_analysis_posts() -> list[dict[str, Any]]:
    if not CONTENT_DIR.exists():
        return []

    posts = []

    for path in sorted(CONTENT_DIR.glob("*.md"), reverse=True):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        slug = meta.get("slug") or slug_from_path(path)

        posts.append(
            {
                "slug": slug,
                "symbol": meta.get("symbol", ""),
                "title": meta.get("title", slug),
                "date": meta.get("date", ""),
                "category": meta.get("category", ""),
                "status": meta.get("status", "관찰"),
                "summary": meta.get("summary", ""),
                "watch_price": meta.get("watch_price", ""),
                "invalid": meta.get("invalid", ""),
                "chart_image": meta.get("chart_image", ""),
                "tradingview_url": meta.get("tradingview_url", ""),
                "body": body,
                "body_html": simple_markdown_to_html(body),
            }
        )

    posts.sort(key=lambda x: x.get("date", ""), reverse=True)
    return posts


def get_analysis_post(slug: str) -> dict[str, Any] | None:
    for post in load_analysis_posts():
        if post["slug"] == slug:
            return post
    return None


def get_related_posts(symbol: str, limit: int = 3) -> list[dict[str, Any]]:
    if not symbol:
        return []

    normalized = symbol.upper()
    posts = [
        p for p in load_analysis_posts()
        if p.get("symbol", "").upper() == normalized
    ]

    return posts[:limit]

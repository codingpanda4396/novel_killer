from __future__ import annotations

import hashlib
import html
import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from .base import BaseCollector
from ..models import RawNovelSignal


USER_AGENT = "NovelRadar/0.1 (+public ranking research; no paid content)"
NAV_WORDS = {
    "首页", "书库", "排行", "排行榜", "分类", "登录", "注册", "更多", "全部",
    "男生", "女生", "原创", "言情", "玄幻", "都市", "历史", "科幻", "游戏",
}


@dataclass(frozen=True)
class CollectorIssue:
    source: str
    url: str
    status: str
    message: str


@dataclass(frozen=True)
class ParsedBook:
    title: str
    author: str | None = None
    category: str | None = None
    description: str | None = None
    rank_position: int | None = None
    source_url: str | None = None
    external_book_id: str | None = None
    metric_name: str | None = None
    metric_value: float | None = None
    metric_text: str | None = None
    tags: list[str] | None = None
    word_count: str | None = None
    status: str | None = None
    update_time: str | None = None


class _LinkTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_href: str | None = None
        self._buffer: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attrs_dict = dict(attrs)
            self._current_href = attrs_dict.get("href")
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href is not None:
            text = clean_text("".join(self._buffer))
            if text:
                self.links.append((self._current_href, text))
            self._current_href = None
            self._buffer = []


class WebCollector(BaseCollector):
    """Public web page collector with robots checks, rate limiting and snapshots."""

    request_interval_seconds = 3.0
    timeout_seconds = 15

    def __init__(
        self,
        rank_type: str = "hot",
        category: str | None = None,
        limit: int = 50,
        snapshot_dir: Path | None = None,
        use_playwright: bool = False,
        respect_robots: bool = True,
    ):
        self.rank_type = rank_type
        self.category = category
        self.limit = limit
        self.snapshot_dir = snapshot_dir or Path("runtime/radar/snapshots")
        self.use_playwright = use_playwright
        self.respect_robots = respect_robots
        self.issues: list[CollectorIssue] = []
        self._last_request_at: dict[str, float] = {}

    def fetch_html(self, url: str) -> str | None:
        if self.respect_robots and not self._allowed_by_robots(url):
            self._issue(url, "blocked", "robots.txt disallows this URL")
            return None

        parsed = urlparse(url)
        domain = parsed.netloc
        wait = self.request_interval_seconds - (time.monotonic() - self._last_request_at.get(domain, 0))
        if wait > 0:
            time.sleep(wait)

        try:
            import requests
        except Exception as exc:
            self._issue(url, "dependency_missing", f"requests is not installed: {exc}")
            return None

        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"},
                timeout=self.timeout_seconds,
            )
            self._last_request_at[domain] = time.monotonic()
        except Exception as exc:
            self._issue(url, "network_error", str(exc))
            return None

        if response.status_code in {401, 403, 429}:
            self._issue(url, "blocked", f"HTTP {response.status_code}")
            return None
        if response.status_code >= 400:
            self._issue(url, "http_error", f"HTTP {response.status_code}")
            return None

        response.encoding = response.apparent_encoding or response.encoding
        html_text = response.text
        if len(clean_text(html_text)) < 50 and self.use_playwright:
            html_text = self._fetch_with_playwright(url) or html_text
        self.save_snapshot(url, html_text)
        return html_text

    def save_snapshot(self, url: str, html_text: str) -> Path:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        parsed = urlparse(url)
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{parsed.netloc.replace('.', '_')}_{stamp}_{digest}.html"
        path = self.snapshot_dir / filename
        path.write_text(html_text, encoding="utf-8")
        return path

    def _fetch_with_playwright(self, url: str) -> str | None:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            self._issue(url, "dependency_missing", f"playwright is not installed: {exc}")
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(url, wait_until="networkidle", timeout=self.timeout_seconds * 1000)
                html_text = page.content()
                browser.close()
                return html_text
        except Exception as exc:
            self._issue(url, "playwright_error", str(exc))
            return None

    def _allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception as exc:
            self._issue(url, "robots_error", f"cannot read robots.txt: {exc}")
            return False
        return rp.can_fetch(USER_AGENT, url)

    def _issue(self, url: str, status: str, message: str) -> None:
        self.issues.append(CollectorIssue(self.source, url, status, message))


class RankPageCollector(WebCollector):
    platform = ""
    source_key = ""
    rank_urls: dict[str, str] = {}
    rank_metric_names: dict[str, str] = {}

    @property
    def name(self) -> str:
        return f"{self.platform} {self.rank_type} Collector"

    @property
    def source(self) -> str:
        return self.source_key

    def collect(self) -> list[RawNovelSignal]:
        url = self.rank_urls.get(self.rank_type) or self.rank_urls.get("hot")
        if not url:
            self._issue("", "config_error", f"unknown rank type: {self.rank_type}")
            return []
        html_text = self.fetch_html(url)
        if not html_text:
            return []
        books = parse_rank_html(
            html_text,
            base_url=url,
            rank_type=self.rank_type,
            metric_name=self.rank_metric_names.get(self.rank_type),
            limit=self.limit,
        )
        if not books:
            self._issue(url, "parse_error", "no books parsed from public page")
            return []
        return [
            parsed_book_to_signal(
                book,
                source=self.source,
                platform=self.platform,
                rank_type=self.rank_type,
                collected_at=datetime.now(timezone.utc).isoformat(),
            )
            for book in books[: self.limit]
        ]


def parse_rank_html(
    html_text: str,
    base_url: str,
    rank_type: str,
    metric_name: str | None = None,
    limit: int = 50,
) -> list[ParsedBook]:
    books = _parse_books_from_structured_json(html_text, base_url, metric_name)
    if len(books) < max(1, min(limit, 5)):
        books.extend(_parse_books_from_blocks(html_text, base_url, metric_name))
    return _dedupe_books(books)[:limit]


def parsed_book_to_signal(
    book: ParsedBook,
    source: str,
    platform: str,
    rank_type: str,
    collected_at: str,
) -> RawNovelSignal:
    snapshot_date = date.fromisoformat(collected_at[:10]).isoformat()
    identity = book.external_book_id or book.source_url or book.title
    signal_digest = hashlib.sha1(f"{source}:{identity}".encode("utf-8")).hexdigest()[:12]
    metric_value = book.metric_value
    hot_score = normalize_metric(metric_value, metric_name=book.metric_name, rank_position=book.rank_position)
    raw_payload: dict[str, Any] = {
        "source_url": book.source_url,
        "external_book_id": book.external_book_id,
        "rank_metric_name": book.metric_name,
        "rank_metric_value": metric_value,
        "rank_metric_text": book.metric_text,
        "word_count": book.word_count,
        "status": book.status,
        "update_time": book.update_time,
        "snapshot_date": snapshot_date,
    }
    return RawNovelSignal(
        signal_id=f"{source}_{signal_digest}",
        source=source,
        source_type="ranking",
        platform=platform,
        rank_type=rank_type,
        rank_position=book.rank_position,
        title=book.title,
        author=book.author,
        category=book.category,
        tags=book.tags or [],
        description=book.description,
        hot_score=hot_score,
        read_count=int(metric_value) if book.metric_name and "读" in book.metric_name and metric_value else None,
        collected_at=collected_at,
        raw_payload=raw_payload,
    )


def normalize_metric(
    value: float | None,
    metric_name: str | None = None,
    rank_position: int | None = None,
) -> float:
    if value is not None:
        name = metric_name or ""
        if any(key in name for key in ("在读", "阅读", "点击")):
            return max(1.0, min(100.0, 20.0 + value / 50000.0))
        if any(key in name for key in ("月票", "推荐", "收藏", "霸王票", "畅销")):
            return max(1.0, min(100.0, 25.0 + value / 1000.0))
        return max(1.0, min(100.0, value))
    if rank_position:
        return max(1.0, min(100.0, 101.0 - rank_position))
    return 50.0


def parse_metric_value(text: str) -> float | None:
    text = text.replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(万|亿|千)?", text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit == "千":
        value *= 1000
    elif unit == "万":
        value *= 10000
    elif unit == "亿":
        value *= 100000000
    return value


def clean_text(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.S | re.I)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.S | re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _parse_books_from_structured_json(
    html_text: str,
    base_url: str,
    metric_name: str | None,
) -> list[ParsedBook]:
    books: list[ParsedBook] = []
    for script_body in re.findall(r"<script[^>]*>(.*?)</script>", html_text, flags=re.S | re.I):
        body = html.unescape(script_body).strip()
        if not body or not any(key in body for key in ("book", "title", "书名", "bookName")):
            continue
        candidates = re.findall(r"\{[^{}]*(?:bookName|book_name|title|书名)[^{}]*\}", body)
        for raw in candidates[:100]:
            try:
                item = json.loads(raw)
            except Exception:
                continue
            title = _first(item, "bookName", "book_name", "title", "name", "书名")
            if not _looks_like_title(title):
                continue
            href = _first(item, "bookUrl", "url", "href", "link")
            book_id = str(_first(item, "bookId", "book_id", "id") or "") or None
            books.append(ParsedBook(
                title=title,
                author=_first(item, "author", "authorName", "writer", "作者"),
                category=_first(item, "category", "catName", "type", "分类"),
                description=_first(item, "abstract", "intro", "description", "desc", "简介"),
                source_url=urljoin(base_url, href) if href else None,
                external_book_id=book_id,
                metric_name=metric_name,
                metric_value=parse_metric_value(str(_first(item, "score", "hot", "readCount", "cnt") or "")),
            ))
    return books


def _parse_books_from_blocks(
    html_text: str,
    base_url: str,
    metric_name: str | None,
) -> list[ParsedBook]:
    blocks = re.findall(
        r"<(?:li|article|dd|div)\b[^>]*(?:book|rank|item|list|作品|小说)[^>]*>.*?</(?:li|article|dd|div)>",
        html_text,
        flags=re.S | re.I,
    )
    if not blocks:
        blocks = re.findall(r"<li\b[^>]*>.*?</li>", html_text, flags=re.S | re.I)

    books: list[ParsedBook] = []
    for idx, block in enumerate(blocks, 1):
        link_parser = _LinkTextParser()
        try:
            link_parser.feed(block)
        except Exception:
            continue
        title_link = _pick_title_link(link_parser.links)
        if not title_link:
            continue
        href, title = title_link
        block_text = clean_text(block)
        metric_text = _extract_metric_text(block_text, metric_name)
        books.append(ParsedBook(
            title=title,
            author=_extract_author(block_text),
            category=_extract_category(block_text),
            description=_extract_description(block),
            rank_position=_extract_rank_position(block_text) or idx,
            source_url=urljoin(base_url, href),
            external_book_id=_extract_book_id(href),
            metric_name=metric_name,
            metric_text=metric_text,
            metric_value=parse_metric_value(metric_text or ""),
            tags=_extract_tags(block_text),
            word_count=_extract_word_count(block_text),
            status=_extract_status(block_text),
            update_time=_extract_update_time(block_text),
        ))
    return books


def _dedupe_books(books: list[ParsedBook]) -> list[ParsedBook]:
    seen: set[str] = set()
    result: list[ParsedBook] = []
    for i, book in enumerate(books, 1):
        key = book.external_book_id or book.source_url or book.title
        if not book.title or key in seen:
            continue
        seen.add(key)
        if book.rank_position is None:
            book = ParsedBook(**{**book.__dict__, "rank_position": i})
        result.append(book)
    return result


def _pick_title_link(links: list[tuple[str, str]]) -> tuple[str, str] | None:
    for href, text in links:
        if _looks_like_title(text) and not any(word == text for word in NAV_WORDS):
            return href, text
    return None


def _looks_like_title(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = clean_text(value)
    return 2 <= len(text) <= 60 and not text.startswith("http") and text not in NAV_WORDS


def _first(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key]:
            return item[key]
    return None


def _extract_author(text: str) -> str | None:
    patterns = [
        r"(?:作者|作家)[:：]?\s*([\u4e00-\u9fa5A-Za-z0-9_\-]{2,24})",
        r"([\u4e00-\u9fa5A-Za-z0-9_\-]{2,24})\s*(?:著|作品)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1)
            if value not in NAV_WORDS:
                return value
    return None


def _extract_category(text: str) -> str | None:
    for word in ("玄幻", "奇幻", "武侠", "仙侠", "都市", "现实", "军事", "历史", "游戏", "体育", "科幻", "悬疑", "轻小说", "言情", "古言", "现言", "青春", "纯爱"):
        if word in text:
            return word
    return None


def _extract_description(block: str) -> str | None:
    for pattern in (r"<p[^>]*(?:intro|desc|简介)[^>]*>(.*?)</p>", r"<p[^>]*>(.*?)</p>"):
        match = re.search(pattern, block, flags=re.S | re.I)
        if match:
            text = clean_text(match.group(1))
            if 8 <= len(text) <= 300:
                return text
    return None


def _extract_rank_position(text: str) -> int | None:
    match = re.search(r"(?:第\s*)?(\d{1,3})(?:\s*名)?", text)
    if match:
        return int(match.group(1))
    return None


def _extract_metric_text(text: str, metric_name: str | None) -> str | None:
    if metric_name:
        match = re.search(rf"(\d+(?:\.\d+)?\s*(?:万|亿|千)?\s*{re.escape(metric_name)})", text)
        if match:
            return match.group(1)
    match = re.search(r"(\d+(?:\.\d+)?\s*(?:万|亿|千)?\s*(?:人在读|阅读|点击|月票|推荐票?|收藏|霸王票|畅销|热度|总分))", text)
    return match.group(1) if match else None


def _extract_tags(text: str) -> list[str]:
    tags = []
    for word in ("重生", "穿越", "系统", "爽文", "打脸", "逆袭", "甜宠", "豪门", "末世", "囤货", "空间", "高武", "修仙", "反派", "种田", "年代"):
        if word in text:
            tags.append(word)
    return tags


def _extract_word_count(text: str) -> str | None:
    match = re.search(r"(\d+(?:\.\d+)?\s*万?字)", text)
    return match.group(1) if match else None


def _extract_status(text: str) -> str | None:
    for word in ("连载", "完结", "已完结"):
        if word in text:
            return word
    return None


def _extract_update_time(text: str) -> str | None:
    match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2})", text)
    return match.group(1) if match else None


def _extract_book_id(href: str) -> str | None:
    match = re.search(r"(\d{4,})", href)
    return match.group(1) if match else None

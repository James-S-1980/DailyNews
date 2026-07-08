import argparse
import datetime as dt
import email.utils
import html
import os
import re
import smtplib
import ssl
import sys
import textwrap
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
LOG_DIR = BASE_DIR / "logs"
DEFAULT_RECIPIENT = "james.schliesske@gmail.com"


SECTIONS = {
    "Top News": [
        ("CNN", "http://rss.cnn.com/rss/cnn_topstories.rss"),
        ("NBC News", "https://feeds.nbcnews.com/nbcnews/public/news"),
        ("BBC News", "https://feeds.bbci.co.uk/news/rss.xml"),
        ("WSJ", "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
        ("NPR", "https://feeds.npr.org/1001/rss.xml"),
    ],
    "World News": [
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("CNN World", "http://rss.cnn.com/rss/cnn_world.rss"),
        ("NBC World", "https://feeds.nbcnews.com/nbcnews/public/world"),
        ("WSJ World", "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
        ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "Technology News": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        ("Wired", "https://www.wired.com/feed/rss"),
        ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
        ("Engadget", "https://www.engadget.com/rss.xml"),
    ],
}


@dataclass(frozen=True)
class Article:
    title: str
    summary: str
    source: str
    link: str
    published: dt.datetime


def load_env() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_date(value: str) -> dt.datetime:
    if not value:
        return dt.datetime.now(dt.timezone.utc)
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return dt.datetime.now(dt.timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def child_text(item: ET.Element, names: Iterable[str]) -> str:
    for name in names:
        node = item.find(name)
        if node is not None and node.text:
            return node.text

    # ElementTree namespace matching can be fussy for mixed feeds, so fall back
    # to suffix matching for common RSS/Atom fields.
    wanted = {name.split("}")[-1] for name in names}
    for node in item:
        if node.tag.split("}")[-1] in wanted and node.text:
            return node.text
    return ""


def item_link(item: ET.Element) -> str:
    direct = child_text(item, ["link", "{http://www.w3.org/2005/Atom}link"])
    if direct:
        return direct.strip()
    for node in item:
        if node.tag.split("}")[-1] == "link":
            href = node.attrib.get("href", "")
            if href:
                return href.strip()
    return ""


def summarize(title: str, description: str) -> str:
    description = clean_text(description)
    if not description:
        return f"{title} is among the latest headlines from this source. Open the full article for the complete report and context."

    sentences = re.split(r"(?<=[.!?])\s+", description)
    selected = [sentence.strip() for sentence in sentences if sentence.strip()][:3]
    summary = " ".join(selected)
    if len(summary) > 520:
        summary = textwrap.shorten(summary, width=520, placeholder="...")
    if len(selected) == 1:
        summary += " The full story has additional context and updates from the source."
    return summary


def is_obviously_stale(article: Article) -> bool:
    current_year = dt.datetime.now(dt.timezone.utc).year
    years = [int(match) for match in re.findall(r"/(20\d{2})/", article.link)]
    for month, day, year in re.findall(r"(?:/|-)(\d{2})-(\d{2})-(\d{2})(?:/|$)", article.link):
        month_number = int(month)
        day_number = int(day)
        full_year = 2000 + int(year)
        if 1 <= month_number <= 12 and 1 <= day_number <= 31:
            years.append(full_year)
    return any(year < current_year - 1 for year in years)


def fetch_feed(source: str, url: str, max_items: int = 8) -> list[Article]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "daily-headlines-newsletter/1.0 (+https://localhost)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        log(f"Feed failed: {source} {url} ({exc})")
        return []

    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        log(f"Feed parse failed: {source} {url} ({exc})")
        return []

    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    articles: list[Article] = []
    for item in items[:max_items]:
        title = clean_text(child_text(item, ["title", "{http://www.w3.org/2005/Atom}title"]))
        link = clean_text(item_link(item))
        description = child_text(
            item,
            [
                "description",
                "summary",
                "content",
                "{http://www.w3.org/2005/Atom}summary",
                "{http://purl.org/rss/1.0/modules/content/}encoded",
            ],
        )
        published_raw = child_text(
            item,
            [
                "pubDate",
                "published",
                "updated",
                "{http://www.w3.org/2005/Atom}published",
                "{http://www.w3.org/2005/Atom}updated",
            ],
        )
        if title and link:
            articles.append(
                Article(
                    title=title,
                    summary=summarize(title, description),
                    source=source,
                    link=link,
                    published=parse_date(published_raw),
                )
            )
    return articles


def collect_section(feed_specs: list[tuple[str, str]], target_count: int = 8) -> list[Article]:
    articles_by_source: list[list[Article]] = []
    seen_links: set[str] = set()
    seen_titles: set[str] = set()

    for source, url in feed_specs:
        source_articles: list[Article] = []
        for article in fetch_feed(source, url):
            title_key = re.sub(r"\W+", "", article.title).lower()
            if article.link in seen_links or title_key in seen_titles or is_obviously_stale(article):
                continue
            seen_links.add(article.link)
            seen_titles.add(title_key)
            source_articles.append(article)
        source_articles.sort(key=lambda item: item.published, reverse=True)
        if source_articles:
            articles_by_source.append(source_articles)
        time.sleep(0.4)

    selected: list[Article] = []
    index = 0
    while len(selected) < target_count:
        added = False
        for source_articles in articles_by_source:
            if index < len(source_articles):
                selected.append(source_articles[index])
                added = True
                if len(selected) == target_count:
                    break
        if not added:
            break
        index += 1
    return selected


def html_escape(value: str) -> str:
    return html.escape(value, quote=True)


def build_html(sections: dict[str, list[Article]]) -> str:
    today = dt.datetime.now().strftime("%A, %B %-d, %Y") if os.name != "nt" else dt.datetime.now().strftime("%A, %B %#d, %Y")
    parts = [
        "<!doctype html>",
        "<html>",
        "<body style=\"margin:0;background:#f5f7fb;color:#1f2937;font-family:Arial,Helvetica,sans-serif;\">",
        "<div style=\"max-width:760px;margin:0 auto;padding:28px 18px;\">",
        "<h1 style=\"margin:0 0 6px;font-size:28px;color:#111827;\">Daily Headlines</h1>",
        f"<p style=\"margin:0 0 24px;color:#4b5563;\">{html_escape(today)}</p>",
    ]

    for section_name, articles in sections.items():
        parts.append(f"<h2 style=\"border-bottom:2px solid #d1d5db;padding-bottom:8px;margin:28px 0 14px;color:#111827;\">{html_escape(section_name)}</h2>")
        if not articles:
            parts.append("<p>No stories were available from the configured feeds this morning.</p>")
            continue
        for index, article in enumerate(articles, start=1):
            parts.extend(
                [
                    "<div style=\"background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:0 0 14px;\">",
                    f"<h3 style=\"font-size:18px;line-height:1.35;margin:0 0 8px;\">{index}. <a href=\"{html_escape(article.link)}\" style=\"color:#0f766e;text-decoration:none;\">{html_escape(article.title)}</a></h3>",
                    f"<p style=\"font-size:14px;line-height:1.55;margin:0 0 10px;\">{html_escape(article.summary)}</p>",
                    f"<p style=\"font-size:13px;color:#6b7280;margin:0;\">Source: {html_escape(article.source)} | <a href=\"{html_escape(article.link)}\" style=\"color:#2563eb;\">Full article</a></p>",
                    "</div>",
                ]
            )

    parts.extend(
        [
            "<p style=\"font-size:12px;color:#6b7280;margin-top:28px;\">Generated automatically from RSS feeds. Some linked articles may require a subscription.</p>",
            "</div>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(parts)


def build_text(sections: dict[str, list[Article]]) -> str:
    today = dt.datetime.now().strftime("%A, %B %d, %Y")
    lines = [f"Daily Headlines - {today}", ""]
    for section_name, articles in sections.items():
        lines.extend([section_name, "-" * len(section_name)])
        if not articles:
            lines.extend(["No stories were available from the configured feeds this morning.", ""])
            continue
        for index, article in enumerate(articles, start=1):
            lines.extend(
                [
                    f"{index}. {article.title}",
                    f"Summary: {article.summary}",
                    f"Source: {article.source}",
                    f"Link: {article.link}",
                    "",
                ]
            )
    return "\n".join(lines)


def build_newsletter() -> tuple[str, str, dict[str, list[Article]]]:
    sections = {section: collect_section(feeds) for section, feeds in SECTIONS.items()}
    return build_html(sections), build_text(sections), sections


def send_email(subject: str, html_body: str, text_body: str) -> None:
    sender = os.environ.get("SMTP_USERNAME", DEFAULT_RECIPIENT)
    recipient = os.environ.get("NEWSLETTER_RECIPIENT", DEFAULT_RECIPIENT)
    password = os.environ.get("SMTP_APP_PASSWORD", "").replace(" ", "")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))

    if not password:
        raise RuntimeError("SMTP_APP_PASSWORD is missing. Add it to .env before sending.")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(sender, password)
        server.send_message(message)


def log(message: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with (LOG_DIR / "newsletter.log").open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and send the Daily Headlines newsletter.")
    parser.add_argument("--dry-run", action="store_true", help="Build the newsletter and print a text preview without sending.")
    parser.add_argument("--save-html", action="store_true", help="Save the generated HTML to latest_newsletter.html.")
    args = parser.parse_args()

    load_env()
    try:
        html_body, text_body, sections = build_newsletter()
        total = sum(len(items) for items in sections.values())
        subject = f"Daily Headlines - {dt.datetime.now().strftime('%B %d, %Y')}"

        if args.save_html or args.dry_run:
            (BASE_DIR / "latest_newsletter.html").write_text(html_body, encoding="utf-8")

        if args.dry_run:
            print(text_body)
            print(f"\nPreview saved to {BASE_DIR / 'latest_newsletter.html'}")
            log(f"Dry run completed with {total} articles.")
            return 0

        send_email(subject, html_body, text_body)
        log(f"Sent newsletter with {total} articles.")
        return 0
    except Exception as exc:
        log(f"ERROR: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

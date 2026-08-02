import argparse
import datetime as dt
import email.utils
import html
import json
import mimetypes
import os
import re
import smtplib
import ssl
import subprocess
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
GENERAL_RECIPIENT = "james.schliesske@gmail.com"
DEFENSE_RECIPIENT = "James.d.schliesske.civ@army.mil"
DEFAULT_MAX_ARTICLE_AGE_DAYS = 3
PODCAST_TITLE = "Daily Headlines Podcast"
PODCAST_RECIPIENT = GENERAL_RECIPIENT
PODCAST_DIR = BASE_DIR / "podcasts"
PODCAST_SCRIPT_WORD_TARGET = 2600
PODCAST_TTS_CHARS_PER_CHUNK = 3600


GENERAL_SECTIONS = {
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


DEFENSE_SECTIONS = {
    "Defense Headlines": [
        ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
        ("Stars and Stripes", "https://subscribe.stripes.com/rss/top-news.xml"),
        ("TWZ", "https://www.twz.com/feed"),
        ("Breaking Defense", "https://breakingdefense.com/feed/"),
        ("Defense One", "https://www.defenseone.com/rss/all/"),
        ("Military Times", "https://www.militarytimes.com/arc/outboundfeeds/rss/"),
        ("USNI News", "https://news.usni.org/feed"),
    ],
    "Military Services": [
        ("Army Times", "https://www.armytimes.com/arc/outboundfeeds/rss/"),
        ("Air Force Times", "https://www.airforcetimes.com/arc/outboundfeeds/rss/"),
        ("Marine Corps Times", "https://www.marinecorpstimes.com/arc/outboundfeeds/rss/"),
        ("Navy Times", "https://www.navytimes.com/arc/outboundfeeds/rss/"),
        ("Stars and Stripes U.S.", "https://subscribe.stripes.com/rss/us.xml"),
        ("USNI News", "https://news.usni.org/feed"),
        ("Air & Space Forces Magazine", "https://www.airandspaceforces.com/feed/"),
    ],
    "Defense Technology & Industry": [
        ("C4ISRNET", "https://www.c4isrnet.com/arc/outboundfeeds/rss/"),
        ("Breaking Defense", "https://breakingdefense.com/feed/"),
        ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
        ("TWZ", "https://www.twz.com/feed"),
        ("Naval News", "https://www.navalnews.com/feed/"),
        ("Air & Space Forces Magazine", "https://www.airandspaceforces.com/feed/"),
    ],
    "C4ISR": [
        ("C4ISRNET", "https://www.c4isrnet.com/arc/outboundfeeds/rss/"),
        ("Breaking Defense", "https://breakingdefense.com/feed/"),
        ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
        ("Defense One", "https://www.defenseone.com/rss/all/"),
        ("TWZ", "https://www.twz.com/feed"),
        ("Air & Space Forces Magazine", "https://www.airandspaceforces.com/feed/"),
    ],
    "Field Artillery": [
        ("Army Times", "https://www.armytimes.com/arc/outboundfeeds/rss/"),
        ("Military Times", "https://www.militarytimes.com/arc/outboundfeeds/rss/"),
        ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
        ("Breaking Defense", "https://breakingdefense.com/feed/"),
        ("TWZ", "https://www.twz.com/feed"),
        ("Defense One", "https://www.defenseone.com/rss/all/"),
        ("Defence Blog", "https://defence-blog.com/feed/"),
        ("Army Technology", "https://www.army-technology.com/feed/"),
    ],
}


DEFENSE_SECTION_KEYWORDS = {
    "C4ISR": [
        "c4isr",
        "command and control",
        "jadc2",
        "cjadc2",
        "sensor",
        "sensors",
        "electronic warfare",
        "spectrum",
        "cyber",
        "satellite",
        "space force",
        "isr",
        "intelligence",
        "surveillance",
        "reconnaissance",
        "network",
        "networks",
        "communications",
        "data link",
        "radar",
    ],
    "Field Artillery": [
        "field artillery",
        "artillery",
        "howitzer",
        "howitzers",
        "cannon",
        "long-range fires",
        "long range fires",
        "precision fires",
        "fires",
        "mlrs",
        "himars",
        "m270",
        "paladin",
        "m109",
        "155mm",
        "rocket artillery",
        "counterfire",
        "mortar",
        "munitions",
        "ammunition",
        "ammo",
        "projectile",
        "projectiles",
        "missile",
        "missiles",
        "rocket",
        "rockets",
        "launcher",
        "launchers",
        "strike",
        "strikes",
        "fire support",
        "surface-to-surface",
        "land warfare",
    ],
}


NEWSLETTERS = {
    "general": {
        "title": "Daily Headlines",
        "recipient_env": "GENERAL_NEWSLETTER_RECIPIENT",
        "default_recipient": GENERAL_RECIPIENT,
        "sections": GENERAL_SECTIONS,
        "preview_file": "latest_general_newsletter.html",
        "user_agent": "daily-headlines-newsletter/1.0 (+https://localhost)",
    },
    "defense": {
        "title": "Defense Daily",
        "recipient_env": "DEFENSE_NEWSLETTER_RECIPIENT",
        "default_recipient": DEFENSE_RECIPIENT,
        "sections": DEFENSE_SECTIONS,
        "section_keywords": DEFENSE_SECTION_KEYWORDS,
        "preview_file": "latest_defense_newsletter.html",
        "user_agent": "defense-daily-newsletter/1.0 (+https://localhost)",
    },
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


def max_article_age() -> dt.timedelta:
    raw_value = os.environ.get("MAX_ARTICLE_AGE_DAYS", str(DEFAULT_MAX_ARTICLE_AGE_DAYS))
    try:
        days = float(raw_value)
    except ValueError:
        days = DEFAULT_MAX_ARTICLE_AGE_DAYS
    return dt.timedelta(days=max(days, 0.25))


def is_recent(article: Article, max_age: dt.timedelta) -> bool:
    published = article.published
    if published.tzinfo is None:
        published = published.replace(tzinfo=dt.timezone.utc)
    now = dt.datetime.now(dt.timezone.utc)
    if published > now + dt.timedelta(hours=12):
        return False
    return now - published.astimezone(dt.timezone.utc) <= max_age


def matches_keywords(article: Article, keywords: list[str] | None) -> bool:
    if not keywords:
        return True
    haystack = f"{article.title} {article.summary}".lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def is_probably_english(article: Article) -> bool:
    text = f"{article.title} {article.summary}".lower()
    if "telemundo.com" in article.link.lower():
        return False
    if re.search(r"[¿¡ñ]", text):
        return False

    words = re.findall(r"[a-záéíóúü]+", text)
    if not words:
        return True

    spanish_words = {
        "asi",
        "así",
        "con",
        "del",
        "de",
        "el",
        "en",
        "esta",
        "este",
        "la",
        "las",
        "los",
        "marruecos",
        "para",
        "por",
        "que",
        "se",
        "su",
        "tras",
        "una",
        "un",
        "y",
    }
    english_words = {
        "a",
        "about",
        "after",
        "and",
        "as",
        "for",
        "from",
        "has",
        "in",
        "is",
        "of",
        "on",
        "said",
        "says",
        "the",
        "this",
        "to",
        "with",
    }
    spanish_count = sum(1 for word in words if word in spanish_words)
    english_count = sum(1 for word in words if word in english_words)
    accented_count = len(re.findall(r"[áéíóúü]", text))

    if spanish_count >= 3 and spanish_count > english_count:
        return False
    if accented_count >= 2 and spanish_count >= english_count:
        return False
    return True


def fetch_feed(source: str, url: str, user_agent: str, max_items: int = 8) -> list[Article]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
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


def collect_section(
    feed_specs: list[tuple[str, str]],
    user_agent: str,
    keywords: list[str] | None = None,
    target_count: int = 8,
) -> list[Article]:
    articles_by_source: list[list[Article]] = []
    seen_links: set[str] = set()
    seen_titles: set[str] = set()
    recent_age = max_article_age()

    for source, url in feed_specs:
        source_articles: list[Article] = []
        for article in fetch_feed(source, url, user_agent):
            title_key = re.sub(r"\W+", "", article.title).lower()
            if (
                article.link in seen_links
                or title_key in seen_titles
                or is_obviously_stale(article)
                or not is_recent(article, recent_age)
                or not is_probably_english(article)
                or not matches_keywords(article, keywords)
            ):
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


def build_html(title: str, sections: dict[str, list[Article]]) -> str:
    today = dt.datetime.now().strftime("%A, %B %-d, %Y") if os.name != "nt" else dt.datetime.now().strftime("%A, %B %#d, %Y")
    parts = [
        "<!doctype html>",
        "<html>",
        "<body style=\"margin:0;background:#f5f7fb;color:#1f2937;font-family:Arial,Helvetica,sans-serif;\">",
        "<div style=\"max-width:760px;margin:0 auto;padding:28px 18px;\">",
        f"<h1 style=\"margin:0 0 6px;font-size:28px;color:#111827;\">{html_escape(title)}</h1>",
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


def build_text(title: str, sections: dict[str, list[Article]]) -> str:
    today = dt.datetime.now().strftime("%A, %B %d, %Y")
    lines = [f"{title} - {today}", ""]
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


def build_newsletter(config: dict) -> tuple[str, str, dict[str, list[Article]]]:
    user_agent = config["user_agent"]
    section_keywords = config.get("section_keywords", {})
    sections = {
        section: collect_section(feeds, user_agent, section_keywords.get(section))
        for section, feeds in config["sections"].items()
    }
    title = config["title"]
    return build_html(title, sections), build_text(title, sections), sections


def send_email(
    subject: str,
    html_body: str,
    text_body: str,
    recipient: str,
    attachments: list[Path] | None = None,
) -> None:
    sender = os.environ.get("SMTP_USERNAME", GENERAL_RECIPIENT)
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

    for attachment in attachments or []:
        content_type, _ = mimetypes.guess_type(attachment.name)
        if content_type:
            maintype, subtype = content_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        message.add_attachment(
            attachment.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=attachment.name,
        )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(sender, password)
        server.send_message(message)


def selected_podcast_newsletters() -> list[str]:
    raw_value = os.environ.get("PODCAST_NEWSLETTERS", "general,defense")
    names = [value.strip().lower() for value in raw_value.split(",") if value.strip()]
    return [name for name in names if name in NEWSLETTERS] or ["general"]


def podcast_article_limit(section_name: str) -> int:
    if section_name in {"C4ISR", "Field Artillery"}:
        return 3
    return 6


def podcast_script_from_sections(newsletter_sections: dict[str, dict[str, list[Article]]]) -> str:
    today = dt.datetime.now().strftime("%A, %B %d, %Y")
    lines = [
        f"{PODCAST_TITLE} for {today}.",
        "This is a wave-top summary of the major stories in today's newsletters, designed for a commute-length listen.",
        "I will focus on what changed, why it matters, and where to watch for follow-up.",
        "",
    ]

    for newsletter_title, sections in newsletter_sections.items():
        lines.append(
            f"First, {newsletter_title}. I am grouping the coverage by section and keeping each item at the headline-and-context level."
        )
        for section_name, articles in sections.items():
            if not articles:
                continue
            selected = articles[:podcast_article_limit(section_name)]
            lines.append(
                f"In {section_name}, there are {len(selected)} items worth tracking. "
                "The goal here is not to exhaust the details, but to give you enough context to decide what deserves a closer read later."
            )
            for article in selected:
                lines.append(
                    f"{article.title}. {article.summary} "
                    f"This reporting comes from {article.source}. "
                    "The practical takeaway is to note the direction of the story, the institution or market being affected, and whether this looks like a one-day development or something likely to keep moving."
                )
            lines.append(
                f"That is the quick read for {section_name}. The full written newsletter has the links if any of these need a deeper look."
            )
            lines.append("")

    lines.extend(
        [
            "That is the top-level picture for today.",
            "The written newsletters include the full article links for anything you want to read in detail later.",
        ]
    )
    script = "\n".join(lines)
    return trim_to_word_target(script, PODCAST_SCRIPT_WORD_TARGET)


def trim_to_word_target(script: str, target_words: int) -> str:
    words = script.split()
    if len(words) <= target_words:
        return script
    trimmed = " ".join(words[:target_words])
    return trimmed.rstrip(" ,;:") + "."


def split_script(script: str, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in script.splitlines() if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
        elif len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return chunks


def synthesize_with_openai(script: str, output_path: Path) -> Path:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    model = os.environ.get("PODCAST_TTS_MODEL", "gpt-4o-mini-tts")
    voice = os.environ.get("PODCAST_TTS_VOICE", "ash")
    instructions = os.environ.get(
        "PODCAST_TTS_INSTRUCTIONS",
        "Speak like a professional public radio news host. Use a natural, calm, realistic delivery with clear pacing for driving.",
    )
    chunk_paths: list[Path] = []
    for index, chunk in enumerate(split_script(script, PODCAST_TTS_CHARS_PER_CHUNK), start=1):
        request = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=json.dumps(
                {
                    "model": model,
                    "voice": voice,
                    "input": chunk,
                    "instructions": instructions,
                    "response_format": "mp3",
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        chunk_path = output_path.with_name(f"{output_path.stem}_part{index:02d}.mp3")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                chunk_path.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI TTS failed: HTTP {exc.code} {detail}") from exc
        chunk_paths.append(chunk_path)

    with output_path.open("wb") as merged:
        for chunk_path in chunk_paths:
            merged.write(chunk_path.read_bytes())
    for chunk_path in chunk_paths:
        chunk_path.unlink(missing_ok=True)
    return output_path


def synthesize_with_windows_sapi(script: str, output_path: Path) -> Path:
    wav_path = output_path.with_suffix(".wav")
    script_input_path = output_path.with_suffix(".sapi.txt")
    script_input_path.write_text(script, encoding="utf-8")
    command = (
        "Add-Type -AssemblyName System.Speech; "
        f"$text = Get-Content -LiteralPath '{script_input_path}' -Raw; "
        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$synth.Rate = -1; "
        f"$synth.SetOutputToWaveFile('{wav_path}'); "
        "$synth.Speak($text); "
        "$synth.Dispose();"
    )
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        check=True,
        timeout=180,
    )
    script_input_path.unlink(missing_ok=True)
    return wav_path


def synthesize_podcast(script: str, title: str) -> Path:
    PODCAST_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d")
    output_path = PODCAST_DIR / f"{slugify(title)}-{stamp}.mp3"
    if os.environ.get("OPENAI_API_KEY", "").strip():
        return synthesize_with_openai(script, output_path)
    return synthesize_with_windows_sapi(script, output_path)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "podcast"


def build_podcast() -> tuple[str, Path, dict[str, dict[str, list[Article]]]]:
    newsletter_sections: dict[str, dict[str, list[Article]]] = {}
    for name in selected_podcast_newsletters():
        config = NEWSLETTERS[name]
        _, _, sections = build_newsletter(config)
        newsletter_sections[config["title"]] = sections
    script = podcast_script_from_sections(newsletter_sections)
    audio_path = synthesize_podcast(script, PODCAST_TITLE)
    script_path = audio_path.with_suffix(".txt")
    script_path.write_text(script, encoding="utf-8")
    return script, audio_path, newsletter_sections


def send_podcast_email(script: str, audio_path: Path) -> None:
    recipient = os.environ.get("PODCAST_RECIPIENT", PODCAST_RECIPIENT)
    today = dt.datetime.now().strftime("%B %d, %Y")
    subject = f"{PODCAST_TITLE} - {today}"
    text_body = (
        f"Attached is today's podcast-style audio summary.\n\n"
        f"Audio file: {audio_path.name}\n\n"
        f"Script preview:\n{textwrap.shorten(script, width=1200, placeholder='...')}"
    )
    html_body = (
        "<p>Attached is today's podcast-style audio summary.</p>"
        f"<p><strong>Audio file:</strong> {html_escape(audio_path.name)}</p>"
        f"<p>{html_escape(textwrap.shorten(script, width=1200, placeholder='...'))}</p>"
    )
    send_email(subject, html_body, text_body, recipient, [audio_path])


def log(message: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with (LOG_DIR / "newsletter.log").open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def safe_print(value: str = "") -> None:
    try:
        print(value)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.write(value.encode(encoding, errors="replace").decode(encoding, errors="replace"))
        sys.stdout.write("\n")


def already_sent_today(title: str) -> bool:
    log_path = LOG_DIR / "newsletter.log"
    if not log_path.exists():
        return False
    today = dt.datetime.now().strftime("%Y-%m-%d")
    marker = f"Sent {title} "
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith(f"[{today} ") and marker in line:
            return True
    return False


def before_local_time(value: str) -> bool:
    try:
        hour_text, minute_text = value.split(":", 1)
        not_before = dt.time(hour=int(hour_text), minute=int(minute_text))
    except ValueError as exc:
        raise ValueError("--not-before must use HH:MM format") from exc
    return dt.datetime.now().time() < not_before


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and send the configured daily newsletters.")
    parser.add_argument(
        "--newsletter",
        choices=["all", *NEWSLETTERS.keys()],
        default="all",
        help="Choose which newsletter to run. Defaults to all.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build the newsletter and print a text preview without sending.")
    parser.add_argument("--save-html", action="store_true", help="Save the generated HTML preview files.")
    parser.add_argument(
        "--once-per-day",
        action="store_true",
        help="Skip sending a newsletter if it already succeeded today. Intended for scheduled runs.",
    )
    parser.add_argument(
        "--not-before",
        help="Skip sending until this local HH:MM time. Intended for logon catch-up runs.",
    )
    parser.add_argument("--with-podcast", action="store_true", help="Also generate and send the podcast email.")
    parser.add_argument("--podcast-only", action="store_true", help="Only generate and send the podcast email.")
    args = parser.parse_args()

    load_env()
    try:
        if args.not_before and before_local_time(args.not_before):
            log(f"Skipped run; current time is before {args.not_before}.")
            return 0

        send_podcast = args.with_podcast or os.environ.get("SEND_PODCAST", "").lower() in {"1", "true", "yes"}
        selected_names = [] if args.podcast_only else list(NEWSLETTERS) if args.newsletter == "all" else [args.newsletter]
        failures: list[str] = []

        for name in selected_names:
            config = NEWSLETTERS[name]
            title = config["title"]
            try:
                if args.once_per_day and not args.dry_run and already_sent_today(title):
                    log(f"Skipped {title}; already sent today.")
                    continue

                html_body, text_body, sections = build_newsletter(config)
                total = sum(len(items) for items in sections.values())
                subject = f"{title} - {dt.datetime.now().strftime('%B %d, %Y')}"
                preview_path = BASE_DIR / config["preview_file"]
                recipient = os.environ.get(config["recipient_env"], config["default_recipient"])

                if args.save_html or args.dry_run:
                    preview_path.write_text(html_body, encoding="utf-8")

                if args.dry_run:
                    safe_print(text_body)
                    safe_print(f"\nPreview saved to {preview_path}")
                    safe_print()
                    log(f"Dry run completed for {title} with {total} articles.")
                    continue

                send_email(subject, html_body, text_body, recipient)
                log(f"Sent {title} to {recipient} with {total} articles.")
            except Exception as exc:
                failures.append(f"{title}: {exc}")
                log(f"ERROR sending {title}: {exc}")

        if args.podcast_only or send_podcast:
            try:
                if args.once_per_day and not args.dry_run and already_sent_today(PODCAST_TITLE):
                    log(f"Skipped {PODCAST_TITLE}; already sent today.")
                else:
                    if not args.dry_run and not os.environ.get("OPENAI_API_KEY", "").strip():
                        raise RuntimeError("OPENAI_API_KEY is required to send realistic podcast audio.")
                    script, audio_path, newsletter_sections = build_podcast()
                    total = sum(
                        len(articles)
                        for sections in newsletter_sections.values()
                        for articles in sections.values()
                    )
                    if args.dry_run:
                        safe_print(script)
                        safe_print(f"\nPodcast audio saved to {audio_path}")
                        log(f"Dry run completed for {PODCAST_TITLE} with {total} source articles.")
                    else:
                        send_podcast_email(script, audio_path)
                        recipient = os.environ.get("PODCAST_RECIPIENT", PODCAST_RECIPIENT)
                        log(f"Sent {PODCAST_TITLE} to {recipient} with {total} source articles.")
            except Exception as exc:
                failures.append(f"{PODCAST_TITLE}: {exc}")
                log(f"ERROR sending {PODCAST_TITLE}: {exc}")

        if failures:
            raise RuntimeError("; ".join(failures))
        return 0
    except Exception as exc:
        log(f"ERROR: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

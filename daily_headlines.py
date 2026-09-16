import argparse
import datetime as dt
import email.utils
import html
import json
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
GENERAL_RECIPIENT = "james.schliesske@gmail.com"
DEFENSE_RECIPIENT = "James.d.schliesske.civ@army.mil"
DEFAULT_MAX_ARTICLE_AGE_DAYS = 3


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


DEFENSE_CORE_FEEDS = [
    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
    ("Military Times", "https://www.militarytimes.com/arc/outboundfeeds/rss/"),
    ("Stars and Stripes", "https://subscribe.stripes.com/rss/top-news.xml"),
    ("TWZ", "https://www.twz.com/feed"),
    ("Breaking Defense", "https://breakingdefense.com/feed/"),
    ("Defense One", "https://www.defenseone.com/rss/all/"),
    ("RealClearDefense", "https://www.realcleardefense.com/index.xml"),
    ("War on the Rocks", "https://warontherocks.com/feed/"),
    ("DefenseScoop", "https://defensescoop.com/feed/"),
]

DEFENSE_ACQUISITION_FEEDS = [
    ("GovCon Wire", "https://www.govconwire.com/feed/"),
    ("ExecutiveGov", "https://executivegov.com/feed/"),
    ("DefenseScoop", "https://defensescoop.com/feed/"),
    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
    ("Breaking Defense", "https://breakingdefense.com/feed/"),
    ("Defense One", "https://www.defenseone.com/rss/all/"),
]

DEFENSE_CYBER_FEEDS = [
    ("CyberScoop", "https://cyberscoop.com/feed/"),
    ("The Record", "https://therecord.media/feed"),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("Dark Reading", "https://www.darkreading.com/rss.xml"),
    ("DefenseScoop", "https://defensescoop.com/feed/"),
    ("FedScoop", "https://fedscoop.com/feed/"),
    ("Defense One", "https://www.defenseone.com/rss/all/"),
    ("C4ISRNET", "https://www.c4isrnet.com/arc/outboundfeeds/rss/"),
]

DEFENSE_FMS_FEEDS = [
    ("DSCA Major Arms Sales", "https://www.dsca.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=700&Site=1509&isdashboardselected=0&max=10"),
    ("DSCA Press", "https://www.dsca.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&SelectFeaturedContent=1&Site=1509&dashboardmoduleid=63543&formatxml=0&max=8"),
    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
    ("Breaking Defense", "https://breakingdefense.com/feed/"),
    ("Defense One", "https://www.defenseone.com/rss/all/"),
    ("GovCon Wire", "https://www.govconwire.com/feed/"),
    ("ExecutiveGov", "https://executivegov.com/feed/"),
]


DEFENSE_SECTIONS = {
    "Army": [
        ("Army Times", "https://www.armytimes.com/arc/outboundfeeds/rss/"),
        ("DVIDS Army", "https://www.dvidshub.net/rss/news?branch=Army"),
        ("Army Technology", "https://www.army-technology.com/feed/"),
        *DEFENSE_CORE_FEEDS,
    ],
    "Marines": [
        ("Marine Corps Times", "https://www.marinecorpstimes.com/arc/outboundfeeds/rss/"),
        ("Marines", "https://www.marines.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=481&max=10"),
        ("DVIDS Marines", "https://www.dvidshub.net/rss/news?branch=Marines"),
        *DEFENSE_CORE_FEEDS,
    ],
    "Air Force": [
        ("Air Force Times", "https://www.airforcetimes.com/arc/outboundfeeds/rss/"),
        ("Air & Space Forces Magazine", "https://www.airandspaceforces.com/feed/"),
        ("Air Force", "https://www.af.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=1&Category=755&max=10"),
        ("DVIDS Air Force", "https://www.dvidshub.net/rss/news?branch=Air%20Force"),
        ("Airforce Technology", "https://www.airforce-technology.com/feed/"),
        *DEFENSE_CORE_FEEDS,
    ],
    "Navy": [
        ("Navy Times", "https://www.navytimes.com/arc/outboundfeeds/rss/"),
        ("USNI News", "https://news.usni.org/feed"),
        ("DVIDS Navy", "https://www.dvidshub.net/rss/news?branch=Navy"),
        ("Naval Technology", "https://www.naval-technology.com/feed/"),
        ("Naval News", "https://www.navalnews.com/feed/"),
        *DEFENSE_CORE_FEEDS,
    ],
    "C4ISR": [
        ("DARPA", "https://www.darpa.mil/rss.xml"),
        ("C4ISRNET", "https://www.c4isrnet.com/arc/outboundfeeds/rss/"),
        ("Air & Space Forces Magazine", "https://www.airandspaceforces.com/feed/"),
        ("Airforce Technology", "https://www.airforce-technology.com/feed/"),
        *DEFENSE_CORE_FEEDS,
        *DEFENSE_ACQUISITION_FEEDS,
    ],
    "Cyber Security": [
        *DEFENSE_CYBER_FEEDS,
        *DEFENSE_CORE_FEEDS,
    ],
    "Foreign Military Sales": [
        *DEFENSE_FMS_FEEDS,
        *DEFENSE_CORE_FEEDS,
    ],
    "Defense Acquisition": [
        *DEFENSE_ACQUISITION_FEEDS,
        ("DARPA", "https://www.darpa.mil/rss.xml"),
        ("C4ISRNET", "https://www.c4isrnet.com/arc/outboundfeeds/rss/"),
        ("Army Technology", "https://www.army-technology.com/feed/"),
        ("Naval Technology", "https://www.naval-technology.com/feed/"),
        ("Airforce Technology", "https://www.airforce-technology.com/feed/"),
        *DEFENSE_CORE_FEEDS,
    ],
    "Field Artillery": [
        ("Army Times", "https://www.armytimes.com/arc/outboundfeeds/rss/"),
        ("DVIDS Army", "https://www.dvidshub.net/rss/news?branch=Army"),
        ("Military Times", "https://www.militarytimes.com/arc/outboundfeeds/rss/"),
        ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
        ("Breaking Defense", "https://breakingdefense.com/feed/"),
        ("TWZ", "https://www.twz.com/feed"),
        ("Defense One", "https://www.defenseone.com/rss/all/"),
        ("Defence Blog", "https://defence-blog.com/feed/"),
        ("Army Technology", "https://www.army-technology.com/feed/"),
        ("DefenseScoop", "https://defensescoop.com/feed/"),
    ],
}


DEFENSE_SECTION_KEYWORDS = {
    "Army": [
        "army",
        "soldier",
        "soldiers",
        "brigade",
        "division",
        "corps",
        "fort ",
        "land forces",
        "ground combat",
        "armored",
        "infantry",
        "stryker",
        "abrams",
        "bradley",
    ],
    "Marines": [
        "marine corps",
        "marines",
        "usmc",
        "littoral regiment",
        "amphibious",
        "expeditionary",
        "marine expeditionary force",
        "mef",
        "maw",
        "mcas",
        "vmfa",
        "camp foster",
        "camp pendleton",
        "camp lejeune",
        "quantico",
    ],
    "Air Force": [
        "air force",
        "airman",
        "airmen",
        "usaf",
        "fighter",
        "bomber",
        "aircraft",
        "air wing",
        "air base",
        "f-35",
        "f-22",
        "f-15",
        "f-16",
        "b-21",
        "b-52",
        "kc-46",
        "c-130",
        "drone",
        "uav",
    ],
    "Navy": [
        "navy",
        "naval",
        "sailor",
        "sailors",
        "fleet",
        "ship",
        "ships",
        "submarine",
        "submarines",
        "destroyer",
        "frigate",
        "aircraft carrier",
        "carrier strike group",
        "amphibious ready group",
        "usni",
        "marine vessel",
    ],
    "C4ISR": [
        "c4isr",
        "command and control",
        "command, control",
        "jadc2",
        "cjadc2",
        "sensor",
        "sensors",
        "electronic warfare",
        "electromagnetic spectrum",
        "cyber",
        "satellite",
        "space force",
        "isr",
        "surveillance",
        "reconnaissance",
        "network",
        "networks",
        "communications",
        "data link",
        "radar",
    ],
    "Cyber Security": [
        "cyber",
        "cybersecurity",
        "cyber security",
        "cyberattack",
        "cyber attack",
        "cyber threat",
        "malware",
        "ransomware",
        "breach",
        "hack",
        "hacker",
        "zero trust",
        "network security",
        "critical infrastructure",
        "vulnerability",
        "cisa",
        "nsa",
    ],
    "Foreign Military Sales": [
        "foreign military sales",
        "fms",
        "major arms sale",
        "major arms sales",
        "arms sale",
        "arms sales",
        "arms transfer",
        "weapons sale",
        "missile sale",
        "military sale",
        "security cooperation",
        "security assistance",
        "congressional notification",
        "foreign military financing",
        "military aid",
        "export approval",
        "approved sale",
        "support package",
        "sale to",
        "sales to",
        "fms contract",
        "fms contract modification",
    ],
    "Defense Acquisition": [
        "acquisition",
        "procurement",
        "contract",
        "contracts",
        "contractor",
        "award",
        "awarded",
        "solicitation",
        "request for proposals",
        "rfp",
        "program office",
        "program executive office",
        "production",
        "supplier",
        "supply chain",
        "industrial base",
        "appropriation",
        "prototype",
        "vendor",
        "technology demonstrator",
    ],
    "Field Artillery": [
        "field artillery",
        "artillery",
        "howitzer",
        "howitzers",
        "cannon",
        "tube artillery",
        "long-range fires",
        "long range fires",
        "precision fires",
        "mlrs",
        "himars",
        "m270",
        "prsm",
        "precision strike missile",
        "paladin",
        "m109",
        "155mm",
        "105mm",
        "rocket artillery",
        "counterfire",
        "mortar",
        "mortars",
        "shell",
        "shells",
        "projectile",
        "projectiles",
        "fire support",
        "surface-to-surface",
    ],
}

DEFENSE_SECTION_EXCLUDE_KEYWORDS = {
    "Army": [
        "marine corps",
        "marines",
        "navy",
        "naval",
        "submarine",
        "sailor",
        "air force",
        "airman",
        "field artillery",
        "howitzer",
        "himars",
        "precision strike missile",
        "prsm",
    ],
    "Marines": [
        "merchant marine",
        "marine vessel",
        "submarine",
    ],
    "Air Force": [
        "navy",
        "naval",
        "submarine",
        "sailor",
        "marine corps",
        "marines",
        "field artillery",
        "howitzer",
    ],
    "Navy": [
        "army",
        "soldier",
        "air force",
        "airman",
        "field artillery",
        "howitzer",
    ],
    "C4ISR": [
        "artillery",
        "howitzer",
        "himars",
        "mortar",
    ],
    "Cyber Security": [
        "artillery",
        "howitzer",
        "shipbuilding",
        "aircraft maintenance",
    ],
    "Foreign Military Sales": [
        "cyberattack",
        "cyber attack",
        "ransomware",
        "data breach",
        "intern",
        "internship",
        "recruitment",
        "pathways",
    ],
    "Defense Acquisition": [
        "foreign military sales",
        "major arms sale",
        "major arms sales",
        "congressional notification",
        "cyberattack",
        "ransomware",
        "field artillery",
        "howitzer",
        "precision strike missile",
        "prsm",
    ],
    "Field Artillery": [
        "submarine",
        "submarines",
        "naval",
        "navy",
        "ship",
        "ships",
        "destroyer",
        "frigate",
        "battleship",
        "aircraft carrier",
        "carrier strike group",
        "fighter jet",
        "bomber",
        "drone boat",
        "unmanned vessel",
        "cyber",
        "satellite",
        "space force",
        "radar",
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
        "section_exclude_keywords": DEFENSE_SECTION_EXCLUDE_KEYWORDS,
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


@dataclass(frozen=True)
class HistoryEvent:
    year: int
    text: str
    link: str


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


def article_key(article: Article) -> tuple[str, str]:
    link = article.link.lower().strip()
    link = re.sub(r"#.*$", "", link)
    link = re.sub(r"\?.*$", "", link)
    link = link.rstrip("/")
    title = re.sub(r"\W+", "", article.title).lower()
    return link, title


def title_tokens(title: str) -> set[str]:
    stop_words = {
        "about",
        "after",
        "amid",
        "and",
        "are",
        "for",
        "from",
        "has",
        "have",
        "how",
        "into",
        "its",
        "new",
        "says",
        "that",
        "the",
        "this",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", title.lower())
        if len(token) >= 3 and token not in stop_words
    }


def is_similar_title(tokens: set[str], previous_tokens: list[set[str]]) -> bool:
    if len(tokens) < 4:
        return False
    for previous in previous_tokens:
        overlap = len(tokens & previous)
        smaller = min(len(tokens), len(previous))
        if smaller >= 4 and overlap / smaller >= 0.6:
            return True
    return False


def keyword_in_text(keyword: str, text: str) -> bool:
    escaped = re.escape(keyword.lower()).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None


def matches_keywords(article: Article, keywords: list[str] | None) -> bool:
    if not keywords:
        return True
    haystack = f"{article.title} {article.summary}".lower()
    return any(keyword_in_text(keyword, haystack) for keyword in keywords)


def matches_section_rules(
    article: Article,
    keywords: list[str] | None,
    excluded_keywords: list[str] | None = None,
) -> bool:
    haystack = f"{article.title} {article.summary}".lower()
    if excluded_keywords and any(keyword_in_text(keyword, haystack) for keyword in excluded_keywords):
        return False
    return matches_keywords(article, keywords)


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


def fetch_feed(source: str, url: str, user_agent: str, max_items: int = 15) -> list[Article]:
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
    excluded_keywords: list[str] | None = None,
    target_count: int = 8,
    newsletter_seen_links: set[str] | None = None,
    newsletter_seen_titles: set[str] | None = None,
    newsletter_seen_title_tokens: list[set[str]] | None = None,
    feed_cache: dict[tuple[str, str], list[Article]] | None = None,
) -> list[Article]:
    articles_by_source: list[list[Article]] = []
    seen_links: set[str] = set()
    seen_titles: set[str] = set()
    seen_title_tokens: list[set[str]] = []
    recent_age = max_article_age()

    for source, url in feed_specs:
        source_articles: list[Article] = []
        feed_key = (source, url)
        if feed_cache is not None and feed_key in feed_cache:
            fetched_articles = feed_cache[feed_key]
        else:
            fetched_articles = fetch_feed(source, url, user_agent)
            if feed_cache is not None:
                feed_cache[feed_key] = fetched_articles
            time.sleep(0.4)

        for article in fetched_articles:
            link_key, title_key = article_key(article)
            tokens = title_tokens(article.title)
            if (
                link_key in seen_links
                or title_key in seen_titles
                or is_similar_title(tokens, seen_title_tokens)
                or (newsletter_seen_links is not None and link_key in newsletter_seen_links)
                or (newsletter_seen_titles is not None and title_key in newsletter_seen_titles)
                or (
                    newsletter_seen_title_tokens is not None
                    and is_similar_title(tokens, newsletter_seen_title_tokens)
                )
                or is_obviously_stale(article)
                or not is_recent(article, recent_age)
                or not is_probably_english(article)
                or not matches_section_rules(article, keywords, excluded_keywords)
            ):
                continue
            seen_links.add(link_key)
            seen_titles.add(title_key)
            seen_title_tokens.append(tokens)
            source_articles.append(article)
        source_articles.sort(key=lambda item: item.published, reverse=True)
        if source_articles:
            articles_by_source.append(source_articles)

    selected: list[Article] = []
    index = 0
    while len(selected) < target_count:
        added = False
        for source_articles in articles_by_source:
            if index < len(source_articles):
                article = source_articles[index]
                link_key, title_key = article_key(article)
                selected.append(article)
                if newsletter_seen_links is not None:
                    newsletter_seen_links.add(link_key)
                if newsletter_seen_titles is not None:
                    newsletter_seen_titles.add(title_key)
                if newsletter_seen_title_tokens is not None:
                    newsletter_seen_title_tokens.append(title_tokens(article.title))
                added = True
                if len(selected) == target_count:
                    break
        if not added:
            break
        index += 1
    return selected


def fetch_this_day_in_history(issue_date: dt.date, user_agent: str) -> HistoryEvent | None:
    url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/selected/{issue_date:%m}/{issue_date:%d}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        log(f"This day in history failed: {url} ({exc})")
        return None

    events = payload.get("selected", [])
    candidates: list[HistoryEvent] = []
    for event in events:
        text = clean_text(event.get("text", ""))
        year = event.get("year")
        if not text or not isinstance(year, int):
            continue
        pages = event.get("pages") or []
        link = ""
        if pages:
            content_urls = pages[0].get("content_urls", {})
            desktop_urls = content_urls.get("desktop", {})
            link = desktop_urls.get("page", "")
        candidates.append(HistoryEvent(year=year, text=text, link=link))

    if not candidates:
        return None

    def event_score(event: HistoryEvent) -> tuple[int, int, int]:
        has_link = 1 if event.link else 0
        modern_weight = 1 if event.year >= 1500 else 0
        return has_link, modern_weight, len(event.text)

    return max(candidates, key=event_score)


def html_escape(value: str) -> str:
    return html.escape(value, quote=True)


def display_date(issue_date: dt.date) -> str:
    if os.name == "nt":
        return issue_date.strftime("%A, %B %#d, %Y")
    return issue_date.strftime("%A, %B %-d, %Y")


def build_html(title: str, sections: dict[str, list[Article]], history_event: HistoryEvent | None, issue_date: dt.date) -> str:
    today = display_date(issue_date)
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

    parts.append("<h2 style=\"border-bottom:2px solid #d1d5db;padding-bottom:8px;margin:28px 0 14px;color:#111827;\">This Day in History</h2>")
    if history_event:
        link_html = (
            f" <a href=\"{html_escape(history_event.link)}\" style=\"color:#2563eb;\">Read more</a>"
            if history_event.link
            else ""
        )
        parts.extend(
            [
                "<div style=\"background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:0 0 14px;\">",
                f"<h3 style=\"font-size:18px;line-height:1.35;margin:0 0 8px;\">{history_event.year}</h3>",
                f"<p style=\"font-size:14px;line-height:1.55;margin:0;\">{html_escape(history_event.text)}{link_html}</p>",
                "</div>",
            ]
        )
    else:
        parts.append("<p>No history item was available this morning.</p>")

    parts.extend(
        [
            "<p style=\"font-size:12px;color:#6b7280;margin-top:28px;\">Generated automatically from RSS feeds. Some linked articles may require a subscription.</p>",
            "</div>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(parts)


def build_text(title: str, sections: dict[str, list[Article]], history_event: HistoryEvent | None, issue_date: dt.date) -> str:
    today = issue_date.strftime("%A, %B %d, %Y")
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

    lines.extend(["This Day in History", "-------------------"])
    if history_event:
        lines.extend(
            [
                f"{history_event.year}: {history_event.text}",
                f"Link: {history_event.link}" if history_event.link else "",
                "",
            ]
        )
    else:
        lines.extend(["No history item was available this morning.", ""])
    return "\n".join(lines)


def build_newsletter(config: dict) -> tuple[str, str, dict[str, list[Article]]]:
    user_agent = config["user_agent"]
    section_keywords = config.get("section_keywords", {})
    section_exclude_keywords = config.get("section_exclude_keywords", {})
    newsletter_seen_links: set[str] = set()
    newsletter_seen_titles: set[str] = set()
    newsletter_seen_title_tokens: list[set[str]] = []
    feed_cache: dict[tuple[str, str], list[Article]] = {}
    sections: dict[str, list[Article]] = {}
    for section, feeds in config["sections"].items():
        sections[section] = collect_section(
            feeds,
            user_agent,
            section_keywords.get(section),
            section_exclude_keywords.get(section),
            newsletter_seen_links=newsletter_seen_links,
            newsletter_seen_titles=newsletter_seen_titles,
            newsletter_seen_title_tokens=newsletter_seen_title_tokens,
            feed_cache=feed_cache,
        )
    title = config["title"]
    issue_date = dt.datetime.now().date()
    history_event = fetch_this_day_in_history(issue_date, user_agent)
    return build_html(title, sections, history_event, issue_date), build_text(title, sections, history_event, issue_date), sections


def send_email(subject: str, html_body: str, text_body: str, recipient: str) -> None:
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

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(sender, password)
        server.send_message(message)


def log(message: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with (LOG_DIR / "newsletter.log").open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def safe_print(value: str = "") -> None:
    print(value.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8"))


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
    args = parser.parse_args()

    load_env()
    try:
        if args.not_before and before_local_time(args.not_before):
            log(f"Skipped run; current time is before {args.not_before}.")
            return 0

        selected_names = list(NEWSLETTERS) if args.newsletter == "all" else [args.newsletter]
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

        if failures:
            raise RuntimeError("; ".join(failures))
        return 0
    except Exception as exc:
        log(f"ERROR: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

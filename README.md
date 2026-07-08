# Daily Headlines Newsletter

This folder contains a small daily newsletter job that collects headlines from RSS feeds, summarizes each item from the feed description, and emails the digest to `james.schliesske@gmail.com`.

## Sections

- Top News: CNN, NBC News, BBC News, WSJ, NPR, Reuters
- World News: BBC World, CNN World, NBC World, WSJ World, NPR World, Al Jazeera
- Technology News: TechCrunch, The Verge, Ars Technica, Wired, MIT Technology Review, Engadget

Each section includes up to 8 articles with a title, 2-3 sentence summary, source, and full article link.

## Run a Preview

```powershell
python .\daily_headlines.py --dry-run
```

The preview writes `latest_newsletter.html` and prints a plain-text version in the terminal.

## Send Now

```powershell
.\run_newsletter.ps1
```

## Schedule for 4 AM Daily

```powershell
.\register_daily_task.ps1
```

The task is registered as `Daily Headlines Newsletter` in Windows Task Scheduler.

## Configuration

Email configuration lives in `.env`. The file is intentionally ignored by Git because it contains the Gmail app password.

# Defense Daily Newsletter

This branch contains a defense-focused daily newsletter job that collects headlines from RSS feeds, summarizes each item from the feed description, and emails the digest to `James.d.schliesske.civ@army.mil`.

## Sections

- Defense Headlines: Defense News, TWZ, Breaking Defense, Defense One, Military Times, USNI News
- Military Services: Army Times, Air Force Times, Marine Corps Times, Navy Times, USNI News, Air & Space Forces Magazine
- Defense Technology & Industry: C4ISRNET, Breaking Defense, Defense News, TWZ, Naval News, Air & Space Forces Magazine

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

The task is registered as `Defense Daily Newsletter` in Windows Task Scheduler.

## Configuration

Email configuration lives in `.env`. The file is intentionally ignored by Git because it contains the Gmail app password.

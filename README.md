# Daily Newsletters

This branch contains a daily newsletter job that sends two separate digests when it runs:

- `Daily Headlines` goes to `james.schliesske@gmail.com`
- `Defense Daily` goes to `James.d.schliesske.civ@army.mil`

Both newsletters collect RSS headlines, summarize each item from the feed description, and include the source and full article link.

## Sections

General newsletter:

- Top News: CNN, NBC News, BBC News, WSJ, NPR
- World News: BBC World, CNN World, NBC World, WSJ World, NPR World, Al Jazeera
- Technology News: TechCrunch, The Verge, Ars Technica, Wired, MIT Technology Review, Engadget

Defense newsletter:

- Defense Headlines: Defense News, TWZ, Breaking Defense, Defense One, Military Times, USNI News
- Military Services: Army Times, Air Force Times, Marine Corps Times, Navy Times, USNI News, Air & Space Forces Magazine
- Defense Technology & Industry: C4ISRNET, Breaking Defense, Defense News, TWZ, Naval News, Air & Space Forces Magazine

Each section includes up to 8 articles with a title, 2-3 sentence summary, source, and full article link.

## Run a Preview

```powershell
python .\daily_headlines.py --dry-run
```

The preview writes `latest_general_newsletter.html` and `latest_defense_newsletter.html`, then prints plain-text versions in the terminal.

To preview only one newsletter:

```powershell
python .\daily_headlines.py --newsletter general --dry-run
python .\daily_headlines.py --newsletter defense --dry-run
```

## Send Now

```powershell
.\run_newsletter.ps1
```

## Schedule for 4 AM Daily

```powershell
.\register_daily_task.ps1
```

The task is registered as `Daily Newsletters` in Windows Task Scheduler.

## Configuration

Email configuration lives in `.env`. The file is intentionally ignored by Git because it contains the Gmail app password. Use `GENERAL_NEWSLETTER_RECIPIENT` and `DEFENSE_NEWSLETTER_RECIPIENT` to change destinations.

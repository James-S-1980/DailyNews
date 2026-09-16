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

- Army: Army Times, DVIDS Army, Army Technology, and broad defense feeds
- Marines: Marine Corps Times, Marines.mil, DVIDS Marines, and broad defense feeds
- Air Force: Air Force Times, Air & Space Forces Magazine, Air Force, DVIDS Air Force, Airforce Technology, and broad defense feeds
- Navy: Navy Times, USNI News, DVIDS Navy, Naval Technology, Naval News, and broad defense feeds
- C4ISR: DARPA, C4ISRNET, Air & Space Forces Magazine, Airforce Technology, broad defense feeds, and acquisition feeds
- Cyber Security: CyberScoop, The Record, BleepingComputer, Dark Reading, DefenseScoop, FedScoop, Defense One, C4ISRNET, and broad defense feeds
- Foreign Military Sales: DSCA Major Arms Sales, DSCA Press, Defense News, Breaking Defense, Defense One, GovCon Wire, ExecutiveGov, and broad defense feeds
- Defense Acquisition: GovCon Wire, ExecutiveGov, DefenseScoop, FedScoop, DARPA, C4ISRNET, service technology feeds, and broad defense feeds
- Field Artillery: Army Times, DVIDS Army, Military Times, Defense News, Breaking Defense, TWZ, Defense One, Defence Blog, Army Technology, DefenseScoop

Each section includes up to 8 articles with a title, 2-3 sentence summary, source, and full article link. Defense newsletter sections use keyword and exclusion filters to keep broad feeds focused on the requested categories. Each newsletter closes with a "This Day in History" item for the issue date.

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

Scheduled runs use `--once-per-day`, so the 4 AM task and logon catch-up will not send duplicate newsletters on the same date. The logon catch-up also uses `--not-before 04:00`, so logging in before 4 AM does not send early.

## Configuration

Email configuration lives in `.env`. The file is intentionally ignored by Git because it contains the Gmail app password. Use `GENERAL_NEWSLETTER_RECIPIENT` and `DEFENSE_NEWSLETTER_RECIPIENT` to change destinations.

By default, articles older than 3 days are excluded. Set `MAX_ARTICLE_AGE_DAYS` in `.env` to adjust the recency window.

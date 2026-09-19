# Daily Newsletters

This app sends two daily newsletter digests:

- `Daily Headlines` goes to `james.schliesske@gmail.com`
- `Defense Daily` goes to `James.d.schliesske.civ@army.mil`

The app now runs as a Docker container. The container exposes a health/status endpoint on port `8774` and runs the newsletter job daily at 4:00 AM Eastern time.

Both newsletters collect RSS headlines, summarize each item from the feed description, and include the source and full article link.

## Sections

General newsletter:

- Top News: CNN, NBC News, BBC News, WSJ, NPR
- World News: BBC World, CNN World, NBC World, WSJ World, NPR World, Al Jazeera
- Technology News: TechCrunch, The Verge, Ars Technica, Wired, MIT Technology Review, Engadget

Defense newsletter:

- Army Aviation: Army Aviation Magazine, Army Times, DVIDS Army, Defense News Air, Vertical Mag, Rotor & Wing, Aviation Week, Army Technology, and broad defense aviation feeds
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

## Configuration

Email configuration lives in `.env`. The file is intentionally ignored by Git because it contains the Gmail app password. `docker-compose.yml` loads this file into the container.

Required values:

```env
GENERAL_NEWSLETTER_RECIPIENT=james.schliesske@gmail.com
DEFENSE_NEWSLETTER_RECIPIENT=James.d.schliesske.civ@army.mil
SMTP_USERNAME=james.schliesske@gmail.com
SMTP_APP_PASSWORD=your-app-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
```

Optional values:

```env
MAX_ARTICLE_AGE_DAYS=3
NEWSLETTER_RUN_AT=04:00
```

By default, articles older than 3 days are excluded. The Army Aviation section uses a 7-day recency window because fresh, narrowly Army aviation-specific RSS items are less frequent than broader defense news.

## Run The Container

Build and start the container:

```powershell
docker compose up -d --build
```

Check status:

```powershell
curl http://localhost:8774/health
```

View logs:

```powershell
docker compose logs -f daily-newsletter
```

Stop the container:

```powershell
docker compose down
```

## Manual Runs

Run a dry-run preview inside the container:

```powershell
docker compose run --rm daily-newsletter python daily_headlines.py --dry-run
```

Send both newsletters immediately:

```powershell
docker compose run --rm daily-newsletter python daily_headlines.py
```

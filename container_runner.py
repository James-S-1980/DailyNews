import datetime as dt
import http.server
import os
import subprocess
import threading
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
RUN_AT = os.environ.get("NEWSLETTER_RUN_AT", "04:00")
PORT = int(os.environ.get("PORT", "8774"))
POLL_SECONDS = int(os.environ.get("SCHEDULER_POLL_SECONDS", "60"))

last_run_date: str | None = None
last_result = {
    "status": "starting",
    "last_run": "",
    "last_exit_code": "",
    "last_message": "Container scheduler is starting.",
}


def log(message: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with (LOG_DIR / "container.log").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def parse_run_time(value: str) -> dt.time:
    try:
        hour_text, minute_text = value.split(":", 1)
        return dt.time(hour=int(hour_text), minute=int(minute_text))
    except ValueError as exc:
        raise ValueError("NEWSLETTER_RUN_AT must use HH:MM format") from exc


def run_newsletters() -> None:
    global last_run_date
    today = dt.datetime.now().date().isoformat()
    last_run_date = today
    started = dt.datetime.now().isoformat(timespec="seconds")
    last_result.update(
        {
            "status": "running",
            "last_run": started,
            "last_exit_code": "",
            "last_message": "Newsletter run started.",
        }
    )
    log("Starting scheduled newsletter run.")
    completed = subprocess.run(
        ["python", "daily_headlines.py", "--once-per-day"],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
    )
    output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
    if completed.returncode == 0:
        message = output or "Newsletter run completed successfully."
        status = "ok"
    else:
        message = output or f"Newsletter run failed with exit code {completed.returncode}."
        status = "error"
    last_result.update(
        {
            "status": status,
            "last_exit_code": str(completed.returncode),
            "last_message": message[-1000:],
        }
    )
    log(last_result["last_message"])


def scheduler_loop() -> None:
    run_time = parse_run_time(RUN_AT)
    log(f"Scheduler active. Daily run time: {RUN_AT}.")
    while True:
        now = dt.datetime.now()
        if now.time() >= run_time and last_run_date != now.date().isoformat():
            run_newsletters()
        time.sleep(POLL_SECONDS)


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in {"/", "/health"}:
            self.send_response(404)
            self.end_headers()
            return
        body = (
            "daily-newsletter-container\n"
            f"status={last_result['status']}\n"
            f"run_at={RUN_AT}\n"
            f"last_run={last_result['last_run']}\n"
            f"last_exit_code={last_result['last_exit_code']}\n"
            f"last_message={last_result['last_message']}\n"
        ).encode("utf-8")
        self.send_response(200 if last_result["status"] != "error" else 500)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    threading.Thread(target=scheduler_loop, daemon=True).start()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    log(f"Health server listening on port {PORT}.")
    server.serve_forever()


if __name__ == "__main__":
    main()

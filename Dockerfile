FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8774
ENV NEWSLETTER_RUN_AT=04:00

WORKDIR /app

COPY daily_headlines.py container_runner.py ./

RUN mkdir -p /app/logs

EXPOSE 8774

CMD ["python", "container_runner.py"]

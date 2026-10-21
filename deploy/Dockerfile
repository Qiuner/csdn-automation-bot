FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DISPLAY=:99 HOME=/home/bot
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver xvfb x11vnc novnc websockify tini fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
COPY deploy/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && useradd --create-home --uid 10001 bot
WORKDIR /app
COPY web/*.py /app/web/
COPY tools/*.py /app/tools/
COPY README.md /app/
COPY deploy/entrypoint.sh /usr/local/bin/bot-desktop
RUN printf 'CHROME_BROWSER_PATH = "/usr/bin/chromium"\nCHROME_DRIVER_PATH = "/usr/bin/chromedriver"\n' > /app/web/config.txt \
    && mkdir -p /app/web/Chrome \
    && chown bot:bot /app/web/Chrome \
    && chmod 700 /app/web/Chrome \
    && chmod 755 /usr/local/bin/bot-desktop
USER bot
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/bot-desktop"]

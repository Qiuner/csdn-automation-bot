#!/bin/bash
set -euo pipefail
umask 077
Xvfb :99 -screen 0 1360x900x24 -nolisten tcp &
xvfb_pid=$!
vnc_pid=''
web_pid=''
cleanup() {
    kill "$xvfb_pid" ${vnc_pid:+"$vnc_pid"} ${web_pid:+"$web_pid"} 2>/dev/null || true
    wait || true
}
trap cleanup EXIT
trap 'exit 0' TERM INT
for attempt in {1..50}; do
    [ -S /tmp/.X11-unix/X99 ] && break
    kill -0 "$xvfb_pid"
    sleep 0.1
done
x11vnc -display :99 -forever -shared -nopw -listen 127.0.0.1 -rfbport 5900 &
vnc_pid=$!
websockify --web=/usr/share/novnc 0.0.0.0:6080 127.0.0.1:5900 &
web_pid=$!
# Only the desktop starts. Run an explicit script with docker compose exec.
wait -n "$xvfb_pid" "$vnc_pid" "$web_pid"
exit 1

#!/usr/bin/env python3
"""Sensimune reminder: local notifications on Mon/Wed/Fri before breakfast.

Usage:
  python sensimune_reminder.py run      # start the reminder loop (leave running)
  python sensimune_reminder.py test     # fire a test notification now
  python sensimune_reminder.py taken    # mark today's dose as taken (stops nudges)
  python sensimune_reminder.py status   # show today's schedule/state

Standard library only. Edit config.json to change days/times/phone push.
"""
import json
import platform
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"
STATE = HERE / ".state.json"
CATCH_UP = timedelta(minutes=10)  # still fire a slot if the PC was asleep briefly


def load_config():
    return json.loads(CONFIG.read_text())


def load_state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state):
    STATE.write_text(json.dumps(state))


def today_state(state, today):
    if state.get("date") != today:
        state.clear()
        state.update(date=today, taken=False, fired=[])
    return state


def desktop_notify(title, msg):
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["osascript", "-e",
                            f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                           check=False)
        elif system == "Windows":
            ps = ("[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,"
                  "ContentType=WindowsRuntime] | Out-Null;"
                  "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(1);"
                  f"$x=$t.GetElementsByTagName('text');$x[0].AppendChild($t.CreateTextNode('{title}: {msg}'))|Out-Null;"
                  "$n=[Windows.UI.Notifications.ToastNotification]::new($t);"
                  "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Sensimune').Show($n)")
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)
        else:
            subprocess.run(["notify-send", "-u", "critical", title, msg], check=False)
    except FileNotFoundError:
        print(f"[no desktop notifier available] {title}: {msg}")


def phone_notify(cfg, title, msg):
    topic = cfg.get("ntfy_topic")
    if not topic:
        return
    req = urllib.request.Request(
        f"{cfg.get('ntfy_server', 'https://ntfy.sh')}/{topic}",
        data=msg.encode(), method="POST",
        headers={"Title": title, "Priority": "high", "Tags": "pill"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:  # never crash the loop on network issues
        print(f"[ntfy failed] {e}")


def notify(cfg, title, msg):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {title}: {msg}", flush=True)
    desktop_notify(title, msg)
    phone_notify(cfg, title, msg)


def slots_for(now, cfg):
    """Return [(datetime, message)] for today, or [] if not a dose day."""
    if now.strftime("%a") not in cfg["days"]:
        return []
    out = []
    for s in cfg["slots"]:
        h, m = map(int, s["time"].split(":"))
        out.append((now.replace(hour=h, minute=m, second=0, microsecond=0), s["message"]))
    return out


def run():
    cfg = load_config()
    print("Sensimune reminder running. Ctrl+C to stop.", flush=True)
    while True:
        cfg = load_config()  # pick up edits without restart
        now = datetime.now()
        state = today_state(load_state(), now.strftime("%Y-%m-%d"))
        if not state["taken"]:
            for when, msg in slots_for(now, cfg):
                key = when.strftime("%H:%M")
                if key not in state["fired"] and when <= now < when + CATCH_UP:
                    notify(cfg, "Sensimune", msg)
                    state["fired"].append(key)
        save_state(state)
        time.sleep(20)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    cfg = load_config()
    now = datetime.now()
    if cmd == "run":
        run()
    elif cmd == "test":
        notify(cfg, "Sensimune (test)", "Test notification - reminders are working.")
    elif cmd == "taken":
        state = today_state(load_state(), now.strftime("%Y-%m-%d"))
        state["taken"] = True
        save_state(state)
        print("Marked as taken today. No more nudges.")
    elif cmd == "status":
        state = today_state(load_state(), now.strftime("%Y-%m-%d"))
        slots = slots_for(now, cfg)
        print("Today:", now.strftime("%A"), "- dose day" if slots else "- no dose today")
        for when, _ in slots:
            print("  ", when.strftime("%H:%M"),
                  "fired" if when.strftime("%H:%M") in state["fired"] else "pending")
        print("Taken:", state["taken"])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

# Sensimune reminder

Local reminder (Mon/Wed/Fri) at 07:40, 07:50 and a last call at 08:00.
Run `python3 sensimune_reminder.py taken` after your dose to silence the rest of the day's nudges.

## Setup (on the computer that is on in the morning)
1. `python3 sensimune_reminder.py test` - confirm you see a notification.
2. `python3 sensimune_reminder.py run` - leave it running, or autostart it:
   - Linux/macOS cron: `@reboot cd /path/to/sensimune && nohup python3 sensimune_reminder.py run &`
   - Windows: Task Scheduler -> "At log on" -> `pythonw.exe sensimune_reminder.py run`
3. Phone push (optional): install the free **ntfy** app, subscribe to a long random topic,
   put it in `config.json` as `ntfy_topic`. Treat the topic as a password (it's public otherwise).

Edit `config.json` any time; changes are picked up without restart.

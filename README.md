# redalert 🩸

A small Python CLI that checks the blood-stock levels published by the
Hungarian National Blood Transfusion Service
([OVSZ](https://www.ovsz.hu/veradas)) and sends you a **Telegram** message when
a blood type runs low — nudging you to donate when it matters most.

It is designed to run unattended as a **GitHub Action every day at 04:00 UTC**,
but you can also run it locally at any time.

## How it works

1. Downloads <https://www.ovsz.hu/veradas>.
2. Parses each blood-type block, e.g.:

   ```html
   <div class="ab-p">
       <img name="ab-p" src=".../keszletszint-5.png">
       <b>AB+</b>
       <span id="ab-p-text">5 vagy több napra elegendő</span>
   </div>
   ```

   The `name`/`id` code encodes the blood type — a `0/a/b/ab` group prefix and a
   `p` (pozitív, `+`) or `m` (negatív, `-`) suffix — and the span text begins
   with the number of days the current stock is expected to last.
3. For every watched blood type, if the number of days is **at or below
   `--threshold`** (default `2`), it sends you a Telegram alert in Hungarian
   describing the current level and asking you to donate if you can.

| Blood type | HTML code | Blood type | HTML code |
| ---------- | --------- | ---------- | --------- |
| 0+         | `0-p`     | 0−         | `0-m`     |
| A+         | `a-p`     | A−         | `a-m`     |
| B+         | `b-p`     | B−         | `b-m`     |
| AB+        | `ab-p`    | AB−        | `ab-m`    |

## Usage

```console
$ redalert --help
$ redalert                          # all blood types, threshold = 2
$ redalert --type AB+               # only AB+, threshold = 2
$ redalert --type AB+ --type 0-     # several types (repeat the flag)
$ redalert --threshold 3            # alert at 3 days or fewer
$ redalert --dry-run                # print the message instead of sending it
```

| Flag          | Default                       | Meaning                                                                    |
| ------------- | ----------------------------- | -------------------------------------------------------------------------- |
| `--threshold` | `2`                           | Alert when stock (in days) is **at or below** this value.                  |
| `--type`      | _(all types)_                 | Blood type to watch, e.g. `AB+`. Repeatable. `O` is accepted as an alias for `0`. |
| `--url`       | `https://www.ovsz.hu/veradas` | Page to scrape (mostly for testing).                                       |
| `--dry-run`   | off                           | Print the alert to stdout instead of sending it to Telegram.               |

The Telegram credentials are read from environment variables:

| Variable             | Description                                                        |
| -------------------- | ------------------------------------------------------------------ |
| `TELEGRAM_BOT_TOKEN` | The bot token from [@BotFather](https://t.me/BotFather).           |
| `TELEGRAM_CHAT_ID`   | The chat ID the message is sent to (your own chat, or a group).    |

## Setting it up for yourself

This project uses [uv](https://docs.astral.sh/uv/) for package management.

### 1. Create a Telegram bot

1. Open a chat with [@BotFather](https://t.me/BotFather), send `/newbot`, and
   follow the prompts. Copy the **bot token** it gives you.
2. Send any message to your new bot (this lets it message you back).
3. Find your **chat ID**: open
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser after
   messaging the bot, and read `result[].message.chat.id` from the JSON.

### 2. Run it locally

```bash
# clone your fork, then from the repo root:
uv sync                       # create .venv and install dependencies

export TELEGRAM_BOT_TOKEN="123456:ABC-..."
export TELEGRAM_CHAT_ID="987654321"

uv run redalert --dry-run     # verify parsing without sending anything
uv run redalert --type AB+    # send a real alert if AB+ is low
```

To develop on it, install the dev tools and run the checks:

```bash
uv sync --extra dev
uv run black src              # format
uv run ty check src           # type-check
```

### 3. Run it daily on GitHub Actions

The workflow in [.github/workflows/redalert.yml](.github/workflows/redalert.yml)
already runs every day at 04:00 UTC (and can be triggered manually from the
**Actions** tab via *Run workflow*). To enable it on your fork:

1. Push this repository to GitHub.
2. Go to **Settings → Secrets and variables → Actions → New repository secret**
   and add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Go to the **Actions** tab and enable workflows if prompted.

That's it — you'll get a Telegram message whenever a blood type you care about
drops to the threshold.

> **Note on the schedule:** GitHub cron always runs in **UTC**, and scheduled
> Actions can be delayed (or skipped on inactive repos) during periods of high
> load. For a guaranteed daily run you can trigger it manually, or use the
> *Run workflow* button.

## Exit codes

| Code | Meaning                                                           |
| ---- | ----------------------------------------------------------------- |
| `0`  | Ran successfully (alert sent, or nothing was below the threshold).|
| `1`  | Runtime failure (download failed, no data, Telegram send failed). |
| `2`  | Bad input (unknown blood type, or missing Telegram env vars).     |

## License

Licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE).

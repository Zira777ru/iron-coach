# IronCoach 🏋️

Personal AI fitness trainer and nutritionist Telegram bot.

## Features

- **Workout tracking** — import from Strong app (CSV), manual logging
- **Nutrition logging** — photo recognition, FatSecret screenshot parsing
- **Fitbit sync** — steps, sleep, heart rate, calories, weight
- **AI Coach** — daily motivation, gym warnings, weekly reviews
- **TTS voice messages** — coach can talk to you
- **Smart AI routing** — fast model (Gemini Flash) for vision/quick tasks, smart model (Claude) for deep analysis

## Quick Start

```bash
cp .env.example .env
# Fill in TELEGRAM_TOKEN, OPENROUTER_API_KEY
docker compose up -d
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Registration / onboarding |
| `/profile` | View your profile |
| `/fitbit` | Connect Fitbit account |
| `/fitbit_sync` | Manual Fitbit data sync |
| `/workouts` | Recent workouts |
| `/food` | Log food entry |
| `тренер <question>` | Ask the AI coach anything |

## Architecture

```
bot/          — Telegram handlers (aiogram 3)
integrations/ — Fitbit OAuth, Strong CSV parser
ai/           — OpenRouter client (fast + smart models)
services/     — nutrition analysis, coach logic
tts/          — voice message generation
scheduler/    — daily/weekly automated jobs
db/           — SQLite (WAL mode)
```

## Scheduled Jobs

- **Morning** (`DAILY_CHECK_HOUR`) — motivation + gym warning if missed `NO_GYM_WARN_DAYS`
- **Evening** (`EVENING_CHECK_HOUR`) — daily steps report
- **Sunday 18:00** — weekly review with smart AI analysis

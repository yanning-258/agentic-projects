# Fin-Analytics

A portfolio monitoring tool for people who don't have time to actively track the market. Instead of checking prices, financials, and news for every stock you hold, it surfaces what's actually worth your attention — a daily snapshot per ticker, plus a short combined report on whichever holdings need a closer look that day.

## Problem Statement

Most portfolio tools either dump raw data and expect you to figure out what matters, or assume you're checking in constantly. This is built for the opposite case: a quick daily check-in — what changed, what's worth watching this week — without reading a wall of numbers or a news feed end to end.

The system splits two jobs that are easy to conflate:
- **Surfacing data** — cheap, deterministic fetch of price, fundamentals, and a price chart for every ticker, every day. No judgment involved, just retrieval.
- **Filtering and synthesizing** — an LLM layer that decides which ticker(s), out of the full list, actually deserve a closer look that day, and writes one combined narrative covering them — instead of forcing you to read a full report per ticker regardless of whether anything happened.

## Architecture

**Dashboard layer** (deterministic, no LLM) — `src/tools.py`
- `yfinance_tool` — current price, today's open/high/low/close, market cap, P/E, 52-week range, sector, company name and description
- `financials_tool` — revenue, net income, EPS, debt-to-equity
- `news_tool` — recent headlines, summaries, links
- `chart_tool` — 1-year price history rendered to a base64-encoded chart image

Bundled per ticker and looped across the portfolio by `src/dashboard.py`, served via `GET /dashboard`. Fixed ticker list for now: AAPL, TSM, TSLA, HSBC, GOOG.

**Ranking agent** (LLM, planned) — given the bundled dashboard data across all tickers, decides which one(s) are worth a deeper dive that day. A judgment call based on price moves, news, and trend — not a fixed rule threshold.

**Report agent** (LLM, planned) — writes one combined narrative synthesizing whichever ticker(s) the ranking agent selected, rather than a separate report per ticker.

**Outlook** (planned) — a week-ahead "what to watch for" view based on calendar awareness (upcoming earnings, trend continuation), not statistical price prediction. Statistical forecasting is a deliberately deferred stretch goal.

**UI** (planned) — a default "Today's Report" view shows the ranking output and combined report with no clicking required. A sidebar lists every ticker for drilling into its own dashboard on demand.

There's also a separate, earlier single-ticker pipeline (`planner_agent` → `executor_agent_step` → data/analyst/writer/editor agents, exposed via `POST /analyse`) from before the portfolio direction — superseded by the above, currently not actively maintained.

## Stack
- FastAPI + Postgres (single Docker container)
- SQLAlchemy ORM, Jinja2 templates
- yfinance for market data
- OpenAI / Anthropic APIs for the agent layer

## Roadmap
- Ranking agent + combined report agent (core agentic layer, not yet built)
- Calendar-aware weekly outlook
- Portfolio dashboard UI (sidebar + landing report view)
- Quarterly/yearly analyst report ingestion (nice-to-have)
- Mindmap visualization for relationship/risk-factor structuring (nice-to-have)
- Statistical/ML-based forecasting (deferred)

## Setup

```bash
docker build -t fin-analytics .
docker run -p 8000:8000 --env-file .env fin-analytics
```

Requires a `.env` with `OPENAI_API_KEY` (and `ANTHROPIC_API_KEY` if using the Claude-based image/chart helpers).

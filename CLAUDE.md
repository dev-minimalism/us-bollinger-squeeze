# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A Bollinger Band "volatility squeeze" trading system for the top ~50 US large-cap stocks. It has two parts: a backtester and a real-time monitor that sends Telegram alerts. All data comes from Yahoo Finance via `yfinance`. User-facing text (logs, prompts, Telegram messages) is mostly Korean.

## Commands

```bash
pip install -r requirements.txt          # pinned direct imports only; pip resolves transitive deps

python main.py --mode backtest           # interactive: prompts on stdin for capital, strategy mode, dates
python main.py --mode monitor            # interactive real-time monitoring
python main.py --mode monitor-default    # non-interactive monitoring with defaults (used by the scripts and systemd)
python main.py --mode both               # default: backtest, wait for Enter, then monitor

scripts/start_monitor.sh / stop_monitor.sh / restart_monitor.sh / status_monitor.sh / view_logs.sh
scripts/install_service.sh               # installs systemd unit `volatility-monitor` (Linux)
```

Every script `cd`s to the project root first (its parent dir), so it can be run from anywhere. `start_monitor.sh` runs `monitor-default` with nohup and writes its PID to `output_files/monitor.pid`.

All paths are anchored to the project root via `src/bollinger_squeeze/paths.py` (`PROJECT_ROOT`, `OUTPUT_DIR`, `monitor_log_path()`), never the CWD. Logs from every mode go to `output_files/logs/monitor_YYYYMMDD.log`. Both `main.setup_logging()` and `RealTimeVolatilityMonitor.__init__` call `logging.basicConfig` with that same file; whichever runs first wins.

There are no tests, linter, or build step.

## Environment

The code reads `US_BOLLINGER_TELEGRAM_BOT_TOKEN` and `US_BOLLINGER_TELEGRAM_CHAT_ID`. Without a token, the monitor still runs and only logs.

## Architecture

Source uses a src layout: the package is `src/bollinger_squeeze/` (relative imports inside it). `main.py` stays at the root and inserts `src/` into `sys.path`. To import the modules elsewhere, use `PYTHONPATH=src`.

- `main.py`: argparse CLI that dispatches to the two modules. It also handles interactive config and SIGINT/SIGTERM shutdown.
- `strategy.py`: the single source of the indicator and signal logic, used by both the backtester and the monitor. `calculate_indicators(data, params)` adds the indicator columns plus `Buy_Signal`, `Sell_50_Signal` and `Sell_All_Signal`. `STRATEGY_PARAMS` holds the per-mode thresholds (`aggressive`, `balanced`, `conservative`); unknown modes fall back to conservative. Change strategy rules here, not in the callers.
  - Squeeze: BandWidth < 20-day min × 1.1. Buy: squeeze on the **previous** bar, close above the upper band, Volume_Ratio above the threshold, and RSI inside (rsi_lower, rsi_upper). The previous-bar check is deliberate: on the breakout bar itself the band widens and the squeeze usually ends.
  - Sell 50%: BB_Position ≥ bb_sell_threshold. Sell all: BB_Position ≤ bb_sell_all_threshold or RSI < 30. RSI uses a simple rolling mean, not Wilder's smoothing.
- `backtest_strategy.py` → `VolatilityBollingerBacktest(initial_capital, strategy_mode)`
  - There are several backtest flavors: per-symbol `run_single_backtest` / `run_multi_stock_backtest`, `run_portfolio_backtest` (equal capital per stock), `run_true_portfolio_backtest` (one shared capital pool, invested dynamically in symbols that signal, prioritized by RSI), and `run_comprehensive_analysis`.
  - Every flavor uses the same position state machine: flat → buy → full → sell 50% (once) → half → sell all → flat, with at most one action per bar.
  - Outputs go to `output_files/{results,charts,reports}/` under the project root. Everything under `output_files/` is gitignored. `setup_korean_font()` configures matplotlib so Korean chart labels render.
- `realtime_monitor.py` → `RealTimeVolatilityMonitor(token, chat_id, strategy_mode="balanced")`. It runs these concurrently:
  - a daemon thread for the scan loop (`_auto_monitoring_loop`), which scans only during US market hours. Hours are computed in `US/Eastern` from KST, with a simple holiday check. Every 5 scans it sends a status summary.
  - a daemon thread for the `python-telegram-bot` (v22, async) polling loop, on its own asyncio event loop, with `stop_signals=None`. It handles the `/start`, `/ticker <SYM>` and `/status` commands.
  - a heartbeat thread that sends a status message every hour.
  - `check_signals` returns the raw signals of the latest (possibly still forming) daily bar. `process_signals` applies the same state machine as the backtest (`_decide_action` / `_apply_action`) and alerts only on transitions. Per-symbol state (`full` / `half`, entry price, last action date) persists in `output_files/positions.json`, so it survives restarts. The state transitions even if the Telegram send fails.
  - Outgoing alerts are sent through the Telegram HTTP API with `requests`, not through the bot application. `ticker_to_korean` maps tickers to Korean names for messages.

The two classes keep separate ticker lists that differ. The backtest uses `top50_stocks` and the monitor uses `watchlist`, which includes e.g. `BRK-B`, `NFLX` and `ADBE`.

## Conventions

- Python uses 2-space indentation throughout.
- Code is organized into sections separated by `# ====...` banner comments.

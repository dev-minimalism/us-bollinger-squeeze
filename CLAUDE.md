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
- `backtest_strategy.py` → `VolatilityBollingerBacktest(initial_capital, strategy_mode)`
  - `strategy_mode` is `conservative` (default), `balanced`, or `aggressive`. It sets `rsi_overbought` (70/65/60), `bb_sell_threshold` and `bb_sell_all_threshold`.
  - There are several backtest flavors: per-symbol `run_single_backtest` / `run_multi_stock_backtest`, `run_portfolio_backtest` (equal capital per stock), `run_true_portfolio_backtest` (one shared capital pool, invested dynamically in symbols that signal), and `run_comprehensive_analysis`.
  - Outputs go to `output_files/{results,charts,reports}/`, under the project root. Everything under `output_files/` is gitignored. `setup_korean_font()` configures matplotlib so Korean chart labels render.
- `realtime_monitor.py` → `RealTimeVolatilityMonitor`. It runs these concurrently:
  - a daemon thread for the scan loop (`_auto_monitoring_loop`), which scans only during US market hours. Hours are computed in `US/Eastern` from KST, with a simple holiday check. Every 5 scans it sends a status summary.
  - a daemon thread for the `python-telegram-bot` (v22, async) polling loop, on its own asyncio event loop, with `stop_signals=None`. It handles the `/start`, `/ticker <SYM>` and `/status` commands.
  - a heartbeat thread that sends a status message every hour.
  - Each alert type for each symbol has a 1-hour cooldown (`last_alerts`). Outgoing alerts are sent through the Telegram HTTP API with `requests`, not through the bot application. `ticker_to_korean` maps tickers to Korean names for messages.

### Strategy logic (duplicated, keep in sync)

The indicator and signal code is implemented twice: `VolatilityBollingerBacktest.calculate_technical_indicators` and `RealTimeVolatilityMonitor.calculate_indicators`. It uses BB(20, 2σ) and RSI(14) computed as a simple rolling mean, not Wilder's smoothing. A squeeze means BandWidth is below the 20th percentile of the last 50 days.
- Buy: RSI > threshold AND squeeze.
- Sell 50%: BB_Position ≥ sell threshold OR within 0.1 of the midline.
- Sell all: BB_Position ≤ sell-all threshold.

The monitor hardcodes the conservative values (70 / 0.8 / 0.1) and ignores strategy modes. When you change signal logic, update both files.

The two classes keep separate ticker lists that differ. The backtest uses `top50_stocks` and the monitor uses `watchlist`, which includes e.g. `BRK-B`, `NFLX` and `ADBE`.

## Conventions

- Python uses 2-space indentation throughout.
- Code is organized into sections separated by `# ====...` banner comments.

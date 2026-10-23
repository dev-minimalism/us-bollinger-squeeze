# 변동성 폭파 볼린저 밴드 트레이딩 시스템

[![Python](https://img.shields.io/badge/Python-3-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![yfinance](https://img.shields.io/badge/yfinance-410093)](https://pypi.org/project/yfinance/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

변동성 압축(Bollinger Squeeze) 후 폭파를 노리는 볼린저 밴드 기반 백테스트 및 실시간 알림 시스템입니다. 미국 시총 상위 50개 종목을 대상으로 하며, 데이터는 Yahoo Finance(`yfinance`)에서 가져옵니다.

## 🚀 주요 기능

### 1. 볼린저 스퀴즈 브레이크아웃 전략
- 밴드폭이 최근 20일 최소값 근처일 때 변동성 압축(스퀴즈)으로 판단
- 압축 직후 상단 밴드 돌파 + 거래량 증가 + RSI 범위 내일 때 매수 신호
- 분할 익절: 상단 근처에서 내려오기 시작하면 50% 익절 → 하단 근처 또는 RSI < 30에서 나머지 전량 매도

### 2. 백테스트 (`src/bollinger_squeeze/backtest_strategy.py`)
- 전략 모드 3종: 보수적 / 균형 / 공격적
- 백테스트 유형: 개별 종목 분석, 균등 배분 포트폴리오, 통합 포트폴리오(동적 자금 관리)
- 성과 지표(수익률, 승률, 손익비, 최대낙폭 등), 차트, CSV, 리포트 생성

### 3. 실시간 모니터링 (`src/bollinger_squeeze/realtime_monitor.py`)
- 미국 정규장 시간(한국 시간 기준 자동 변환, 주말/공휴일 제외)에만 스캔
- 신호 발생 시 텔레그램 알림 (종목 한글명, 매수가 대비 수익률 포함)
- 종목별 포지션 상태(미보유 / 전량 보유 / 절반 보유)를 추적해 상태에 맞는 신호만 알림
- 포지션 상태는 `output_files/positions.json`에 저장되어 재시작해도 유지
- 1시간마다 Heartbeat, 5회 스캔마다 상태 요약 전송
- 텔레그램 봇 명령어: `/ticker <심볼>`, `/status`, `/start`

## 📦 설치

```bash
git clone git@github.com:dev-minimalism/us-bollinger-squeeze.git
cd us-bollinger-squeeze

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 파일 구조
```
us-bollinger-squeeze/
├── main.py                       # CLI 진입점
├── src/
│   └── bollinger_squeeze/
│       ├── backtest_strategy.py  # 백테스트 모듈
│       ├── realtime_monitor.py   # 실시간 모니터링 + 텔레그램 봇
│       ├── strategy.py           # 지표·매매 신호 계산 (백테스트·모니터 공용)
│       └── paths.py              # 프로젝트 루트 기준 출력/로그 경로
├── scripts/
│   ├── start_monitor.sh          # 백그라운드 모니터링 시작
│   ├── stop_monitor.sh           # 중지
│   ├── restart_monitor.sh        # 재시작
│   ├── status_monitor.sh         # 상태 확인 (PID, 메모리, CPU)
│   ├── view_logs.sh              # 로그 보기
│   └── install_service.sh        # systemd 서비스 등록 (Linux)
└── output_files/                 # 결과·차트·리포트·로그 (자동 생성, git 제외)
```

## 🔧 사용 방법

### 실행 모드

```bash
python main.py --mode backtest         # 백테스트 (대화형)
python main.py --mode monitor          # 실시간 모니터링 (대화형)
python main.py --mode monitor-default  # 백그라운드용 모니터링 (기본 설정, 입력 없음)
python main.py --mode both             # 백테스트 후 모니터링 (기본값)
```

`backtest` 모드는 아래 항목을 차례로 입력받습니다.
- 초기 자금: $10,000 / $50,000 / $100,000 / 사용자 정의
- 전략 모드: 보수적 / 균형 / 공격적
- 종목 수: 10 / 20 / 30 / 50
- 백테스트 기간
- 백테스트 유형: 개별 / 균등 배분 포트폴리오 / 통합 포트폴리오 / 개별 + 통합

### 텔레그램 알림 설정

1. [@BotFather](https://t.me/BotFather)에서 봇을 만들고 토큰을 복사합니다.
2. [@userinfobot](https://t.me/userinfobot)에서 chat_id를 확인합니다.
3. 환경변수를 설정합니다.
   ```bash
   export US_BOLLINGER_TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export US_BOLLINGER_TELEGRAM_CHAT_ID="your_chat_id_here"
   ```

토큰이 없어도 모니터링은 동작하며, 알림 대신 로그만 남깁니다.

#### 봇 명령어
| 명령어 | 설명 |
|---|---|
| `/ticker AAPL` | 개별 종목 분석 (대소문자 무관) |
| `/status` | 모니터링 상태 확인 |
| `/start` | 도움말 |

### 백그라운드 실행

```bash
./scripts/start_monitor.sh     # nohup으로 monitor-default 실행, PID는 output_files/monitor.pid
./scripts/status_monitor.sh    # 실행 상태 확인
./scripts/view_logs.sh         # 로그 보기
./scripts/restart_monitor.sh   # 재시작
./scripts/stop_monitor.sh      # 중지
```

systemd 서비스로 등록하려면 (Linux):
```bash
./scripts/install_service.sh
sudo systemctl start volatility-monitor
```

### 로그 위치
모든 모드의 로그는 실행 위치와 관계없이 `output_files/logs/monitor_YYYYMMDD.log`에 기록됩니다. `start_monitor.sh`의 표준 출력은 `output_files/logs/nohup.out`에 남습니다.

스크립트는 어느 디렉토리에서 실행해도 프로젝트 루트로 이동한 뒤 동작합니다.

### 모듈 직접 사용

프로젝트 루트에서 `src`를 경로에 추가한 뒤 import합니다 (예: `PYTHONPATH=src python`).

```python
from bollinger_squeeze.backtest_strategy import VolatilityBollingerBacktest

backtest = VolatilityBollingerBacktest(initial_capital=10000, strategy_mode="balanced")
results = backtest.run_multi_stock_backtest("2022-01-01", "2024-01-01", max_stocks=20)
portfolio = backtest.run_true_portfolio_backtest("2022-01-01", "2024-01-01")
```

```python
import os
from bollinger_squeeze.realtime_monitor import RealTimeVolatilityMonitor

monitor = RealTimeVolatilityMonitor(
    telegram_bot_token=os.getenv("US_BOLLINGER_TELEGRAM_BOT_TOKEN"),
    telegram_chat_id=os.getenv("US_BOLLINGER_TELEGRAM_CHAT_ID"),
)
monitor.run_continuous_monitoring(scan_interval=300)  # 5분 간격
```

## 📊 매매 전략 상세

### 기술적 지표
- 볼린저 밴드: 20일, 2σ
- RSI: 14일 (단순 이동평균 방식)
- 변동성 압축: 밴드폭 < 최근 20일 밴드폭 최소값 × 1.1
- 거래량 비율: 당일 거래량 / 20일 평균 거래량
- BB 위치: (종가 − 하단) / (상단 − 하단). 하단 0, 상단 1이며 밴드 밖에서는 범위를 벗어남

### 매수 / 매도 조건
- **매수**: 전일 변동성 압축 AND 종가 > 상단 밴드 AND 거래량 비율 > 기준 AND RSI 하한 < RSI < RSI 상한
- **50% 익절**: 전일 BB 위치 ≥ 익절 기준 AND 당일 BB 위치 < 익절 기준 (상승 모멘텀 둔화, 포지션당 한 번)
- **전량 매도**: BB 위치 ≤ 전량 매도 기준 OR RSI < 30

한 종목에서는 하루(일봉 하나)에 한 번만 매매합니다. 미보유 상태에서는 매수만, 보유 중에는 매도만 판단합니다.

> 50% 익절을 "기준 이상"이 아니라 "기준 아래로 내려옴"으로 판단하는 이유: 돌파로 매수하는 날은 BB 위치가 이미 1을 넘기 때문에, "기준 이상"으로 두면 매수 다음 날 거의 항상 익절하게 됩니다. 상승이 이어지는 동안은 보유하고, 상단에서 밀리기 시작할 때 절반을 익절합니다.

### 전략 모드

| 모드 | 매수 RSI 범위 | 거래량 기준 | 50% 익절 기준 (하향 돌파) | 전량 매도 BB 위치 |
|---|---|---|---|---|
| 보수적 (conservative) | 55 ~ 70 | 1.3배 | 0.90 | 0.10 |
| 균형 (balanced, 기본값) | 50 ~ 75 | 1.2배 | 0.85 | 0.15 |
| 공격적 (aggressive) | 45 ~ 80 | 1.1배 | 0.80 | 0.20 |

백테스트와 실시간 모니터링은 같은 계산 모듈(`strategy.py`)을 씁니다. 실시간 모니터링은 균형 모드가 기본이며, `RealTimeVolatilityMonitor(strategy_mode=...)`로 바꿀 수 있습니다.

> 실시간 모니터링은 장중 미완성 일봉으로 판단합니다. 장 초반에는 거래량 비율이 낮게 계산되므로 매수 신호가 주로 장 후반에 나옵니다.

## 📱 텔레그램 알림 예시

```
🚀 매수 신호 발생!

종목: AAPL (애플)
현재가: $150.25
RSI: 68.4
BB 위치: 1.12
거래량: 20일 평균의 1.8배
시간: 2024-01-15 14:30:00

⚡ 변동성 압축 후 상단 밴드 돌파!
```

```
💡 50% 익절 신호!

종목: AAPL (애플)
현재가: $158.75
BB 위치: 0.91
매수가 대비: +5.66% (매수가 $150.25)
시간: 2024-01-16 10:15:00

📈 목표 수익구간에 도달했습니다.
```

```
🔴 전량 매도 신호!

종목: AAPL (애플)
현재가: $145.10
BB 위치: 0.08
RSI: 35.2
매수가 대비: -3.43% (매수가 $150.25)
시간: 2024-01-20 11:00:00

⚠️ 손절 또는 나머지 익절 시점입니다.
```

## 🛠️ 설정 커스터마이징

- 백테스트 대상 종목: `VolatilityBollingerBacktest.top50_stocks`
- 지표 및 전략 모드별 기준값: `src/bollinger_squeeze/strategy.py` (`STRATEGY_PARAMS`)
- 모니터링 대상 종목: `RealTimeVolatilityMonitor.watchlist`
- 종목 한글명: `RealTimeVolatilityMonitor.ticker_to_korean`
- 알림 쿨다운 / Heartbeat 간격: `alert_cooldown`, `heartbeat_interval` (기본 3600초)
- 모니터 포지션 상태 초기화: 모니터를 중지한 뒤 `output_files/positions.json` 삭제

## 📊 성과 지표 설명

- **Total_Return(%)**: 총 수익률 (초기 자본 대비)
- **Win_Rate(%)**: 승률 (수익 거래 / 전체 거래)
- **Profit_Factor**: 손익비 (평균 수익 / 평균 손실의 절댓값)
- **Max_Drawdown(%)**: 최대 낙폭 (고점 대비 최대 하락률)
- **Avg_Profit/Loss(%)**: 평균 수익/손실률

## 🔍 문제 해결

### 데이터 다운로드 실패
```bash
pip install --upgrade yfinance
python -c "import yfinance as yf; print(yf.Ticker('AAPL').history(period='5d'))"
```

### 텔레그램 알림이 오지 않음
- 환경변수 이름이 `US_BOLLINGER_TELEGRAM_BOT_TOKEN` / `US_BOLLINGER_TELEGRAM_CHAT_ID`인지 확인하세요.
- 토큰 확인:
  ```bash
  curl "https://api.telegram.org/bot${US_BOLLINGER_TELEGRAM_BOT_TOKEN}/getMe"
  ```

### 백테스트가 너무 오래 걸림
종목 수를 10~20개로 줄여서 실행하세요.

## ⚠️ 주의사항

1. **데이터 지연**: Yahoo Finance 데이터는 15~20분 지연될 수 있습니다.
2. **API 제한**: 요청이 많으면 일시적으로 차단될 수 있습니다.
3. **공휴일**: 미국 공휴일은 주요 휴일만 간단히 처리합니다.
4. **실전 적용**: 충분히 검증한 뒤 소액으로 시작하세요.

## ⚖️ 면책조항

본 소프트웨어는 교육 및 연구 목적으로만 제공됩니다. 실제 투자에 사용하여 발생하는 손실에 대해 개발자는 책임지지 않습니다. 투자는 본인의 책임 하에 신중하게 결정하시기 바랍니다.

## 📄 라이선스

[MIT License](LICENSE)

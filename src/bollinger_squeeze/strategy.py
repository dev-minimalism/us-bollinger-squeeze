"""
볼린저 스퀴즈 브레이크아웃 전략 (백테스트와 실시간 모니터링 공용)

- 스퀴즈: 밴드폭이 최근 20일 최소값의 1.1배 미만
- 매수: 전일 스퀴즈 + 종가 상단밴드 돌파 + 거래량 증가 + RSI 범위 내
- 50% 익절: BB 위치가 익절 기준 이상
- 전량 매도: BB 위치가 전량 매도 기준 이하 또는 RSI < 30
"""

from typing import Dict

import pandas as pd

# 지표 설정
BB_PERIOD = 20
BB_STD_MULTIPLIER = 2.0
RSI_PERIOD = 14
SQUEEZE_LOOKBACK = 20
SQUEEZE_TOLERANCE = 1.1  # 최근 최소 밴드폭 대비 허용 배수
VOLUME_MA_PERIOD = 20
RSI_STOP_LOSS = 30

# 스퀴즈 판정에 필요한 최소 데이터 (밴드 20일 + 밴드폭 최소값 20일 + 여유)
MIN_DATA_LENGTH = 50

DEFAULT_STRATEGY_MODE = "balanced"

# 모드별 매매 기준값
STRATEGY_PARAMS: Dict[str, Dict[str, float]] = {
  "aggressive": {  # 빠른 브레이크아웃 감지
    "rsi_lower": 45,
    "rsi_upper": 80,
    "volume_threshold": 1.1,
    "bb_sell_threshold": 0.8,
    "bb_sell_all_threshold": 0.2,
  },
  "balanced": {  # 안정적 브레이크아웃 확인
    "rsi_lower": 50,
    "rsi_upper": 75,
    "volume_threshold": 1.2,
    "bb_sell_threshold": 0.85,
    "bb_sell_all_threshold": 0.15,
  },
  "conservative": {  # 강한 브레이크아웃만 포착
    "rsi_lower": 55,
    "rsi_upper": 70,
    "volume_threshold": 1.3,
    "bb_sell_threshold": 0.9,
    "bb_sell_all_threshold": 0.1,
  },
}


def get_strategy_params(strategy_mode: str) -> Dict[str, float]:
  """모드별 기준값 (알 수 없는 모드는 conservative)"""
  return STRATEGY_PARAMS.get(strategy_mode, STRATEGY_PARAMS["conservative"])


def calculate_indicators(data: pd.DataFrame,
    params: Dict[str, float]) -> pd.DataFrame:
  """기술적 지표와 매매 신호 컬럼 계산"""
  if len(data) < MIN_DATA_LENGTH:
    return data

  # 볼린저 밴드
  data['SMA'] = data['Close'].rolling(window=BB_PERIOD).mean()
  data['STD'] = data['Close'].rolling(window=BB_PERIOD).std()
  data['Upper_Band'] = data['SMA'] + (data['STD'] * BB_STD_MULTIPLIER)
  data['Lower_Band'] = data['SMA'] - (data['STD'] * BB_STD_MULTIPLIER)

  # 밴드폭과 스퀴즈
  data['Band_Width'] = (data['Upper_Band'] - data['Lower_Band']) / data['SMA']
  data['Volatility_Squeeze'] = data['Band_Width'] < (
      data['Band_Width'].rolling(SQUEEZE_LOOKBACK).min() * SQUEEZE_TOLERANCE)

  # 볼린저 밴드 위치 (하단 0 ~ 상단 1, 밴드 밖이면 범위를 벗어남)
  data['BB_Position'] = (data['Close'] - data['Lower_Band']) / (
      data['Upper_Band'] - data['Lower_Band'])

  # RSI (단순 이동평균 방식)
  delta = data['Close'].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
  rs = gain / loss
  data['RSI'] = 100 - (100 / (1 + rs))

  # 거래량 비율
  if 'Volume' in data.columns:
    data['Volume_MA'] = data['Volume'].rolling(VOLUME_MA_PERIOD).mean()
    data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']
  else:
    data['Volume_MA'] = 1
    data['Volume_Ratio'] = 1

  # 매수: 전일까지 압축 → 오늘 상단 돌파 (돌파 당일은 밴드폭이 커져 압축이 풀리기 쉬움)
  prev_squeeze = data['Volatility_Squeeze'].shift(1, fill_value=False).astype(bool)
  data['Buy_Signal'] = (
      prev_squeeze &
      (data['Close'] > data['Upper_Band']) &
      (data['Volume_Ratio'] > params['volume_threshold']) &
      (data['RSI'] > params['rsi_lower']) &
      (data['RSI'] < params['rsi_upper'])
  )

  data['Sell_50_Signal'] = data['BB_Position'] >= params['bb_sell_threshold']
  data['Sell_All_Signal'] = (
      (data['BB_Position'] <= params['bb_sell_all_threshold']) |
      (data['RSI'] < RSI_STOP_LOSS)
  )

  return data

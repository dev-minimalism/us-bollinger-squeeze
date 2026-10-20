# backtest_strategy.py
"""
변동성 폭파 볼린저 밴드 백테스트 전용 모듈

주요 기능:
- 변동성 폭파 볼린저 밴드 전략 백테스트
- 미국 시총 50위 종목 자동 분석
- 상세한 성과 지표 계산 및 시각화
- CSV 결과 저장 및 차트 생성
"""

import os
import platform
import time
import warnings
from datetime import datetime
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

from .paths import OUTPUT_DIR, PROJECT_ROOT

warnings.filterwarnings('ignore')


# ===================================================================================
# 한글 폰트 설정
# ===================================================================================

def setup_korean_font():
  """한글 폰트 설정 (개선된 버전)"""
  try:
    import matplotlib.font_manager as fm

    system = platform.system()

    # 운영체제별 한글 폰트 설정
    if system == "Windows":
      font_candidates = [
        'C:/Windows/Fonts/malgun.ttf',  # 맑은 고딕
        'C:/Windows/Fonts/gulim.ttc',  # 굴림
        'C:/Windows/Fonts/batang.ttc'  # 바탕
      ]
      font_names = ['Malgun Gothic', 'Gulim', 'Batang', 'Arial Unicode MS']

    elif system == "Darwin":  # macOS
      font_candidates = [
        '/Library/Fonts/AppleSDGothicNeo.ttc',
        '/System/Library/Fonts/AppleGothic.ttf',
        '/Library/Fonts/NanumGothic.ttf'
      ]
      font_names = ['Apple SD Gothic Neo', 'AppleGothic', 'NanumGothic',
                    'Arial Unicode MS']

    else:  # Linux
      font_candidates = [
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf',
        '/usr/share/fonts/TTF/NanumGothic.ttf'
      ]
      font_names = ['NanumGothic', 'DejaVu Sans', 'Liberation Sans']

    # 1. 파일 경로로 폰트 찾기
    font_found = False
    for font_path in font_candidates:
      if os.path.exists(font_path):
        try:
          # 폰트 파일을 matplotlib에 등록
          fm.fontManager.addfont(font_path)
          prop = fm.FontProperties(fname=font_path)
          plt.rcParams['font.family'] = prop.get_name()
          font_found = True
          print(f"✅ 한글 폰트 설정: {font_path}")
          break
        except Exception as e:
          continue

    # 2. 시스템 설치 폰트에서 찾기
    if not font_found:
      available_fonts = [f.name for f in fm.fontManager.ttflist]
      for font_name in font_names:
        if font_name in available_fonts:
          try:
            plt.rcParams['font.family'] = font_name
            font_found = True
            print(f"✅ 한글 폰트 설정: {font_name}")
            break
          except Exception as e:
            continue

    # 3. 기본 대체 폰트 설정
    if not font_found:
      if system == "Windows":
        plt.rcParams['font.family'] = ['Arial Unicode MS', 'DejaVu Sans',
                                       'Arial']
      elif system == "Darwin":
        plt.rcParams['font.family'] = ['Arial Unicode MS', 'Helvetica',
                                       'DejaVu Sans']
      else:
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Liberation Sans',
                                       'Arial']

      print("⚠️ 한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다.")

    # 마이너스 기호 깨짐 방지
    plt.rcParams['axes.unicode_minus'] = False

    return font_found

  except Exception as e:
    print(f"⚠️ 폰트 설정 중 오류: {e}")
    plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    return False


# 폰트 초기화
setup_korean_font()


# ===================================================================================
# 메인 백테스트 클래스
# ===================================================================================

class VolatilityBollingerBacktest:
  """변동성 폭파 볼린저 밴드 백테스트 클래스"""

  # 미국 시총 50위 종목 리스트 검증 및 업데이트
  def __init__(self, initial_capital: float = 10000, strategy_mode: str = "conservative"):
    """초기화 (종목 리스트 검증 포함)"""

    # 미국 시총 50위 종목 (2024년 기준 업데이트)
    self.top50_stocks = [
      # 기술주
      'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'CRM',
      # 금융
      'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'BLK',
      # 헬스케어
      'UNH', 'JNJ', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'LLY',
      # 소비재
      'HD', 'PG', 'KO', 'PEP', 'WMT', 'COST', 'MCD', 'NKE', 'SBUX', 'TGT',
      # 에너지/산업
      'XOM', 'CVX', 'COP', 'SLB', 'CAT', 'BA', 'GE', 'HON', 'UPS', 'RTX'
    ]

    # 백테스트 설정
    self.initial_capital = initial_capital
    self.strategy_mode = strategy_mode
    self._setup_parameters(strategy_mode)

    # 출력 디렉토리 설정 및 생성
    self._setup_output_directories()

    print(f"💰 초기 자금: ${self.initial_capital:,.2f}")
    print(f"📊 전략 모드: {strategy_mode.upper()}")
    print(f"📋 분석 대상: {len(self.top50_stocks)}개 종목")


  def _setup_output_directories(self):
    """출력 디렉토리 설정 및 생성"""
    # 프로젝트 루트 기준으로 출력 디렉토리 설정
    base_dir = PROJECT_ROOT

    self.output_base_dir = OUTPUT_DIR
    self.results_dir = os.path.join(self.output_base_dir, 'results')
    self.charts_dir = os.path.join(self.output_base_dir, 'charts')
    self.reports_dir = os.path.join(self.output_base_dir, 'reports')

    # 디렉토리 생성
    for directory in [self.output_base_dir, self.results_dir, self.charts_dir,
                      self.reports_dir]:
      try:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 디렉토리 준비: {os.path.relpath(directory)}")
      except Exception as e:
        print(f"⚠️ 디렉토리 생성 오류 ({directory}): {e}")
        # 현재 디렉토리를 대안으로 사용
        if directory == self.results_dir:
          self.results_dir = base_dir
        elif directory == self.charts_dir:
          self.charts_dir = base_dir
        elif directory == self.reports_dir:
          self.reports_dir = base_dir

  def _setup_parameters(self, strategy_mode: str):
    """전략 매개변수 설정 (모드별)"""
    self.bb_period = 20
    self.bb_std_multiplier = 2.0
    self.rsi_period = 14
    self.volatility_lookback = 50
    self.volatility_threshold = 0.2

    if strategy_mode == "aggressive":
      # 공격적 전략: 더 많은 매매 기회
      self.rsi_overbought = 60  # 낮춤 (더 빨리 매수)
      self.bb_sell_threshold = 0.7  # 낮춤 (더 빨리 50% 익절)
      self.bb_sell_all_threshold = 0.2  # 높임 (덜 빨리 전량 매도)
      print("🔥 공격적 전략: 더 많은 매매 기회, 높은 수익 추구")

    elif strategy_mode == "balanced":
      # 균형 전략: 적당한 매매
      self.rsi_overbought = 65
      self.bb_sell_threshold = 0.75
      self.bb_sell_all_threshold = 0.15
      print("⚖️ 균형 전략: 적당한 위험과 수익")

    else:  # conservative
      # 보수적 전략: 기존 설정
      self.rsi_overbought = 70
      self.bb_sell_threshold = 0.8
      self.bb_sell_all_threshold = 0.1
      print("🛡️ 보수적 전략: 안전 우선, 신중한 매매")

  # ===================================================================================
  # 기술적 지표 계산
  # ===================================================================================

  def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
    """기술적 지표 계산"""
    if len(data) < max(self.bb_period, self.rsi_period,
                       self.volatility_lookback):
      return data

    # 볼린저 밴드
    data['SMA'] = data['Close'].rolling(window=self.bb_period).mean()
    data['STD'] = data['Close'].rolling(window=self.bb_period).std()
    data['Upper_Band'] = data['SMA'] + (data['STD'] * self.bb_std_multiplier)
    data['Lower_Band'] = data['SMA'] - (data['STD'] * self.bb_std_multiplier)

    # 밴드폭 (변동성 지표)
    data['Band_Width'] = (data['Upper_Band'] - data['Lower_Band']) / data['SMA']

    # 변동성 압축 신호
    data['Volatility_Squeeze'] = (
        data['Band_Width'] < data['Band_Width'].rolling(
        self.volatility_lookback).quantile(self.volatility_threshold)
    )

    # 볼린저 밴드 위치 (0~1)
    data['BB_Position'] = (data['Close'] - data['Lower_Band']) / (
        data['Upper_Band'] - data['Lower_Band'])

    # RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    # 매매 신호 생성 (개선된 버전)
    data['Buy_Signal'] = (data['RSI'] > self.rsi_overbought) & (
      data['Volatility_Squeeze'])
    data['Sell_50_Signal'] = (data['BB_Position'] >= self.bb_sell_threshold) | (
        abs(data['BB_Position'] - 0.5) <= 0.1)
    data['Sell_All_Signal'] = data['BB_Position'] <= self.bb_sell_all_threshold

    return data

  # ===================================================================================
  # 백테스트 실행
  # ===================================================================================

  def run_single_backtest(self, symbol: str, start_date: str, end_date: str) -> Optional[Dict]:
    """단일 종목 백테스트 (개선된 버전)"""
    try:
      # 데이터 다운로드 (더 자세한 디버깅)
      stock = yf.Ticker(symbol)

      # 데이터 다운로드 시도
      data = stock.history(start=start_date, end=end_date, auto_adjust=True, prepost=True)

      # 데이터 검증
      if data.empty:
        print(f"❌ {symbol}: 데이터 없음", end="")
        return None

      if len(data) < self.volatility_lookback:
        print(f"❌ {symbol}: 데이터 부족 ({len(data)}일 < {self.volatility_lookback}일)", end="")
        return None

      # 데이터 품질 검증
      if data['Close'].isna().sum() > len(data) * 0.1:  # 10% 이상이 NaN이면 제외
        print(f"❌ {symbol}: 데이터 품질 불량", end="")
        return None

      # 가격이 너무 낮거나 높으면 제외 (penny stock이나 오류 데이터)
      avg_price = data['Close'].mean()
      if avg_price < 1 or avg_price > 10000:
        print(f"❌ {symbol}: 비정상 가격 (평균: ${avg_price:.2f})", end="")
        return None

      # 기술적 지표 계산
      data = self.calculate_technical_indicators(data)

      # 지표 검증
      if data['RSI'].isna().all() or data['SMA'].isna().all():
        print(f"❌ {symbol}: 지표 계산 실패", end="")
        return None

      # 백테스트 실행
      result = self._execute_backtest(data, symbol, start_date, end_date)
      result['data'] = data

      return result

    except Exception as e:
      # 더 구체적인 오류 메시지
      error_msg = str(e)
      if "No data found" in error_msg:
        print(f"❌ {symbol}: 데이터 없음", end="")
      elif "Invalid ticker" in error_msg:
        print(f"❌ {symbol}: 잘못된 티커", end="")
      elif "timeout" in error_msg.lower():
        print(f"❌ {symbol}: 타임아웃", end="")
      else:
        print(f"❌ {symbol}: {error_msg[:20]}...", end="")
      return None

  def _execute_backtest(self, data: pd.DataFrame, symbol: str, start_date: str,
      end_date: str) -> Dict:
    """백테스트 로직 실행"""
    position = 0  # 0: 노포지션, 1: 50%, 2: 100%
    cash = self.initial_capital
    shares = 0
    trades = []
    equity_curve = []

    for i in range(len(data)):
      current_price = data.iloc[i]['Close']
      current_date = data.index[i]

      # 매수 신호
      if data.iloc[i]['Buy_Signal'] and position == 0:
        shares = cash / current_price
        position = 2

        trades.append({
          'date': current_date,
          'action': 'BUY',
          'price': current_price,
          'shares': shares,
          'value': cash
        })

      # 50% 익절
      elif data.iloc[i]['Sell_50_Signal'] and position == 2:
        sell_shares = shares * 0.5
        cash += sell_shares * current_price
        shares -= sell_shares
        position = 1

        trades.append({
          'date': current_date,
          'action': 'SELL_50%',
          'price': current_price,
          'shares': sell_shares,
          'value': sell_shares * current_price
        })

      # 전량 매도
      elif data.iloc[i]['Sell_All_Signal'] and position > 0:
        cash += shares * current_price

        trades.append({
          'date': current_date,
          'action': 'SELL_ALL',
          'price': current_price,
          'shares': shares,
          'value': shares * current_price
        })

        shares = 0
        position = 0

      # 자산가치 기록
      portfolio_value = cash + (shares * current_price)
      equity_curve.append({
        'date': current_date,
        'portfolio_value': portfolio_value,
        'cash': cash,
        'stock_value': shares * current_price
      })

    # 마지막 포지션 청산
    if shares > 0:
      cash += shares * data.iloc[-1]['Close']

    # 성과 지표 계산
    metrics = self._calculate_metrics(trades, equity_curve, cash, start_date,
                                      end_date)

    return {
      'symbol': symbol,
      'trades': trades,
      'equity_curve': equity_curve,
      'final_cash': cash,
      **metrics
    }

  def _calculate_metrics(self, trades: List[Dict], equity_curve: List[Dict],
      final_cash: float, start_date: str, end_date: str) -> Dict:
    """성과 지표 계산"""
    # 기본 수익률
    total_return = (
                       final_cash - self.initial_capital) / self.initial_capital * 100

    # 거래 분석
    completed_trades = self._analyze_trades(trades)

    # 통계 계산
    total_trades = len(completed_trades)
    winning_trades = sum(1 for t in completed_trades if t['is_winning'])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    # 수익/손실 분석
    profits = [t['profit_pct'] for t in completed_trades if t['is_winning']]
    losses = [t['profit_pct'] for t in completed_trades if not t['is_winning']]

    avg_profit = np.mean(profits) if profits else 0
    avg_loss = np.mean(losses) if losses else 0
    profit_factor = abs(avg_profit / avg_loss) if avg_loss != 0 else float(
        'inf')

    # 최대 낙폭
    max_drawdown = self._calculate_max_drawdown(equity_curve)

    # 테스트 기간
    test_period_days = self._calculate_test_period_days(start_date, end_date)

    return {
      'total_return': total_return,
      'win_rate': win_rate,
      'total_trades': total_trades,
      'winning_trades': winning_trades,
      'avg_profit': avg_profit,
      'avg_loss': avg_loss,
      'profit_factor': profit_factor,
      'max_drawdown': max_drawdown,
      'final_value': final_cash,
      'completed_trades': completed_trades,
      'test_period_days': test_period_days
    }

  def _analyze_trades(self, trades: List[Dict]) -> List[Dict]:
    """거래 분석"""
    completed_trades = []
    buy_trade = None

    for trade in trades:
      if trade['action'] == 'BUY':
        buy_trade = trade
      elif buy_trade and trade['action'] in ['SELL_50%', 'SELL_ALL']:
        profit_pct = (trade['price'] - buy_trade['price']) / buy_trade[
          'price'] * 100

        completed_trades.append({
          'entry_date': buy_trade['date'],
          'exit_date': trade['date'],
          'entry_price': buy_trade['price'],
          'exit_price': trade['price'],
          'profit_pct': profit_pct,
          'is_winning': profit_pct > 0
        })

        if trade['action'] == 'SELL_ALL':
          buy_trade = None

    return completed_trades

  def _calculate_max_drawdown(self, equity_curve: List[Dict]) -> float:
    """최대 낙폭 계산"""
    if not equity_curve:
      return 0

    portfolio_values = [eq['portfolio_value'] for eq in equity_curve]
    peak = portfolio_values[0]
    max_drawdown = 0

    for value in portfolio_values:
      if value > peak:
        peak = value
      drawdown = (peak - value) / peak * 100
      if drawdown > max_drawdown:
        max_drawdown = drawdown

    return max_drawdown

  def _calculate_test_period_days(self, start_date: str, end_date: str) -> int:
    """테스트 기간 일수 계산"""
    try:
      start = datetime.strptime(start_date, '%Y-%m-%d')
      end = datetime.strptime(end_date, '%Y-%m-%d')
      return (end - start).days
    except:
      return 0

  # ===================================================================================
  # 포트폴리오 백테스트 (신규 추가)
  # ===================================================================================

  def run_true_portfolio_backtest(self, start_date: str, end_date: str, max_stocks: int = 50) -> Dict:
    """진정한 통합 포트폴리오 백테스트 (개선된 버전)"""
    print("=" * 80)
    print("💼 진정한 통합 포트폴리오 백테스트 시작")
    print("=" * 80)

    stocks_to_test = self.top50_stocks[:max_stocks]

    print(f"💰 총 자금: ${self.initial_capital:,.2f} (통합 관리)")
    print(f"📊 대상 종목: {len(stocks_to_test)}개")
    print(f"🎯 전략: 신호 발생한 종목에만 동적 투자")

    # 각 종목별 데이터 준비
    stock_data = {}
    valid_stocks = []
    failed_stocks = []

    print(f"\n📥 데이터 다운로드 중...")
    print("-" * 80)

    for i, symbol in enumerate(stocks_to_test):
      print(f"진행: {i + 1:2d}/{len(stocks_to_test)} - {symbol}", end=" ... ")

      retry_count = 0
      max_retries = 2
      success = False

      while retry_count < max_retries and not success:
        try:
          stock = yf.Ticker(symbol)
          data = stock.history(start=start_date, end=end_date, auto_adjust=True)

          if data.empty or len(data) < self.volatility_lookback:
            if retry_count == 0:
              print("데이터 부족", end="")
            break

          # 데이터 품질 검증
          if data['Close'].isna().sum() > len(data) * 0.1:
            print("품질 불량", end="")
            break

          data = self.calculate_technical_indicators(data)

          if data['RSI'].isna().all():
            print("지표 실패", end="")
            break

          stock_data[symbol] = data
          valid_stocks.append(symbol)
          print("완료")
          success = True

        except Exception as e:
          retry_count += 1
          if retry_count < max_retries:
            print(f"재시도({retry_count})", end="...")
            time.sleep(0.5)
          else:
            print(f"실패")
            failed_stocks.append(symbol)

        time.sleep(0.05)  # API 제한 방지

      if not success and retry_count >= max_retries:
        failed_stocks.append(symbol)

      # 중간 요약 (매 10개마다)
      if (i + 1) % 10 == 0:
        print(f"📊 진행률: {len(valid_stocks)}/{i+1} 성공 ({len(valid_stocks)/(i+1)*100:.1f}%)")

    print("-" * 80)
    print(f"✅ 유효 종목: {len(valid_stocks)}개")
    if failed_stocks:
      print(f"❌ 실패 종목: {len(failed_stocks)}개 - {', '.join(failed_stocks[:5])}" +
            (f" 외 {len(failed_stocks)-5}개" if len(failed_stocks) > 5 else ""))

    if not valid_stocks:
      print("❌ 분석 가능한 종목이 없습니다.")
      return {}

    # 진정한 통합 포트폴리오 백테스트 실행
    result = self._execute_true_portfolio_backtest(stock_data, valid_stocks)

    # 결과에 실패 정보 추가
    if result:
      result['failed_stocks'] = failed_stocks
      result['success_rate'] = len(valid_stocks) / len(stocks_to_test) * 100

    return result

  def _execute_true_portfolio_backtest(self, stock_data: Dict,
      valid_stocks: List[str]) -> Dict:
    """진정한 통합 포트폴리오 백테스트 로직"""
    # 모든 날짜 통합
    all_dates = None
    for symbol in valid_stocks:
      if all_dates is None:
        all_dates = set(stock_data[symbol].index)
      else:
        all_dates = all_dates.intersection(set(stock_data[symbol].index))

    all_dates = sorted(list(all_dates))

    if not all_dates:
      return {}

    print(f"📅 거래일: {len(all_dates)}일")

    # 통합 포트폴리오 상태
    total_cash = self.initial_capital
    holdings = {}  # {symbol: shares}
    portfolio_history = []
    all_trades = []
    max_positions = 10  # 최대 동시 보유 종목 수

    print(f"\n⚡ 진정한 통합 포트폴리오 백테스트 실행...")
    print(f"📊 최대 동시 보유: {max_positions}개 종목")

    for i, date in enumerate(all_dates):
      if (i + 1) % 50 == 0:
        print(
            f"진행률: {i + 1}/{len(all_dates)} ({(i + 1) / len(all_dates) * 100:.1f}%)")

      daily_signals = []

      # 1. 모든 종목의 신호 수집
      for symbol in valid_stocks:
        try:
          data = stock_data[symbol]
          if date not in data.index:
            continue

          row = data.loc[date]
          current_price = row['Close']

          # 신호 정보 수집
          signal_info = {
            'symbol': symbol,
            'price': current_price,
            'buy_signal': row['Buy_Signal'],
            'sell_50_signal': row['Sell_50_Signal'],
            'sell_all_signal': row['Sell_All_Signal'],
            'rsi': row['RSI'],
            'bb_position': row['BB_Position']
          }
          daily_signals.append(signal_info)

        except:
          continue

      # 2. 매도 신호 우선 처리 (현금 확보)
      for signal in daily_signals:
        symbol = signal['symbol']
        if symbol not in holdings:
          continue

        current_shares = holdings[symbol]
        current_price = signal['price']

        # 50% 매도
        if signal['sell_50_signal'] and current_shares > 0:
          sell_shares = current_shares * 0.5
          sell_value = sell_shares * current_price
          total_cash += sell_value
          holdings[symbol] = current_shares - sell_shares

          trade = {
            'date': date,
            'symbol': symbol,
            'action': 'SELL_50%',
            'price': current_price,
            'shares': sell_shares,
            'value': sell_value
          }
          all_trades.append(trade)

        # 전량 매도
        elif signal['sell_all_signal'] and current_shares > 0:
          sell_value = current_shares * current_price
          total_cash += sell_value

          trade = {
            'date': date,
            'symbol': symbol,
            'action': 'SELL_ALL',
            'price': current_price,
            'shares': current_shares,
            'value': sell_value
          }
          all_trades.append(trade)

          del holdings[symbol]  # 포지션 완전 삭제

      # 3. 매수 신호 처리 (RSI 순으로 우선순위)
      buy_candidates = [s for s in daily_signals if
                        s['buy_signal'] and s['symbol'] not in holdings]
      buy_candidates.sort(key=lambda x: x['rsi'], reverse=True)  # RSI 높은 순

      current_positions = len(holdings)
      available_slots = max_positions - current_positions

      for signal in buy_candidates[:available_slots]:
        if total_cash < 1000:  # 최소 투자금액
          break

        symbol = signal['symbol']
        current_price = signal['price']

        # 사용 가능한 현금의 일정 비율로 투자 (리스크 분산)
        investment_ratio = min(0.2, 1.0 / max_positions)  # 최대 20% 또는 균등분할
        investment_amount = total_cash * investment_ratio

        if investment_amount >= 1000:  # 최소 $1000 투자
          shares = investment_amount / current_price
          total_cash -= investment_amount
          holdings[symbol] = shares

          trade = {
            'date': date,
            'symbol': symbol,
            'action': 'BUY',
            'price': current_price,
            'shares': shares,
            'value': investment_amount
          }
          all_trades.append(trade)

      # 4. 포트폴리오 가치 계산
      total_stock_value = 0
      for symbol, shares in holdings.items():
        try:
          current_price = next(
              s['price'] for s in daily_signals if s['symbol'] == symbol)
          total_stock_value += shares * current_price
        except:
          continue

      total_portfolio_value = total_cash + total_stock_value

      portfolio_history.append({
        'date': date,
        'total_value': total_portfolio_value,
        'cash': total_cash,
        'stock_value': total_stock_value,
        'positions': len(holdings),
        'daily_trades': len([t for t in all_trades if t['date'] == date])
      })

    # 최종 청산
    final_date = all_dates[-1]
    for symbol, shares in holdings.items():
      try:
        final_price = stock_data[symbol].loc[final_date]['Close']
        total_cash += shares * final_price
      except:
        continue

    # 결과 계산
    total_return = (
                       total_cash - self.initial_capital) / self.initial_capital * 100
    total_profit = total_cash - self.initial_capital

    # 통계 계산
    stats = self._calculate_true_portfolio_stats(portfolio_history, all_trades,
                                                 total_cash)

    result = {
      'initial_capital': self.initial_capital,
      'final_value': total_cash,
      'total_profit': total_profit,
      'total_return': total_return,
      'valid_stocks': valid_stocks,
      'portfolio_history': portfolio_history,
      'all_trades': all_trades,
      'final_holdings': holdings,
      'max_positions': max_positions,
      **stats
    }

    self._print_true_portfolio_results(result)
    return result

  def _calculate_true_portfolio_stats(self, portfolio_history: List[Dict],
      all_trades: List[Dict], final_value: float) -> Dict:
    """진정한 포트폴리오 통계 계산"""
    if not portfolio_history:
      return {}

    values = [p['total_value'] for p in portfolio_history]

    # 최대 낙폭
    peak = values[0]
    max_drawdown = 0
    for value in values:
      if value > peak:
        peak = value
      drawdown = (peak - value) / peak * 100
      if drawdown > max_drawdown:
        max_drawdown = drawdown

    # 일일 수익률
    daily_returns = []
    for i in range(1, len(values)):
      daily_return = (values[i] - values[i - 1]) / values[i - 1] * 100
      daily_returns.append(daily_return)

    volatility = np.std(daily_returns) if daily_returns else 0
    avg_daily_return = np.mean(daily_returns) if daily_returns else 0

    # 샤프 비율
    sharpe_ratio = (avg_daily_return * 252) / (
        volatility * np.sqrt(252)) if volatility > 0 else 0

    # 거래 통계
    buy_trades = len([t for t in all_trades if t['action'] == 'BUY'])
    sell_trades = len(
        [t for t in all_trades if t['action'] in ['SELL_50%', 'SELL_ALL']])

    # 포지션 통계
    avg_positions = np.mean([p['positions'] for p in portfolio_history])
    max_positions_held = max([p['positions'] for p in portfolio_history])

    return {
      'max_drawdown': max_drawdown,
      'volatility': volatility,
      'sharpe_ratio': sharpe_ratio,
      'total_trade_count': len(all_trades),
      'buy_trades': buy_trades,
      'sell_trades': sell_trades,
      'avg_daily_return': avg_daily_return,
      'avg_positions': avg_positions,
      'max_positions_held': max_positions_held
    }

  def _print_true_portfolio_results(self, result: Dict):
    """진정한 포트폴리오 결과 출력"""
    print(f"\n{'=' * 80}")
    print(f"💼 진정한 통합 포트폴리오 백테스트 결과")
    print(f"{'=' * 80}")

    print(f"💰 초기 자금:        ${result['initial_capital']:>12,.2f}")
    print(f"💵 최종 자산:        ${result['final_value']:>12,.2f}")
    print(f"💲 총 수익금:        ${result['total_profit']:>12,.2f}")
    print(f"📈 총 수익률:        {result['total_return']:>12.2f}%")

    # 연율화 수익률
    if result.get('portfolio_history'):
      days = len(result['portfolio_history'])
      if days > 0:
        annualized = ((result['final_value'] / result['initial_capital']) ** (
            365 / days) - 1) * 100
        print(f"📊 연율화 수익률:    {annualized:>12.2f}%")

    print(f"\n📊 포트폴리오 운용 통계:")
    print(f"📊 감시 종목:        {len(result['valid_stocks']):>12d}개")
    print(f"🎯 최대 동시보유:    {result['max_positions']:>12d}개")
    print(f"📊 평균 보유종목:    {result['avg_positions']:>12.1f}개")
    print(f"📊 최대 보유기록:    {result['max_positions_held']:>12d}개")
    print(f"🔢 총 거래:         {result['total_trade_count']:>12d}회")
    print(f"📊 매수:           {result['buy_trades']:>12d}회")
    print(f"📊 매도:           {result['sell_trades']:>12d}회")
    print(f"📉 최대 낙폭:        {result['max_drawdown']:>12.2f}%")
    print(f"📊 변동성:          {result['volatility']:>12.2f}%")
    print(f"⚖️ 샤프 비율:       {result['sharpe_ratio']:>12.2f}")

    # 성과 평가
    if result['total_return'] > 20:
      evaluation = "🌟 우수"
    elif result['total_return'] > 10:
      evaluation = "✅ 양호"
    elif result['total_return'] > 0:
      evaluation = "📈 수익"
    else:
      evaluation = "📉 손실"
    print(f"🏆 성과 평가:        {evaluation}")

    print(f"\n💡 진정한 통합 포트폴리오 특징:")
    print(f"   🎯 신호 기반 동적 투자 (종목별 고정 배분 없음)")
    print(f"   💰 현금과 주식 비율 유동적 관리")
    print(f"   📊 최대 {result['max_positions']}개 종목 동시 보유")
    print(f"   ⚖️ RSI 기준 투자 우선순위 결정")

    print(f"{'=' * 80}")

  def run_portfolio_backtest(self, start_date: str, end_date: str,
      max_stocks: int = 50) -> Dict:
    """통합 포트폴리오 백테스트"""
    print("=" * 80)
    print("💼 통합 포트폴리오 백테스트 시작")
    print("=" * 80)

    stocks_to_test = self.top50_stocks[:max_stocks]
    stock_allocation = self.initial_capital / len(
        stocks_to_test)  # 종목당 동일 금액 배분

    print(f"💰 총 초기 자금: ${self.initial_capital:,.2f}")
    print(f"📊 대상 종목 수: {len(stocks_to_test)}개")
    print(f"💵 종목당 배분: ${stock_allocation:,.2f}")

    # 각 종목별 데이터 및 지표 준비
    stock_data = {}
    valid_stocks = []

    print(f"\n📥 데이터 다운로드 중...")
    for i, symbol in enumerate(stocks_to_test):
      print(f"진행: {i + 1:2d}/{len(stocks_to_test)} - {symbol}", end=" ... ")

      try:
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)

        if data.empty or len(data) < self.volatility_lookback:
          print("실패 (데이터 부족)")
          continue

        # 기술적 지표 계산
        data = self.calculate_technical_indicators(data)
        stock_data[symbol] = data
        valid_stocks.append(symbol)
        print("완료")

      except Exception as e:
        print(f"실패 ({e})")
        continue

      time.sleep(0.05)  # API 제한 방지

    if not valid_stocks:
      print("❌ 유효한 종목이 없습니다.")
      return {}

    print(f"\n✅ 유효 종목: {len(valid_stocks)}개")

    # 실제 종목당 배분 재계산
    actual_allocation = self.initial_capital / len(valid_stocks)
    print(f"💵 실제 종목당 배분: ${actual_allocation:,.2f}")

    # 포트폴리오 백테스트 실행
    portfolio_result = self._execute_portfolio_backtest(stock_data,
                                                        valid_stocks,
                                                        actual_allocation)

    return portfolio_result

  def _execute_portfolio_backtest(self, stock_data: Dict,
      valid_stocks: List[str], allocation_per_stock: float) -> Dict:
    """포트폴리오 백테스트 로직 실행"""
    # 모든 날짜 통합 (교집합)
    all_dates = None
    for symbol in valid_stocks:
      if all_dates is None:
        all_dates = set(stock_data[symbol].index)
      else:
        all_dates = all_dates.intersection(set(stock_data[symbol].index))

    all_dates = sorted(list(all_dates))

    if not all_dates:
      print("❌ 공통 거래일이 없습니다.")
      return {}

    print(f"📅 공통 거래일: {len(all_dates)}일")

    # 포트폴리오 상태 초기화
    portfolio_state = {}
    for symbol in valid_stocks:
      portfolio_state[symbol] = {
        'cash': allocation_per_stock,
        'shares': 0,
        'position': 0,  # 0: 노포지션, 1: 50%, 2: 100%
        'trades': []
      }

    # 포트폴리오 전체 기록
    portfolio_history = []
    total_trades = []

    print(f"\n⚡ 포트폴리오 백테스트 실행 중...")

    for i, date in enumerate(all_dates):
      if (i + 1) % 50 == 0:
        print(
            f"진행률: {i + 1}/{len(all_dates)} ({(i + 1) / len(all_dates) * 100:.1f}%)")

      total_portfolio_value = 0
      total_cash = 0
      total_stock_value = 0
      daily_trades = []

      # 각 종목별 처리
      for symbol in valid_stocks:
        try:
          data = stock_data[symbol]
          if date not in data.index:
            continue

          row = data.loc[date]
          current_price = row['Close']
          state = portfolio_state[symbol]

          # 매수 신호
          if row['Buy_Signal'] and state['position'] == 0:
            shares = state['cash'] / current_price
            state['shares'] = shares
            state['position'] = 2

            trade = {
              'date': date,
              'symbol': symbol,
              'action': 'BUY',
              'price': current_price,
              'shares': shares,
              'value': state['cash']
            }
            state['trades'].append(trade)
            daily_trades.append(trade)
            state['cash'] = 0  # 전액 투자

          # 50% 익절
          elif row['Sell_50_Signal'] and state['position'] == 2:
            sell_shares = state['shares'] * 0.5
            sell_value = sell_shares * current_price
            state['cash'] += sell_value
            state['shares'] -= sell_shares
            state['position'] = 1

            trade = {
              'date': date,
              'symbol': symbol,
              'action': 'SELL_50%',
              'price': current_price,
              'shares': sell_shares,
              'value': sell_value
            }
            state['trades'].append(trade)
            daily_trades.append(trade)

          # 전량 매도
          elif row['Sell_All_Signal'] and state['position'] > 0:
            sell_value = state['shares'] * current_price
            state['cash'] += sell_value

            trade = {
              'date': date,
              'symbol': symbol,
              'action': 'SELL_ALL',
              'price': current_price,
              'shares': state['shares'],
              'value': sell_value
            }
            state['trades'].append(trade)
            daily_trades.append(trade)

            state['shares'] = 0
            state['position'] = 0

          # 현재 자산가치 계산
          stock_value = state['shares'] * current_price
          total_value = state['cash'] + stock_value

          total_cash += state['cash']
          total_stock_value += stock_value
          total_portfolio_value += total_value

        except Exception as e:
          # 개별 종목 오류는 무시하고 계속
          continue

      # 포트폴리오 일일 기록
      portfolio_history.append({
        'date': date,
        'total_value': total_portfolio_value,
        'total_cash': total_cash,
        'total_stock_value': total_stock_value,
        'daily_trades': daily_trades
      })

      if daily_trades:
        total_trades.extend(daily_trades)

    # 마지막 포지션 청산
    final_date = all_dates[-1]
    final_total_value = 0

    for symbol in valid_stocks:
      try:
        if portfolio_state[symbol]['shares'] > 0:
          final_price = stock_data[symbol].loc[final_date]['Close']
          final_sell_value = portfolio_state[symbol]['shares'] * final_price
          portfolio_state[symbol]['cash'] += final_sell_value
          portfolio_state[symbol]['shares'] = 0

        final_total_value += portfolio_state[symbol]['cash']
      except:
        continue

    # 결과 계산
    total_return = (
                       final_total_value - self.initial_capital) / self.initial_capital * 100
    total_profit = final_total_value - self.initial_capital

    # 포트폴리오 통계 계산
    portfolio_stats = self._calculate_portfolio_stats(portfolio_history,
                                                      total_trades,
                                                      final_total_value)

    result = {
      'initial_capital': self.initial_capital,
      'final_value': final_total_value,
      'total_profit': total_profit,
      'total_return': total_return,
      'valid_stocks': valid_stocks,
      'portfolio_history': portfolio_history,
      'total_trades': total_trades,
      'portfolio_state': portfolio_state,
      **portfolio_stats
    }

    # 결과 출력
    self._print_portfolio_results(result)

    return result

  def _calculate_portfolio_stats(self, portfolio_history: List[Dict],
      total_trades: List[Dict], final_value: float) -> Dict:
    """포트폴리오 통계 계산"""
    if not portfolio_history:
      return {}

    # 자산 곡선 분석
    values = [p['total_value'] for p in portfolio_history]

    # 최대 낙폭 계산
    peak = values[0]
    max_drawdown = 0

    for value in values:
      if value > peak:
        peak = value
      drawdown = (peak - value) / peak * 100
      if drawdown > max_drawdown:
        max_drawdown = drawdown

    # 변동성 계산 (일일 수익률)
    daily_returns = []
    for i in range(1, len(values)):
      daily_return = (values[i] - values[i - 1]) / values[i - 1] * 100
      daily_returns.append(daily_return)

    volatility = np.std(daily_returns) if daily_returns else 0
    avg_daily_return = np.mean(daily_returns) if daily_returns else 0

    # 샤프 비율 (연율화)
    if volatility > 0:
      sharpe_ratio = (avg_daily_return * 252) / (
          volatility * np.sqrt(252))  # 252 거래일
    else:
      sharpe_ratio = 0

    # 거래 통계
    total_trade_count = len(total_trades)
    buy_trades = len([t for t in total_trades if t['action'] == 'BUY'])
    sell_trades = len(
        [t for t in total_trades if t['action'] in ['SELL_50%', 'SELL_ALL']])

    return {
      'max_drawdown': max_drawdown,
      'volatility': volatility,
      'sharpe_ratio': sharpe_ratio,
      'total_trade_count': total_trade_count,
      'buy_trades': buy_trades,
      'sell_trades': sell_trades,
      'avg_daily_return': avg_daily_return
    }

  def _print_portfolio_results(self, result: Dict):
    """포트폴리오 결과 출력"""
    print(f"\n{'=' * 80}")
    print(f"💼 통합 포트폴리오 백테스트 최종 결과")
    print(f"{'=' * 80}")

    # 기본 수익 정보
    print(f"💰 초기 자금:        ${result['initial_capital']:>12,.2f}")
    print(f"💵 최종 자산:        ${result['final_value']:>12,.2f}")
    print(f"💲 총 수익금:        ${result['total_profit']:>12,.2f}")
    print(f"📈 총 수익률:        {result['total_return']:>12.2f}%")

    # 연율화 수익률 계산 (포트폴리오 기간 기반)
    if result.get('portfolio_history'):
      portfolio_days = len(result['portfolio_history'])
      if portfolio_days > 0:
        annualized_return = ((result['final_value'] / result[
          'initial_capital']) ** (365 / portfolio_days) - 1) * 100
        print(f"📊 연율화 수익률:    {annualized_return:>12.2f}%")
        print(f"📅 투자 기간:        {portfolio_days:>12d}일")

    # 성과 평가
    if result['total_return'] > 20:
      evaluation = "🌟 우수"
      evaluation_detail = "매우 성공적인 투자 성과"
    elif result['total_return'] > 10:
      evaluation = "✅ 양호"
      evaluation_detail = "양호한 투자 성과"
    elif result['total_return'] > 0:
      evaluation = "📈 수익"
      evaluation_detail = "수익을 달성한 투자"
    else:
      evaluation = "📉 손실"
      evaluation_detail = "손실을 기록한 투자"

    print(f"🏆 성과 평가:        {evaluation:>12s}")
    print(f"📝 평가 상세:        {evaluation_detail}")

    print(f"\n" + "-" * 80)
    print(f"📊 포트폴리오 운용 통계")
    print(f"-" * 80)
    print(f"📊 유효 종목 수:     {len(result['valid_stocks']):>12d}개")
    print(
        f"💵 종목당 초기배분:  ${result['initial_capital'] / len(result['valid_stocks']):>12,.2f}")
    print(f"🔢 총 거래 횟수:     {result['total_trade_count']:>12d}회")
    print(f"📊 매수 거래:        {result['buy_trades']:>12d}회")
    print(f"📊 매도 거래:        {result['sell_trades']:>12d}회")
    print(f"📉 최대 낙폭:        {result['max_drawdown']:>12.2f}%")
    print(f"📊 변동성:          {result['volatility']:>12.2f}%")
    print(f"⚖️ 샤프 비율:       {result['sharpe_ratio']:>12.2f}")
    print(f"📈 평균 일수익률:    {result['avg_daily_return']:>12.4f}%")

    print(f"{'=' * 80}")

  def plot_portfolio_performance(self, result: Dict, save_path: str = None):
    """포트폴리오 성과 시각화"""
    if not result or not result['portfolio_history']:
      print("❌ 포트폴리오 결과가 없습니다.")
      return

    # 한글 폰트 재설정 (차트 생성 전)
    setup_korean_font()

    portfolio_history = result['portfolio_history']
    dates = [p['date'] for p in portfolio_history]
    total_values = [p['total_value'] for p in portfolio_history]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
    fig.suptitle('통합 포트폴리오 성과 분석', fontsize=16, fontweight='bold')

    # 1. 포트폴리오 가치 곡선
    ax1.plot(dates, total_values, 'darkgreen', linewidth=2, label='포트폴리오 가치')
    ax1.axhline(y=result['initial_capital'], color='gray', linestyle='--',
                alpha=0.7, label='초기자본')

    # 수익률 표시 (한글 깨짐 방지)
    final_return = result['total_return']
    final_profit = result['total_profit']
    info_text = f'Total Return: {final_return:.2f}%\nProfit: ${final_profit:,.0f}'
    ax1.text(0.02, 0.85, info_text, transform=ax1.transAxes, fontsize=12,
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

    ax1.set_title('Portfolio Value Curve', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)

    # Y축 포맷팅 (달러 표시)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    # 2. 일일 수익률 분포
    daily_returns = []
    for i in range(1, len(total_values)):
      daily_return = (total_values[i] - total_values[i - 1]) / total_values[
        i - 1] * 100
      daily_returns.append(daily_return)

    if daily_returns:
      ax2.hist(daily_returns, bins=50, alpha=0.7, color='steelblue',
               edgecolor='black')
      ax2.axvline(x=0, color='red', linestyle='--', alpha=0.7,
                  label='Break-even')
      mean_return = np.mean(daily_returns)
      ax2.axvline(x=mean_return, color='green', linestyle='-', alpha=0.7,
                  label=f'Average: {mean_return:.3f}%')

      ax2.set_title('Daily Return Distribution', fontsize=14)
      ax2.set_xlabel('Daily Return (%)')
      ax2.set_ylabel('Frequency')
      ax2.legend()
      ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
      try:
        # save_path가 절대 경로가 아니면 charts_dir와 결합
        if not os.path.isabs(save_path):
          save_path = os.path.join(self.charts_dir, save_path)

        # 디렉토리 확인 및 생성
        chart_dir = os.path.dirname(save_path)
        os.makedirs(chart_dir, exist_ok=True)

        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"📊 포트폴리오 차트 저장: {os.path.relpath(save_path)}")
      except Exception as e:
        print(f"⚠️ 차트 저장 중 오류: {e}")
        # 기본 옵션으로 재시도
        try:
          filename = os.path.basename(
              save_path) if save_path else f"portfolio_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
          fallback_path = os.path.join(self.charts_dir, filename)
          plt.savefig(fallback_path, dpi=200, bbox_inches='tight')
          plt.close()
          print(f"📊 포트폴리오 차트 저장 완료 (대안 경로): {os.path.relpath(fallback_path)}")
        except Exception as e2:
          print(f"❌ 차트 저장 실패: {e2}")
          plt.close()
    else:
      plt.show()

  def save_portfolio_results(self, result: Dict, filename: str = None):
    """포트폴리오 결과를 CSV로 저장"""
    if not result or not result['portfolio_history']:
      print("❌ 저장할 포트폴리오 결과가 없습니다.")
      return None

    if filename is None:
      timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
      filename = f'portfolio_backtest_{timestamp}.csv'

    # 포트폴리오 히스토리를 DataFrame으로 변환
    history_data = []
    for record in result['portfolio_history']:
      # 일일 수익률 계산
      daily_return_pct = 0
      if history_data:
        prev_value = history_data[-1]['Total_Value']
        daily_return_pct = (record[
                              'total_value'] - prev_value) / prev_value * 100

      history_data.append({
        'Date': record['date'].strftime('%Y-%m-%d'),
        'Total_Value': record['total_value'],
        'Total_Cash': record['total_cash'],
        'Total_Stock_Value': record['total_stock_value'],
        'Daily_Return_Pct': daily_return_pct,
        'Trade_Count': len(record.get('daily_trades', []))
      })

    df = pd.DataFrame(history_data)

    # 파일 경로 설정
    output_path = os.path.join(self.results_dir, filename)

    try:
      df.to_csv(output_path, index=False, encoding='utf-8')
      print(f"💾 포트폴리오 결과 저장: {os.path.relpath(output_path)}")
      return filename
    except Exception as e:
      print(f"❌ 포트폴리오 결과 저장 실패: {e}")
      # 현재 디렉토리에 저장 시도
      try:
        current_dir_path = os.path.join(os.getcwd(), filename)
        df.to_csv(current_dir_path, index=False, encoding='utf-8')
        print(f"💾 포트폴리오 결과 저장 (대안 경로): {filename}")
        return filename
      except Exception as e2:
        print(f"❌ 대안 저장도 실패: {e2}")
        return None

  def run_multi_stock_backtest(self, start_date: str, end_date: str, max_stocks: int = 20) -> pd.DataFrame:
    """다중 종목 백테스트 (개선된 버전)"""
    results = []
    stocks_to_test = self.top50_stocks[:max_stocks]
    failed_stocks = []

    print(f"🔍 {len(stocks_to_test)}개 종목 백테스트 시작...")
    print(f"📅 기간: {start_date} ~ {end_date}")
    print(f"⚠️  중단하려면 Ctrl+C를 누르세요")
    print("-" * 80)

    try:
      for i, symbol in enumerate(stocks_to_test):
        print(f"진행: {i + 1:2d}/{len(stocks_to_test)} - {symbol:5s}", end=" ... ")

        retry_count = 0
        max_retries = 3
        success = False

        # 재시도 로직 추가
        while retry_count < max_retries and not success:
          try:
            result = self.run_single_backtest(symbol, start_date, end_date)
            if result:
              results.append(result)
              print(f"완료 (수익률: {result['total_return']:6.2f}%)")
              success = True
            else:
              print(f"데이터 부족", end="")
              if retry_count < max_retries - 1:
                print(f" - 재시도 {retry_count + 1}/{max_retries}", end="")
                time.sleep(1)  # 1초 대기 후 재시도
              retry_count += 1

          except KeyboardInterrupt:
            print(f"\n⏹️  백테스트가 중단되었습니다.")
            raise
          except Exception as e:
            print(f"오류: {str(e)[:30]}...", end="")
            if retry_count < max_retries - 1:
              print(f" - 재시도 {retry_count + 1}/{max_retries}", end="")
              time.sleep(1)
            retry_count += 1

        if not success:
          failed_stocks.append(symbol)
          print(" - 최종 실패")

        # API 제한 방지를 위한 적절한 대기
        if i < len(stocks_to_test) - 1:  # 마지막이 아니면
          time.sleep(0.1)  # 100ms 대기

        # 진행률 요약 (매 10개마다)
        if (i + 1) % 10 == 0:
          success_count = len(results)
          print(f"\n📊 중간 요약: {success_count}/{i+1} 성공 ({success_count/(i+1)*100:.1f}%)")
          print("-" * 80)

    except KeyboardInterrupt:
      print(f"\n⏹️  다중 종목 백테스트가 중단되었습니다.")

    # 최종 결과 요약
    print(f"\n" + "=" * 80)
    print(f"📊 백테스트 완료 요약")
    print(f"=" * 80)
    print(f"✅ 성공: {len(results)}개 종목")
    print(f"❌ 실패: {len(failed_stocks)}개 종목")
    print(f"📈 성공률: {len(results)/len(stocks_to_test)*100:.1f}%")

    if failed_stocks:
      print(f"\n❌ 실패한 종목들:")
      for i, symbol in enumerate(failed_stocks):
        print(f"   {i+1}. {symbol}")
      print(f"\n💡 실패 원인:")
      print("   - 데이터 부족 (상장 기간이 짧거나 거래 정지)")
      print("   - 네트워크 오류 (일시적 연결 문제)")
      print("   - API 제한 (Yahoo Finance 제한)")

    if not results:
      print("\n❌ 분석 가능한 종목이 없습니다.")
      return pd.DataFrame()

    # DataFrame 변환
    df_results = pd.DataFrame([
      {
        'Symbol': r['symbol'],
        'Initial_Capital($)': f"${self.initial_capital:,.0f}",
        'Final_Value($)': f"${r['final_value']:,.0f}",
        'Profit($)': f"${r['final_value'] - self.initial_capital:,.0f}",
        'Total_Return(%)': round(r['total_return'], 2),
        'Win_Rate(%)': round(r['win_rate'], 2),
        'Total_Trades': r['total_trades'],
        'Winning_Trades': r['winning_trades'],
        'Avg_Profit(%)': round(r['avg_profit'], 2),
        'Avg_Loss(%)': round(r['avg_loss'], 2),
        'Profit_Factor': round(r['profit_factor'], 2),
        'Max_Drawdown(%)': round(r['max_drawdown'], 2),
        'Test_Days': r.get('test_period_days', 0)
      }
      for r in results
    ])

    return df_results.sort_values('Total_Return(%)', ascending=False)

  # ===================================================================================
  # 종합 분석
  # ===================================================================================

  def run_comprehensive_analysis(self, start_date: str, end_date: str,
      max_stocks: int = 20,
      detailed_analysis: str = "top5", save_charts: bool = True) -> Dict:
    """종합 분석 실행"""
    print("=" * 80)
    print("🚀 변동성 폭파 볼린저 밴드 종합 분석")
    print("=" * 80)

    # 1. 다중 종목 백테스트
    results_df = self.run_multi_stock_backtest(start_date, end_date, max_stocks)

    if results_df.empty:
      return {}

    # 2. 요약 통계 출력
    self._print_summary_statistics(results_df)

    # 3. 리스크 분석
    self._print_risk_analysis(results_df)

    # 4. 결과 저장
    self.save_results_to_csv(results_df)

    # 5. 투자 리포트 생성
    self._save_investment_report(results_df, start_date, end_date)

    # 6. 상세 분석
    detailed_results = []
    if detailed_analysis != "none":
      symbols_to_analyze = self._select_analysis_symbols(results_df,
                                                         detailed_analysis)
      if symbols_to_analyze:
        print(f"\n📊 상세 분석 시작: {len(symbols_to_analyze)}개 종목")
        detailed_results = self._run_detailed_analysis(symbols_to_analyze,
                                                       start_date, end_date,
                                                       save_charts)

    return {
      'summary_results': results_df,
      'detailed_results': detailed_results,
      'statistics': self._calculate_summary_stats(results_df)
    }

  def _select_analysis_symbols(self, results_df: pd.DataFrame, mode: str) -> \
      List[str]:
    """분석할 종목 선택"""
    if mode == "top3":
      return results_df.head(3)['Symbol'].tolist()
    elif mode == "top5":
      return results_df.head(5)['Symbol'].tolist()
    elif mode == "positive":
      return results_df[results_df['Total_Return(%)'] > 0]['Symbol'].tolist()
    elif mode == "all":
      return results_df['Symbol'].tolist()
    else:
      return []

  def _run_detailed_analysis(self, symbols: List[str], start_date: str,
      end_date: str, save_charts: bool = True) -> List[Dict]:
    """상세 분석 실행"""
    detailed_results = []

    # 차트 저장 설정
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if save_charts:
      print(f"📁 차트 저장 디렉토리: {os.path.relpath(self.charts_dir)}/")

    for i, symbol in enumerate(symbols):
      print(f"\n📈 상세 분석 {i + 1}/{len(symbols)}: {symbol}")
      print("-" * 50)

      try:
        result = self.run_single_backtest(symbol, start_date, end_date)
        if result:
          # 차트 생성 (수정된 저장 방식)
          if save_charts:
            filename = f"{symbol}_analysis_{timestamp}.png"  # 파일명만 전달
            self._create_analysis_chart(result, save_path=filename)
          else:
            self._create_analysis_chart(result, show_chart=True)

          # 결과 출력
          self._print_detailed_results(result)
          detailed_results.append(result)
        else:
          print(f"❌ {symbol} 분석 실패")

      except Exception as e:
        print(f"❌ {symbol} 분석 중 오류: {e}")

    if save_charts and detailed_results:
      print(
          f"\n📊 총 {len(detailed_results)}개 차트가 {os.path.relpath(self.charts_dir)}/ 디렉토리에 저장되었습니다.")

    return detailed_results

  # ===================================================================================
  # 시각화
  # ===================================================================================

  def _create_analysis_chart(self, result: Dict, save_path: str = None,
      show_chart: bool = False):
    """분석 차트 생성"""
    data = result['data']
    trades = result['trades']
    equity_curve = result['equity_curve']
    symbol = result['symbol']

    fig, axes = plt.subplots(4, 1, figsize=(15, 12))
    fig.suptitle(f'{symbol} - 변동성 폭파 볼린저 밴드 전략 분석', fontsize=16,
                 fontweight='bold')

    # 1. 주가 & 볼린저 밴드
    ax1 = axes[0]
    ax1.plot(data.index, data['Close'], 'k-', linewidth=1.5, label='종가')
    ax1.plot(data.index, data['Upper_Band'], 'r--', alpha=0.7, label='상단밴드')
    ax1.plot(data.index, data['SMA'], 'b-', alpha=0.7, label='중간밴드')
    ax1.plot(data.index, data['Lower_Band'], 'g--', alpha=0.7, label='하단밴드')
    ax1.fill_between(data.index, data['Upper_Band'], data['Lower_Band'],
                     alpha=0.1, color='gray')

    # 매매 신호 표시
    buy_signals = [t for t in trades if t['action'] == 'BUY']
    sell_50_signals = [t for t in trades if t['action'] == 'SELL_50%']
    sell_all_signals = [t for t in trades if t['action'] == 'SELL_ALL']

    if buy_signals:
      dates = [t['date'] for t in buy_signals]
      prices = [t['price'] for t in buy_signals]
      ax1.scatter(dates, prices, color='green', marker='^', s=100, zorder=5,
                  label='매수')

    if sell_50_signals:
      dates = [t['date'] for t in sell_50_signals]
      prices = [t['price'] for t in sell_50_signals]
      ax1.scatter(dates, prices, color='orange', marker='v', s=100, zorder=5,
                  label='50% 매도')

    if sell_all_signals:
      dates = [t['date'] for t in sell_all_signals]
      prices = [t['price'] for t in sell_all_signals]
      ax1.scatter(dates, prices, color='red', marker='v', s=100, zorder=5,
                  label='전량매도')

    ax1.set_title('주가 & 볼린저밴드 & 매매신호', fontsize=12)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. RSI
    ax2 = axes[1]
    ax2.plot(data.index, data['RSI'], 'purple', linewidth=1.5, label='RSI')
    ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='과매수 (70)')
    ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='과매도 (30)')
    ax2.fill_between(data.index, 70, 100, alpha=0.2, color='red')
    ax2.fill_between(data.index, 0, 30, alpha=0.2, color='green')
    ax2.set_title('RSI (상대강도지수)', fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 변동성 지표
    ax3 = axes[2]
    ax3.plot(data.index, data['Band_Width'], 'brown', linewidth=1.5,
             label='밴드폭')
    squeeze_data = data[data['Volatility_Squeeze']]
    if not squeeze_data.empty:
      ax3.scatter(squeeze_data.index, squeeze_data['Band_Width'], color='red',
                  s=20, alpha=0.7, label='변동성 압축')
    ax3.set_title('변동성 지표 (밴드폭 & 압축구간)', fontsize=12)
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. 자산 곡선
    ax4 = axes[3]
    if equity_curve:
      dates = [eq['date'] for eq in equity_curve]
      values = [eq['portfolio_value'] for eq in equity_curve]
      ax4.plot(dates, values, 'darkgreen', linewidth=2, label='포트폴리오 가치')
      ax4.axhline(y=self.initial_capital, color='gray', linestyle='--',
                  alpha=0.7, label='초기자본')

      final_return = ((values[
                         -1] - self.initial_capital) / self.initial_capital) * 100
      final_profit = values[-1] - self.initial_capital

      info_text = f'총 수익률: {final_return:.2f}%\n총 수익금: ${final_profit:,.0f}'
      ax4.text(0.02, 0.85, info_text, transform=ax4.transAxes, fontsize=11,
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

    ax4.set_title('포트폴리오 자산 곡선', fontsize=12)
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # X축 레이블 회전
    for ax in axes:
      ax.tick_params(axis='x', rotation=45)

    plt.tight_layout()

    # 저장 또는 출력
    if save_path:
      try:
        # save_path가 절대 경로가 아니면 charts_dir와 결합
        if not os.path.isabs(save_path):
          save_path = os.path.join(self.charts_dir, save_path)

        # 디렉토리 확인 및 생성
        chart_dir = os.path.dirname(save_path)
        os.makedirs(chart_dir, exist_ok=True)

        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"📊 차트 저장: {os.path.relpath(save_path)}")
      except Exception as e:
        print(f"❌ 차트 저장 실패: {e}")
        # 기본 경로에 저장 시도
        try:
          filename = os.path.basename(save_path)
          fallback_path = os.path.join(self.charts_dir, filename)
          plt.savefig(fallback_path, dpi=200, bbox_inches='tight')
          plt.close()
          print(f"📊 차트 저장 (대안 경로): {os.path.relpath(fallback_path)}")
        except Exception as e2:
          print(f"❌ 대안 차트 저장도 실패: {e2}")
          plt.close()
    elif show_chart:
      plt.show()
    else:
      plt.close()

  # ===================================================================================
  # 결과 출력 및 저장
  # ===================================================================================

  def _print_summary_statistics(self, results_df: pd.DataFrame):
    """요약 통계 출력"""
    print(f"\n📊 백테스트 결과 요약:")
    print("-" * 140)
    print(results_df.to_string(index=False))

    print(f"\n📈 전체 통계:")
    print("-" * 70)

    total_stocks = len(results_df)
    profitable_stocks = len(results_df[results_df['Total_Return(%)'] > 0])
    avg_return = results_df['Total_Return(%)'].mean()
    avg_win_rate = results_df['Win_Rate(%)'].mean()
    avg_drawdown = results_df['Max_Drawdown(%)'].mean()

    # 수익금 통계
    profits = []
    for profit_str in results_df['Profit($)']:
      profit_val = float(profit_str.replace('$', '').replace(',', ''))
      profits.append(profit_val)

    avg_profit = np.mean(profits) if profits else 0

    best = results_df.iloc[0]
    worst = results_df.iloc[-1]

    print(f"💰 초기 자금:     ${self.initial_capital:>10,.2f}")
    print(f"📊 분석 종목 수:   {total_stocks:>10d}개")
    print(
      f"✅ 수익 종목 수:   {profitable_stocks:>10d}개 ({profitable_stocks / total_stocks * 100:.1f}%)")
    print(f"📈 평균 수익률:   {avg_return:>10.2f}%")
    print(f"💲 평균 수익금:   ${avg_profit:>10,.2f}")
    print(f"🎯 평균 승률:     {avg_win_rate:>10.2f}%")
    print(f"📉 평균 최대낙폭: {avg_drawdown:>10.2f}%")
    print(f"🏆 최고 수익:     {best['Symbol']} ({best['Total_Return(%)']:6.2f}%)")
    print(f"📉 최저 수익:     {worst['Symbol']} ({worst['Total_Return(%)']:6.2f}%)")

    # 포트폴리오 시뮬레이션
    portfolio_return = avg_return
    portfolio_profit = (portfolio_return / 100) * self.initial_capital

    print(f"\n💼 포트폴리오 시뮬레이션 (동일 비중 투자):")
    print(f"   예상 수익률:    {portfolio_return:>10.2f}%")
    print(f"   예상 수익금:    ${portfolio_profit:>10,.2f}")
    print(f"   예상 최종자산:  ${self.initial_capital + portfolio_profit:>10,.2f}")

  def _print_detailed_results(self, result: Dict):
    """상세 결과 출력"""
    symbol = result['symbol']
    final_value = result['final_value']
    total_profit = final_value - self.initial_capital

    print(f"\n{'=' * 70}")
    print(f"📊 {symbol} 백테스트 상세 결과")
    print(f"{'=' * 70}")
    print(f"💰 초기 자금:      ${self.initial_capital:>10,.2f}")
    print(f"💵 최종 자산:      ${final_value:>10,.2f}")
    print(f"💲 총 수익금:      ${total_profit:>10,.2f}")
    print(f"📈 총 수익률:      {result['total_return']:>10.2f}%")
    print(f"🎯 승률:          {result['win_rate']:>10.2f}%")
    print(f"🔢 총 거래 횟수:   {result['total_trades']:>10d}회")
    print(f"✅ 수익 거래:      {result['winning_trades']:>10d}회")
    print(f"📊 평균 수익:      {result['avg_profit']:>10.2f}%")
    print(f"📉 평균 손실:      {result['avg_loss']:>10.2f}%")
    print(f"⚖️ 손익비:        {result['profit_factor']:>10.2f}")
    print(f"📉 최대 낙폭:      {result['max_drawdown']:>10.2f}%")

    # 연율화 수익률
    if result.get('test_period_days', 0) > 0:
      test_days = result['test_period_days']
      annualized_return = ((final_value / self.initial_capital) ** (
          365 / test_days) - 1) * 100
      print(f"📅 테스트 기간:    {test_days:>10d}일")
      print(f"📊 연율화 수익률:  {annualized_return:>10.2f}%")

    # 성과 평가
    if result['total_return'] > 20:
      evaluation = "🌟 우수"
    elif result['total_return'] > 10:
      evaluation = "✅ 양호"
    elif result['total_return'] > 0:
      evaluation = "📈 수익"
    else:
      evaluation = "📉 손실"
    print(f"🏆 성과 평가:      {evaluation:>10s}")

    # 거래 내역 (최근 5개)
    trades = result['completed_trades'][:5]
    if trades:
      print(f"\n📋 최근 거래 내역 (최대 5개):")
      print("-" * 70)
      for i, trade in enumerate(trades):
        status = "✅ 수익" if trade['is_winning'] else "❌ 손실"
        profit_amount = (trade['profit_pct'] / 100) * self.initial_capital * 0.5
        print(f"{i + 1}. {trade['entry_date'].strftime('%Y-%m-%d')} → "
              f"{trade['exit_date'].strftime('%Y-%m-%d')}: "
              f"{trade['profit_pct']:6.2f}% (${profit_amount:,.0f}) {status}")

    print(f"{'=' * 70}")

  def _print_risk_analysis(self, results_df: pd.DataFrame):
    """리스크 분석 결과 출력"""
    if results_df.empty:
      return

    returns = results_df['Total_Return(%)'].values

    # 기본 통계
    mean_return = np.mean(returns)
    std_return = np.std(returns)

    # 리스크 지표
    sharpe_ratio = mean_return / std_return if std_return > 0 else 0
    var_95 = np.percentile(returns, 5)
    max_loss = np.min(returns)
    success_rate = len(returns[returns > 0]) / len(returns) * 100

    # 리스크 등급
    if std_return <= 10:
      risk_grade = "🟢 낮음"
    elif std_return <= 20:
      risk_grade = "🟡 보통"
    else:
      risk_grade = "🔴 높음"

    print(f"\n📊 리스크 분석:")
    print("-" * 50)
    print(f"📈 평균 수익률:    {mean_return:8.2f}%")
    print(f"📊 변동성:        {std_return:8.2f}%")
    print(f"⚖️ 샤프 비율:     {sharpe_ratio:8.2f}")
    print(f"⚠️ 95% VaR:      {var_95:8.2f}%")
    print(f"💥 최대 손실:     {max_loss:8.2f}%")
    print(f"🎯 성공 확률:     {success_rate:8.1f}%")
    print(f"🚦 리스크 등급:   {risk_grade}")

    # 투자 가이드
    print(f"\n💡 투자 가이드:")
    if sharpe_ratio > 1.0:
      print("   ✅ 우수한 위험 대비 수익률")
    elif sharpe_ratio > 0.5:
      print("   ⚖️ 적정한 위험 대비 수익률")
    else:
      print("   ⚠️ 리스크 대비 수익률 낮음")

    if success_rate > 70:
      print("   🎯 높은 성공 확률")
    elif success_rate > 50:
      print("   📊 보통 성공 확률")
    else:
      print("   ⚠️ 낮은 성공 확률")

  def _save_investment_report(self, results_df: pd.DataFrame, start_date: str,
      end_date: str):
    """투자 리포트 저장"""
    if results_df.empty:
      print("❌ 저장할 리포트 데이터가 없습니다.")
      return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'investment_report_{timestamp}.txt'

    # 기본 통계 계산
    total_stocks = len(results_df)
    profitable_stocks = len(results_df[results_df['Total_Return(%)'] > 0])
    avg_return = results_df['Total_Return(%)'].mean()

    # 성과 분석
    excellent_stocks = len(results_df[results_df['Total_Return(%)'] >= 20])
    good_stocks = len(results_df[(results_df['Total_Return(%)'] >= 10) &
                                 (results_df['Total_Return(%)'] < 20)])

    # 포트폴리오 추천
    top_3 = results_df.head(3)
    safe_picks = results_df[(results_df['Total_Return(%)'] > 0) &
                            (results_df['Max_Drawdown(%)'] <= 10)].head(3)

    # 리포트 작성
    report = f"""📊 투자 분석 리포트
{'=' * 60}
📅 분석 기간: {start_date} ~ {end_date}
💰 초기 자금: ${self.initial_capital:,.2f}
⚙️ 전략 모드: {self.strategy_mode.upper()}

📈 성과 요약:
   • 분석 종목: {total_stocks}개
   • 수익 종목: {profitable_stocks}개 ({profitable_stocks / total_stocks * 100:.1f}%)
   • 평균 수익률: {avg_return:.2f}%
   
🏆 성과 등급별 분포:
   • 우수 (20%+): {excellent_stocks}개
   • 양호 (10-20%): {good_stocks}개
   • 수익 (0-10%): {profitable_stocks - excellent_stocks - good_stocks}개

🎯 투자 추천:
"""

    # 공격적 포트폴리오
    if not top_3.empty:
      report += "\n   📈 공격적 포트폴리오 (수익률 우선):\n"
      for i, (_, row) in enumerate(top_3.iterrows()):
        profit_amount = (row['Total_Return(%)'] / 100) * self.initial_capital
        report += f"      {i + 1}. {row['Symbol']}: {row['Total_Return(%)']}% (${profit_amount:,.0f})\n"

    # 안정적 포트폴리오
    if not safe_picks.empty:
      report += "\n   🛡️ 안정적 포트폴리오 (리스크 최소화):\n"
      for i, (_, row) in enumerate(safe_picks.iterrows()):
        profit_amount = (row['Total_Return(%)'] / 100) * self.initial_capital
        report += f"      {i + 1}. {row['Symbol']}: {row['Total_Return(%)']}% (낙폭: {row['Max_Drawdown(%)']}%)\n"

    # 투자 전략 추천
    if avg_return > 15:
      strategy_advice = "💪 강세장 전략: 적극적 투자 추천"
    elif avg_return > 5:
      strategy_advice = "⚖️ 균형 전략: 분산 투자 추천"
    else:
      strategy_advice = "🛡️ 보수적 전략: 신중한 투자 필요"

    report += f"\n💡 추천 투자 전략: {strategy_advice}\n"

    # 주의사항
    report += f"""
⚠️ 투자 주의사항:
   • 과거 성과는 미래 수익을 보장하지 않습니다
   • 분산 투자를 통해 리스크를 관리하세요
   • 손실 허용 범위 내에서 투자하세요
   • 정기적인 포트폴리오 리밸런싱을 고려하세요

📊 사용된 전략 파라미터:
   • 볼린저 밴드: {self.bb_period}일, {self.bb_std_multiplier}σ
   • RSI 임계값: {self.rsi_overbought}
   • 변동성 압축: 하위 {self.volatility_threshold * 100}%

📞 추가 정보: 더 상세한 분석이 필요하시면 상세 모드를 실행하세요
{'=' * 60}
리포트 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # 파일 저장
    output_path = os.path.join(self.reports_dir, filename)

    try:
      with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
      print(f"📋 투자 리포트 저장: {os.path.relpath(output_path)}")
      return filename
    except Exception as e:
      print(f"❌ 리포트 저장 실패: {e}")
      # 현재 디렉토리에 저장 시도
      try:
        current_dir_path = os.path.join(os.getcwd(), filename)
        with open(current_dir_path, 'w', encoding='utf-8') as f:
          f.write(report)
        print(f"📋 투자 리포트 저장 (대안 경로): {filename}")
        return filename
      except Exception as e2:
        print(f"❌ 대안 리포트 저장도 실패: {e2}")
        return None

  def _calculate_summary_stats(self, results_df: pd.DataFrame) -> Dict:
    """요약 통계 계산"""
    return {
      'total_stocks': len(results_df),
      'profitable_stocks': len(results_df[results_df['Total_Return(%)'] > 0]),
      'average_return': results_df['Total_Return(%)'].mean(),
      'median_return': results_df['Total_Return(%)'].median(),
      'best_stock': results_df.iloc[0]['Symbol'],
      'best_return': results_df.iloc[0]['Total_Return(%)'],
      'worst_stock': results_df.iloc[-1]['Symbol'],
      'worst_return': results_df.iloc[-1]['Total_Return(%)']
    }

  def save_results_to_csv(self, results_df: pd.DataFrame, filename: str = None):
    """결과를 CSV로 저장"""
    if results_df.empty:
      print("❌ 저장할 결과가 없습니다.")
      return None

    if filename is None:
      timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
      filename = f'backtest_results_{timestamp}.csv'

    # 파일 경로 설정
    output_path = os.path.join(self.results_dir, filename)

    try:
      results_df.to_csv(output_path, index=False, encoding='utf-8')
      print(f"💾 백테스트 결과 저장: {os.path.relpath(output_path)}")
      return filename
    except Exception as e:
      print(f"❌ 백테스트 결과 저장 실패: {e}")
      # 현재 디렉토리에 저장 시도
      try:
        current_dir_path = os.path.join(os.getcwd(), filename)
        results_df.to_csv(current_dir_path, index=False, encoding='utf-8')
        print(f"💾 백테스트 결과 저장 (대안 경로): {filename}")
        return filename
      except Exception as e2:
        print(f"❌ 대안 저장도 실패: {e2}")
        return None


# ===================================================================================
# 메인 실행 함수
# ===================================================================================

def main():
  """메인 실행 함수"""
  print("🚀 변동성 폭파 볼린저 밴드 백테스트")
  print("=" * 50)

  # 초기 자금 설정
  print("💰 초기 자금 설정:")
  try:
    capital = float(input("초기 자금을 입력하세요 ($): "))
    backtest = VolatilityBollingerBacktest(initial_capital=capital)
  except ValueError:
    print("잘못된 입력입니다. 기본값 $10,000을 사용합니다.")
    backtest = VolatilityBollingerBacktest(initial_capital=10000)

  # 백테스트 기간 설정
  start_date = "2022-01-01"
  end_date = "2024-01-01"

  print(f"📅 분석 기간: {start_date} ~ {end_date}")

  # 종합 분석 실행
  results = backtest.run_comprehensive_analysis(
      start_date=start_date,
      end_date=end_date,
      max_stocks=10,
      detailed_analysis="top3",
      save_charts=True
  )

  if results:
    print(f"\n✅ 분석 완료!")

    # 투자 권장사항
    summary_results = results.get('summary_results')
    if not summary_results.empty:
      top_performers = summary_results.head(3)
      print(f"\n🏆 투자 추천 종목 (상위 3개):")
      for i, (_, row) in enumerate(top_performers.iterrows()):
        print(f"{i + 1}. {row['Symbol']}: {row['Total_Return(%)']}% 수익률")

  else:
    print(f"\n❌ 분석 실패")


if __name__ == "__main__":
  main()

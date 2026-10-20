"""프로젝트 경로 설정 (실행 위치와 무관하게 프로젝트 루트 기준)"""

import os
from datetime import datetime

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output_files')
LOG_DIR = os.path.join(OUTPUT_DIR, 'logs')


def monitor_log_path() -> str:
  """오늘 날짜의 모니터링 로그 파일 경로 (디렉토리 자동 생성)"""
  os.makedirs(LOG_DIR, exist_ok=True)
  return os.path.join(LOG_DIR, f"monitor_{datetime.now().strftime('%Y%m%d')}.log")

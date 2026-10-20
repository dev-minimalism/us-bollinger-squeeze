#!/bin/bash
# ===================================================================================
# 1. start_monitor.sh - 백그라운드 모니터링 시작 스크립트
# ===================================================================================

# start_monitor.sh

echo "🚀 변동성 폭파 모니터링 백그라운드 시작"
echo "=================================="

# 프로젝트 루트로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 로그 디렉토리 생성
mkdir -p output_files/logs

# PID 파일 경로
PID_FILE="output_files/monitor.pid"

# 이미 실행 중인지 확인
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  모니터링이 이미 실행 중입니다 (PID: $OLD_PID)"
        echo "🛑 중지하려면: ./scripts/stop_monitor.sh"
        exit 1
    else
        echo "🧹 이전 PID 파일 정리 중..."
        rm -f "$PID_FILE"
    fi
fi

# 백그라운드에서 실행
echo "📡 백그라운드 모니터링 시작..."
nohup python3 main.py --mode monitor-default > output_files/logs/nohup.out 2>&1 &
NEW_PID=$!

# PID 저장
echo "$NEW_PID" > "$PID_FILE"

echo "✅ 모니터링이 백그라운드에서 시작되었습니다!"
echo "📊 PID: $NEW_PID"
echo "📝 로그: output_files/logs/monitor_$(date +%Y%m%d).log"
echo "📄 nohup 로그: output_files/logs/nohup.out"
echo ""
echo "🔍 상태 확인: ./scripts/status_monitor.sh"
echo "🛑 중지: ./scripts/stop_monitor.sh"
echo "📋 로그 보기: tail -f output_files/logs/monitor_$(date +%Y%m%d).log"

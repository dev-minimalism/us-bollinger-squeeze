#!/bin/bash
# ===================================================================================
# 4. restart_monitor.sh - 백그라운드 모니터링 재시작 스크립트
# ===================================================================================

# restart_monitor.sh

echo "🔄 변동성 폭파 모니터링 재시작"
echo "=========================="

# 프로젝트 루트로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 현재 실행 중인 모니터링 중지
echo "1️⃣ 기존 모니터링 중지 중..."
"$SCRIPT_DIR/stop_monitor.sh"

# 잠시 대기
echo "⏳ 2초 대기 중..."
sleep 2

# 새로 시작
echo "2️⃣ 모니터링 새로 시작 중..."
"$SCRIPT_DIR/start_monitor.sh"

# G-DIAS v5 - Windows PowerShell 설치 및 실행 스크립트
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  G-DIAS v5 - 설치 및 실행" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Python 확인
Write-Host "`n[1] Python 확인 중..." -ForegroundColor Yellow
try {
    $pyVersion = python --version 2>&1
    Write-Host "    $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "    Python 없음. https://python.org 에서 설치하세요." -ForegroundColor Red
    exit 1
}

# 2. 가상환경
if (-Not (Test-Path ".\venv")) {
    Write-Host "`n[2] 가상환경 생성 중..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "`n[2] 기존 venv 사용" -ForegroundColor Green
}
& ".\venv\Scripts\Activate.ps1"

# 3. 의존성 설치
Write-Host "`n[3] 패키지 설치 중..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
Write-Host "    설치 완료" -ForegroundColor Green

# 4. 폴더 생성
Write-Host "`n[4] 폴더 준비..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path ".\models" | Out-Null
New-Item -ItemType Directory -Force -Path ".\data"   | Out-Null
New-Item -ItemType Directory -Force -Path ".\data\cache" | Out-Null

# 5. ACLED API 키 안내
Write-Host "`n[5] ACLED API 키 (선택사항)" -ForegroundColor Yellow
Write-Host "    분쟁 실시간 데이터 활성화하려면:" -ForegroundColor White
Write-Host "    1. https://developer.acleddata.com/ 에서 무료 등록" -ForegroundColor White
Write-Host "    2. 아래 명령으로 환경변수 설정:" -ForegroundColor White
Write-Host '       $env:ACLED_API_KEY="your_key"' -ForegroundColor Cyan
Write-Host '       $env:ACLED_EMAIL="your@email.com"' -ForegroundColor Cyan
Write-Host "    없으면 그냥 진행 (나머지 소스는 정상 동작)" -ForegroundColor Gray

# 6. 실시간 데이터 수집
Write-Host "`n[6] 실시간 데이터 수집 중..." -ForegroundColor Yellow
Write-Host "    소스: GDELT(15분) + World Bank + ReliefWeb + UNHCR + TI CPI" -ForegroundColor Gray
$env:PYTHONPATH = ".\src"
python src\data_collector.py
Write-Host "    데이터 수집 완료" -ForegroundColor Green

# 7. 모델 학습
Write-Host "`n[7] DSI 모델 학습 중..." -ForegroundColor Yellow
python src\train_dsi_model.py
Write-Host "    모델 학습 완료" -ForegroundColor Green

# 8. 경보 파이프라인
Write-Host "`n[8] 경보 엔진 실행..." -ForegroundColor Yellow
python src\alert_engine.py
Write-Host "    경보 분석 완료" -ForegroundColor Green

# 9. 대시보드 실행
Write-Host "`n[9] 대시보드 시작..." -ForegroundColor Cyan
Write-Host "    브라우저: http://localhost:8501" -ForegroundColor White
Write-Host "    종료: Ctrl+C`n" -ForegroundColor White
streamlit run dashboard.py

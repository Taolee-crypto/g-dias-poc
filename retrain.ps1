# G-DIAS - 모델만 다시 학습할 때 사용
# 사용법: .\retrain.ps1
# V-Dem CSV 있을 때: .\retrain.ps1 -VdemCsv "C:\path\to\V-Dem-CY-Core-v13.csv"

param(
    [string]$VdemCsv = ""
)

& ".\venv\Scripts\Activate.ps1"

$env:PYTHONPATH = ".\src"

if ($VdemCsv -ne "") {
    Write-Host "V-Dem CSV 사용: $VdemCsv" -ForegroundColor Cyan
    python src\train_dsi_model.py --vdem-csv $VdemCsv
} else {
    Write-Host "시뮬레이션 데이터로 학습" -ForegroundColor Yellow
    python src\train_dsi_model.py
}

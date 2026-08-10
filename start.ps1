# Real-Time Order Flow Indicator — Launch Scripts
# ================================================
# PowerShell — Run both services in separate windows

Write-Host "=== Real-Time Order Flow Engine ===" -ForegroundColor Cyan

# 1. Start FastAPI Backend
Write-Host "Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location 'c:\Users\beino\Desktop\ORDER-FLOW\backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

Start-Sleep -Seconds 2

# 2. Launch Flutter Windows app
Write-Host "Launching Flutter Windows desktop app..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location 'c:\Users\beino\Desktop\ORDER-FLOW\frontend'; flutter run -d windows"

Write-Host ""
Write-Host "System live! Backend: http://localhost:8000 | WebSocket: ws://localhost:8000/ws/orderflow" -ForegroundColor Cyan
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor White

@echo off
REM ============================================================
REM  YOLOv13 繼續訓練腳本 v2
REM  從 best.pt 出發，套用改善超參：lrf=0.001 + cos_lr
REM  batch=4 + imgsz=512（RTX 3050 Ti 4GB 限制）
REM
REM  使用方式（雙擊或在命令列執行）：
REM    scripts\windows\train-finetune2.bat
REM ============================================================

SET REPO=%~dp0..\..
SET BEST_PT=%REPO%\data\train_runs\rainfog_20260329_121743\weights\best.pt

echo [INFO] 專案根目錄: %REPO%
echo [INFO] 起點模型:   %BEST_PT%
echo.

IF NOT EXIST "%BEST_PT%" (
    echo [ERROR] best.pt 不存在: %BEST_PT%
    echo         請確認訓練 run 路徑正確
    pause
    exit /b 1
)

cd /d "%REPO%\backend"

echo [INFO] 啟動訓練...
echo.

SET PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

uv run python -m training.train ^
    --model "%BEST_PT%" ^
    --dataset rainfog_detection ^
    --epochs 50 ^
    --batch 4 ^
    --imgsz 512 ^
    --device 0 ^
    --workers 0 ^
    --patience 20 ^
    --lr0 0.001 ^
    --lrf 0.001 ^
    --cos-lr ^
    --name rainfog_v2

echo.
echo [INFO] 訓練結束，結果在: %REPO%\data\train_runs\rainfog_v2\
pause

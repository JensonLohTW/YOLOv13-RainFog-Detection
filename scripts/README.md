# Scripts 說明

本目錄提供 macOS 與 Windows 的常用腳本，主要覆蓋以下場景：

- 安裝前後端依賴
- 啟動 Django / FastAPI / React
- 停止前後端進程
- 啟停 Docker 基礎設施
- 初始化 MySQL 資料庫與帳號

## 目錄結構

- `scripts/macos/`：適用於 macOS / Linux shell 的 `.sh` 腳本
- `scripts/windows/`：適用於 Windows PowerShell 的 `.ps1` 腳本

## 使用建議

1. 先準備好 Python、`uv`、Node.js、npm。
2. 若要使用 Docker 腳本，請先自行安裝 Docker Desktop。
3. 若要使用 MySQL 初始化腳本，請先在本機手動安裝並啟動 MySQL。

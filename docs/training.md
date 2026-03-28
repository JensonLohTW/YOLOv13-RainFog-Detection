# YOLOv13 微調訓練指引

本文說明如何以本地資料集對 YOLOv13 預訓練權重進行微調訓練（Fine-Tuning）。

---

## 前置條件

### 1. 安裝 ultralytics 依賴

```bash
cd backend
uv sync --extra yolo
```

> **Intel Mac（x86_64）例外**：PyTorch 不提供 x86_64 macOS 的 PyPI wheel，需改用：
> ```bash
> conda install pytorch torchvision cpuonly -c pytorch
> pip install ultralytics
> ```

### 2. 確認預訓練權重已存在

```
data/models/
  yolov13n.pt   ← nano（最快，適合快速實驗）
  yolov13s.pt   ← small
  yolov13l.pt   ← large
  yolov13x.pt   ← extra-large（最準，需更多 VRAM）
```

若尚未下載，請至 [iMoonLab/yolov13 Releases](https://github.com/iMoonLab/yolov13/releases) 下載對應 `.pt` 檔案。

### 3. 準備訓練資料集

資料集放置於：

```
data/datasets/rainfog_detection/
  images/
    train/      ← 訓練圖片（.jpg / .png）
    val/        ← 驗證圖片
    test/       ← 測試圖片（可選）
  labels/
    train/      ← YOLO 格式標注（.txt，與圖片同名）
    val/
    test/
  data.yaml     ← 已建立，類別清單見下方
```

`data.yaml` 預設類別（`nc=4`）：

| class_id | 名稱 | 說明 |
|----------|------|------|
| 0 | car | 轎車 / 乘用車 |
| 1 | truck | 貨車 / 卡車 |
| 2 | bus | 公車 / 大客車 |
| 3 | person | 行人 |

> 標注格式（每行一個物件）：
> ```
> <class_id> <x_center> <y_center> <width> <height>
> ```
> 所有數值均為 0~1 的相對座標（相對圖片寬高）。

---

## 啟動訓練

### 標準啟動

```bash
./scripts/macos/train.sh
```

### 自訂訓練參數（常用範例）

```bash
# 指定模型規格與 epoch 數
./scripts/macos/train.sh --model yolov13s.pt --epochs 100

# 小記憶體環境（CPU 訓練、縮小 batch / imgsz）
./scripts/macos/train.sh --device cpu --batch 4 --imgsz 416

# GPU 訓練（指定第 0 張顯卡）
./scripts/macos/train.sh --device 0 --batch 32 --epochs 200

# 從中斷處繼續訓練
./scripts/macos/train.sh --resume

# 自訂實驗名稱（方便區分多次實驗）
./scripts/macos/train.sh --name exp_v2_s_100ep --model yolov13s.pt --epochs 100
```

### 完整參數列表

```
./scripts/macos/train.sh --help

  --model     模型規格（預設：yolov13n.pt）
  --dataset   資料集子目錄名稱（預設：rainfog_detection）
  --epochs    訓練 epoch 數（預設：50）
  --batch     批次大小（預設：16；-1 = 自動）
  --imgsz     輸入影像大小（預設：640）
  --device    訓練裝置（預設：自動；cpu / 0 / 0,1）
  --workers   DataLoader 執行緒數（預設：4）
  --patience  Early stopping 無改善上限（預設：20）
  --project   輸出根目錄（預設：data/train_runs）
  --name      實驗名稱（預設：rainfog_finetune）
  --resume    從上次中斷繼續
```

---

## 訓練輸出

訓練結束後，結果存放於：

```
data/train_runs/rainfog_finetune/
  weights/
    best.pt    ← 驗證指標最佳的權重（推薦用於推理）
    last.pt    ← 最後一個 epoch 的權重
  results.csv  ← 各 epoch 的損失與指標
  confusion_matrix.png
  ...
```

訓練完成的日誌範例：

```
2025-01-01 12:00:00 [INFO] === 訓練完成 ===
2025-01-01 12:00:00 [INFO] 結果目錄：/path/to/data/train_runs/rainfog_finetune
2025-01-01 12:00:00 [INFO] 最佳權重：/path/to/data/train_runs/rainfog_finetune/weights/best.pt
2025-01-01 12:00:00 [INFO] 最後權重：/path/to/data/train_runs/rainfog_finetune/weights/last.pt
```

### 切換至微調後的模型進行推理

訓練完成後，將 `best.pt` 複製至 `data/models/`，並更新 `backend/.env`：

```bash
cp data/train_runs/rainfog_finetune/weights/best.pt data/models/rainfog_best.pt
```

```dotenv
# backend/.env
INFERENCE_MODEL_MODE=yolov13
INFERENCE_YOLOV13_MODEL_FILE=rainfog_best.pt
```

重啟推理服務：

```bash
./scripts/macos/stop_inference.sh
./scripts/macos/start_inference.sh
```

---

## 常見錯誤排查

### 錯誤：預訓練權重不存在

```
[ERROR] 預訓練權重不存在：/path/to/data/models/yolov13n.pt
```

**解法**：至 [iMoonLab/yolov13 Releases](https://github.com/iMoonLab/yolov13/releases) 下載對應 `.pt` 並放至 `data/models/`。

---

### 錯誤：資料集設定檔不存在

```
[ERROR] 資料集設定檔不存在：.../rainfog_detection/data.yaml
```

**解法**：確認 `data/datasets/rainfog_detection/data.yaml` 存在。若整個資料集目錄為空，表示圖片與標注尚未放入。

---

### 錯誤：ultralytics 未安裝

```
RuntimeError: ultralytics 未安裝，無法進行訓練。
```

**解法**：

```bash
cd backend && uv sync --extra yolo
```

---

### 錯誤：CUDA out of memory

**解法**：縮小 `--batch` 或 `--imgsz`：

```bash
./scripts/macos/train.sh --batch 4 --imgsz 416
```

---

### 訓練中斷後繼續

```bash
./scripts/macos/train.sh --resume
```

ultralytics 會自動從 `last.pt` 恢復訓練。

---

## 路徑設定一覽

所有路徑由 `backend/inference_service/core/config.py` 的 `Settings` 管理，可透過 `backend/.env` 覆蓋：

| 環境變數 | 預設值 | 說明 |
|----------|--------|------|
| `INFERENCE_MODELS_ROOT` | `../data/models` | 預訓練權重目錄 |
| `INFERENCE_DATASETS_ROOT` | `../data/datasets` | 資料集根目錄 |
| `INFERENCE_YOLOV13_ROOT` | `../yolov13-main` | ultralytics 原始碼目錄 |
| `INFERENCE_YOLOV13_MODEL_FILE` | `yolov13n.pt` | 預設載入的模型規格 |
| `INFERENCE_TRAIN_PROJECT` | `../data/train_runs` | 訓練輸出根目錄（參考值） |
| `INFERENCE_TRAIN_NAME` | `rainfog_finetune` | 訓練執行名稱（參考值） |

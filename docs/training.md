# 模型微調實操手冊 (Training Execution Guide)

> **當前落實狀態標註**：
> 本文紀錄的終端代碼以及執行指令（或 `scripts/macos/train.sh`）均屬**離線開發階段性工具**。由於進行影像類物件特徵捕捉訓練十分耗費硬體算力，強烈建議本指令應置於掛載有 Nvidia CUDA 等強運算資源雲端硬體（如本機 GPU 主機、AWS EC2 或是 Google Colab）獨立執行。

## 1. 環境前置依賴準備
為了將 Ultralytics 套件一併配置入 Python 開發環境中，您需要於 `backend` 執行下述指令進行安裝：

```bash
cd backend
uv sync --extra yolo
```
> **排查注意**：如果是部分相容性特殊之載體 (例如無 GPU 顯卡之舊款 Intel Mac)，請放棄 `--extra yolo` ，手動採用 conda 來橋接 CPU 支援版 PyTorch，後續手動執行 `pip install ultralytics`。

## 2. 教學專用資料集結構
所有的 YOLO 格式圖片與標籤 (0.0~1.0 的相對標點法)，必須嚴格遵守以下路徑結構才可被識別套用。假定子目標資料名稱為 `rainfog_detection`：

```text
data/datasets/rainfog_detection/
├── images/
│   ├── train/  # 用於主要訓練學習之批次驗證圖 (.jpg / .png)
│   └── val/    # 用於 Epoch 巡迴驗證指標防止 Overfitting 之圖片
├── labels/
│   ├── train/  # 與圖片同名同姓的 YOLO txt 檔
│   └── val/
└── data.yaml   # 設定定義文件 (標明類別 nc，相對目錄位址，對應標籤分類)
```

## 3. 觸發微調的命令 (CLI 指引)

您可以靈活運用已經包裝好的 Ultralytics 指令，於 Terminal 輸入觸發指令啟動監聽。

```bash
# 工作目錄需切換至專案底下之 backend
uv run yolo detect train \
  data=../data/datasets/rainfog_detection/data.yaml \
  model=../data/models/yolov13n.pt \
  epochs=50 \
  imgsz=640 \
  batch=16 \
  project=../data/train_runs \
  name=rainfog_training_exp \
  device=0
```

### 命令參數科普
- `model`：作為基底繼承神經網路層的初始權重。預設以最輕量的 `yolov13n.pt` 作為入門。
- `imgsz`：自動將送入管線的圖資拉長縮放成該張量體積。
- `batch`：顯卡記憶體 VRAM 如果不夠大，請向下調整，例如改為 8 或 4。
- `device`：設定目標使用的實體設備。(`0` 代表第一顆 GPU 核心，若缺顯卡可直接指定 `cpu` 慢速驗證)。

## 4. 產出物與模型調用佈署
經過漫長的 Epoch 收斂，系統結束後自動於指定的 `project` 與 `name` 目錄 (如 `data/train_runs/rainfog_training_exp/weights/`) 封裝生成 `best.pt` 與 `last.pt`。

**上線佈署至 FastAPI 推理端**：
1. 取出表現最優良的檔案，將之複製移交系統的預設模型調用區塊：
   ```bash
   cp ../data/train_runs/rainfog_training_exp/weights/best.pt ../data/models/rainfog_best.pt
   ```
2. 更新後端 `.env` 設定檔，告知 Adapter 層改為外接：
   ```env
   # 在 .env 中強制打開真實模式與宣導檔名
   INFERENCE_MODEL_MODE=yolov13
   INFERENCE_YOLOV13_MODEL_FILE=rainfog_best.pt
   ```
3. 對應 `FastAPI` (預測模組位於 9000 端口) 執行重啟即可！

## 5. 常見訓練階段異常與排除
1. **問題：`CUDA Out of Memory` 或記憶體爆炸**
   - **處置**：減少 Mini-Batch 之運送量。將指令中的 `batch` 由 16 砍半調降至 8 甚至 4；如仍極限再微幅降低 `imgsz`。
2. **問題：`預訓練權重不存在` 或未自動下載**
   - **處置**：若開發環境網路有阻擋致使工具無法自動 fetch `yolov13n.pt` 等原廠模型，請至開源庫 [iMoonLab/yolov13](https://github.com/iMoonLab/yolov13/releases) 人工下載其基礎 `.pt` 放進您的目標位址內。
3. **問題：Loss 損失函數始終無法收斂或震盪劇烈**
   - **處置**：多半屬於 Dataset 過少或者訓練樣本的特徵失準。可能需要提升原本 `ultralytics` 包之預設資料增減 (Augmentation) 定義。或者檢測 `data.yaml` 的 `nc` 與您實際 txt 內部的代碼區間是否合法。

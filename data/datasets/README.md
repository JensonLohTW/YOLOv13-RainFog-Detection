# 資料集目錄

每個資料集為一個子目錄，採用 YOLO 標準格式組織影像與標注。

## 目錄結構

```
datasets/
  rainfog_detection/       ← 雨霧天氣車輛行人偵測資料集（模板已建立）
    images/
      train/               ← 訓練圖片（.jpg / .png）
      val/                 ← 驗證圖片
      test/                ← 測試圖片（可選）
    labels/
      train/               ← YOLO 格式標注（.txt，與圖片同名）
      val/
      test/
    data.yaml              ← 資料集配置與類別清單（car / truck / bus / person）
```

## YOLO 標注格式

每個 `.txt` 標注檔對應一張圖片，每行代表一個物件：

```
<class_id> <x_center> <y_center> <width> <height>
```

所有數值均為 0~1 的相對座標（相對於圖片寬高）。

## 新增犬種資料集步驟

1. 將圖片放入對應的 `images/train/` 與 `images/val/` 目錄。
2. 將對應標注檔（`.txt`）放入 `labels/train/` 與 `labels/val/`。
3. 編輯 `data.yaml`：填入 `nc`（類別數）與 `names`（犬種清單）。
4. 執行訓練（在 `backend/` 目錄下）：

```bash
uv run yolo train data=../data/datasets/dog_breeds/data.yaml model=yolov13n.pt epochs=100
```

## 新增其他類型資料集

1. 在 `datasets/` 下建立新目錄（如 `cat_breeds/`）。
2. 按上述相同結構建立 `images/`、`labels/` 子目錄與 `data.yaml`。
3. 在 `backend/.env` 中更新 `INFERENCE_DATASETS_ROOT`（若有需要）。

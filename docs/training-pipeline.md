# YOLOv13 模型訓練與微調管線 (Training Pipeline)

> **當前落實狀態標註**：
> 本文檔詳述的「資料處理與模型微調」為**離線訓練輔助流程**。
> 當前 YOLOv13-RainFog 專案的主系統實體（前端管理台、後端 API、推理發佈服務）已全數落地完成，然「自動化訓練與資料清洗管線」尚未整合至主系統流水線，亦無相關介面。
> 此文件目的是作為資料科學家/AI工程師在遠端或單機執行標註檔訓練前之核心教學。

## 1. 訓練管線與概念綜觀
本任務旨在把雨霧環境下的原始劣質照片，經過資料預備工程與增強，輸送到 YOLOv13 架構進行監督式微調（Supervised Fine-Tuning）。訓練後驗證其效果，將萃取出高精度的特徵權重檔轉換給 FastAPI 推理端調用。

## 2. 訓練流程架構圖

整個機器學習生命週期依賴以下的工作管線推動：

```mermaid
flowchart TD
    Raw[原始極端天氣資料集 (如 DAWN Dataset)] --> Split[80/20 資料分割: Train / Val]
    Split --> Prep[影像增強與預處理: Mosaic / 仿射轉換 / 色彩加減]
    
    subgraph "離線微調計算流程 (Offline ML Training)"
        Prep --> Load[載入泛用預訓練 YOLOv13 權重]
        Load --> Forward[進入 DNN 進行前向計算 (Forward Pass)]
        Forward --> Loss[計算 Loss 函數偏差 (BBox + Cls + DFL)]
        Loss --> Backprop[AdamW 優化器執行梯度反向傳播]
        Backprop --> Epoch{完成所有的 Epoch?}
        Epoch --> |否| Forward
    end
    
    Epoch --> |是| Eval[對 Validation Set 計算 mAP 與 F1-Score]
    Eval --> Export[產出優化結果 best.pt 權重]
    
    Export -.-> |人工將檔案轉移至 data/models/| FastAPI[配置 Web `.env`<br>設定 INFERENCE_MODEL_MODE=yolov13]
```

## 3. 評量與驗證指標定義

在驗證集判讀的過程中，我們嚴密追蹤以下數學定義下的效能評估指標 (Metrics)：

### 3.1 基礎混淆值與精準率/召回率
任何錨框檢測需判定為 True Positive (TP), False Positive (FP) 還是 False Negative (FN)。

$$ \text{Precision (精確率)} = \frac{TP}{TP + FP} $$
$$ \text{Recall (召回率)} = \frac{TP}{TP + FN} $$

### 3.2 F1-Score
利用調和平均數兼顧假陽性與遺漏抓查之間的天秤：

$$ F1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} $$

### 3.3 平均精度均值 (Mean Average Precision, mAP)
先針對單一個類別求取 Average Precision (AP)，也就是積分 Precision-Recall 曲線下方面積。其後針對所有物種 $N$ 取總體均值。本模型特別審視 `mAP@50` 表現。

$$ \text{mAP} = \frac{1}{N} \sum_{i=1}^{N} \int_{0}^{1} p_i(r) \, dr $$

## 4. 損失函數設計 (Loss Functions)
Ultralytics YOLO 於收斂學習梯度中，所觀察結合的優化函數與約束項目定義為：

$$ \mathcal{L} = \lambda_{\text{box}} \cdot \mathcal{L}_{\text{box}} + \lambda_{\text{cls}} \cdot \mathcal{L}_{\text{cls}} + \lambda_{\text{dfl}} \cdot \mathcal{L}_{\text{dfl}} $$

- $\mathcal{L}_{\text{box}}$: **CIoU 損失** (Complete IoU)。除了框框交集面積，同時把長寬比差異納入衡量。
- $\mathcal{L}_{\text{cls}}$: **BCE 二元交叉熵** (Binary Cross Entropy)。獨立判斷錨框類別準確度。
- $\mathcal{L}_{\text{dfl}}$: **分佈焦點損失**。細緻化並強制回歸邊界細節。

## 5. 與主系統服務的對接與落差說明
作為開發者請充分認知：**「當前的管理網頁，不具備一鍵發起訓練模型的能力」。**

若需掛載訓練後的成品，您應當：
1. 確保自己在包含顯示卡叢集的本地或遠端虛擬主機訓練。
2. 拿到訓練完成打包的 `.pt` 。
3. 歸檔入專案實體目錄：`data/models/` 之中。
4. 強制於 Web 後端環境變數開啟 `INFERENCE_MODEL_MODE=yolov13` 作為掛載指標。

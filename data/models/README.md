# 模型權重目錄

將下載的 `.pt` 權重檔直接放在此目錄下，系統會自動讀取。

## 可用規格

| 檔名          | 規格   | 特性                             |
|---------------|--------|----------------------------------|
| yolov13n.pt   | nano   | 最快速，適合邊緣裝置與測試環境   |
| yolov13s.pt   | small  | 速度與精度均衡，適合一般部署     |
| yolov13l.pt   | large  | 高精度，需要較多計算資源         |
| yolov13x.pt   | xlarge | 最高精度，需要 GPU               |

## 下載來源

https://github.com/iMoonLab/yolov13/releases

## 切換模型規格

在 `backend/.env` 中設定（修改後重啟推理服務）：

```env
INFERENCE_YOLOV13_MODEL_FILE=yolov13n.pt   # 改為所需規格
```

## 新增自訓練權重

將訓練產出的 `best.pt` 複製至此目錄並重新命名，再更新 `.env` 即可：

```bash
cp runs/train/exp/weights/best.pt data/models/dog_breeds_v1.pt
# 然後在 .env 設定：
# INFERENCE_YOLOV13_MODEL_FILE=dog_breeds_v1.pt
```

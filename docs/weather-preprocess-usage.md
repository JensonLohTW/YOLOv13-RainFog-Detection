# 恶劣天气图像预处理模块使用说明

本文档说明本项目新增的**图像预处理**模块如何与现有训练、验证、离线推理和在线推理链路配合使用，并给出最小可运行命令。

## 1. 目标与默认行为

- 目标类别：`truck`, `person`, `bicycle`, `car`, `motorcycle`, `bus`
- 目标：提升恶劣天气下的检测效果，而不是视觉美化
- 默认行为：**关闭预处理**，因此不启用时应与当前基准流程保持一致
- 预处理策略：
  - `off`：关闭预处理
  - `auto`：从文件名自动识别场景并使用推荐算法组合
  - `manual`：手动指定场景模板或算法列表

## 2. 场景识别规则

预处理模块优先从图片名或路径中识别原始场景标签，识别目录来源通常为：
`data/datasets/rainfog_detection/dawn-dataset/images`

### 原始场景标签

- `dusttornado`
- `foggy`
- `haze`
- `mist`
- `rain_storm`
- `sand_storm`
- `snow_storm`

### 场景映射策略

- `dusttornado`, `sand_storm` -> `sandstorm`
- `foggy`, `haze`, `mist` -> `fog`
- `rain_storm` -> `rain`
- `snow_storm` -> `snow`

## 3. 首版默认算法组合

### `sandstorm`

- `white_balance`
- `dcp_dehaze`
- `clahe`
- `guided_filter`

### `fog`

- `dcp_dehaze`
- `clahe`
- `mild_unsharp`

### `rain`

- `bilateral`
- `tone_mapping`
- `clahe`
- 可选 `gamma`

### `snow`

- `highlight_compression`
- `clahe`
- `bilateral`
- `mild_unsharp`

## 4. 新增/修改的主要文件

### 共享预处理模块

- `backend/common/weather_preprocess/__init__.py`
- `backend/common/weather_preprocess/scenes.py`
- `backend/common/weather_preprocess/algorithms.py`
- `backend/common/weather_preprocess/pipeline.py`
- `backend/common/weather_preprocess/dataset.py`

### 训练/验证/离线推理

- `backend/training/config_utils.py`
- `backend/training/preprocess_utils.py`
- `backend/training/train.py`
- `backend/training/validate.py`
- `backend/training/infer.py`
- `backend/training/compare.py`
- `backend/training/configs/preprocess_auto.yaml`
- `backend/training/configs/preprocess_manual_rain.yaml`

### 在线推理与 Django 接口

- `backend/inference_service/schemas/inference.py`
- `backend/inference_service/adapters/mock.py`
- `backend/inference_service/adapters/yolov13.py`
- `backend/integrations/inference/client.py`
- `backend/apps/detection/models.py`
- `backend/apps/detection/serializers.py`
- `backend/apps/detection/services.py`
- `backend/apps/detection/views.py`
- `backend/apps/detection/migrations/0003_add_preprocess_fields.py`

### 训练任务持久化

- `backend/apps/training/models.py`
- `backend/apps/training/serializers.py`
- `backend/apps/training/services/job_service.py`
- `backend/apps/training/views.py`
- `backend/apps/training/migrations/0004_add_preprocess_fields.py`

### 依赖

- `backend/pyproject.toml`

## 5. 安装与迁移

以下命令请由你手动执行。

### 安装依赖

```powershell
uv sync --extra yolo
```

### 执行数据库迁移

```powershell
uv run python manage.py migrate
```

## 6. 最小运行命令

以下命令均在 `backend/` 目录下执行。

### 6.1 基准训练（无预处理）

```powershell
uv run python -m training.train `
  --model yolov13l.pt `
  --dataset rainfog_detection `
  --epochs 50 `
  --batch 4 `
  --imgsz 640 `
  --workers 0 `
  --patience 20 `
  --device 0 `
  --preprocess-mode off
```

### 6.2 自动场景预处理 + 微调训练

```powershell
uv run python -m training.train `
  --config training/configs/preprocess_auto.yaml `
  --model yolov13l.pt `
  --dataset rainfog_detection `
  --device 0
```

### 6.3 手动预处理 + 微调训练

```powershell
uv run python -m training.train `
  --config training/configs/preprocess_manual_rain.yaml `
  --model yolov13l.pt `
  --dataset rainfog_detection `
  --device 0
```

### 6.4 命令行手动指定算法列表

```powershell
uv run python -m training.train `
  --model yolov13l.pt `
  --dataset rainfog_detection `
  --epochs 50 `
  --batch 4 `
  --imgsz 640 `
  --workers 0 `
  --patience 20 `
  --device 0 `
  --preprocess-mode manual `
  --preprocess-profile rain `
  --preprocess-algorithms bilateral,tone_mapping,clahe
```

### 6.5 验证基准模型

```powershell
uv run python -m training.validate `
  --model yolov13l.pt `
  --dataset rainfog_detection `
  --output ../data/results/validate_baseline.json `
  --device 0 `
  --preprocess-mode off
```

### 6.6 验证启用预处理模型

```powershell
uv run python -m training.validate `
  --model ../data/train_runs/<run_name>/weights/best.pt `
  --dataset rainfog_detection `
  --output ../data/results/validate_preprocess_auto.json `
  --device 0 `
  --preprocess-mode auto
```

### 6.7 离线推理识别

```powershell
uv run python -m training.infer `
  --model ../data/train_runs/<run_name>/weights/best.pt `
  --source ../data/datasets/rainfog_detection/images/val `
  --output-dir ../data/results/offline_infer_auto `
  --device 0 `
  --preprocess-mode auto
```

### 6.8 基准模型 vs 预处理模型对比评估

```powershell
uv run python -m training.compare `
  --baseline-model yolov13l.pt `
  --experiment-model ../data/train_runs/<run_name>/weights/best.pt `
  --dataset rainfog_detection `
  --device 0 `
  --preprocess-mode auto `
  --output-dir ../data/results/compare_auto
```

## 7. 在线推理 API 用法

在线推理默认仍可不传预处理参数。

### 默认关闭

- `preprocess_mode = off`

### 请求体新增字段

- `preprocess_mode`
- `preprocess_profile`
- `preprocess_algorithms`
- `preprocess_algorithm_params`
- `preprocess_enable_gamma`

### 在线推理请求示例

```json
{
  "image_id": 1,
  "weather_scene": "fog",
  "confidence_threshold": 0.25,
  "iou_threshold": 0.45,
  "preprocess_mode": "auto",
  "preprocess_profile": "",
  "preprocess_algorithms": [],
  "preprocess_algorithm_params": {},
  "preprocess_enable_gamma": false
}
```

## 8. 输出与可复现产物

### 训练运行目录

`data/train_runs/<run_name>/`

### 关键产物

- `baseline_metrics.json`
- `experiment_manifest.json`
- `experiment_compare.md`
- `epoch_report.md`
- `training_summary.md`
- `training_summary.csv`
- `weights/best.pt`
- `weights/last.pt`

### 预处理派生数据集

默认输出到：

`data/datasets/_prepared/<dataset_name>__<signature>/`

其中包含：

- `images/train`
- `images/val`
- `labels/train`
- `labels/val`
- `data.yaml`
- `preprocess_manifest.json`

## 9. 默认参数说明

### 默认训练参数

- `epochs=50`
- `batch=16`（若通过现有训练 API 创建任务则默认常用值仍由服务层给出）
- `imgsz=640`
- `workers=4`
- `patience=20`

### 默认预处理参数

- `preprocess_mode=off`
- `preprocess_profile=""`
- `preprocess_algorithms=[]`
- `preprocess_enable_gamma=false`

## 10. 如何关闭预处理

### 训练/验证/推理命令行

```powershell
--preprocess-mode off
```

### YAML 配置

```yaml
preprocess:
  mode: off
```

### 在线推理

```json
{
  "preprocess_mode": "off"
}
```

## 11. 如何新增场景策略

### 第一步

在 `backend/common/weather_preprocess/scenes.py` 中添加原始标签到策略场景的映射。

### 第二步

在 `backend/common/weather_preprocess/algorithms.py` 的：

- `DEFAULT_SCENE_ALGORITHMS`
- `DEFAULT_ALGORITHM_PARAMS`
- `ALGORITHM_REGISTRY`

中补充对应算法链与参数。

### 第三步

如果新场景需要自动识别，确保图片名或路径中包含可识别标签。

### 第四步

重新运行：

- `training.validate`
- `training.infer`
- `training.compare`
- 或 `training.train`

以生成新的可复现实验产物。

## 12. 当前首版实现边界

- 当前自动场景识别优先依赖**文件名/路径标签**，不是独立天气分类模型
- 当前采用**传统可解释图像处理算法**，不引入额外深度预处理网络
- 当前训练一致性通过**派生预处理数据集**保证，不覆盖原始数据集
- 若文件名无法识别场景，自动模式会回退为 `unknown`，等价于不执行场景专属算法链

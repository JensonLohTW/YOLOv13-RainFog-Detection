# 图像预处理模块目录结构

```text
backend/
├── common/
│   └── weather_preprocess/
│       ├── __init__.py
│       ├── algorithms.py
│       ├── dataset.py
│       ├── pipeline.py
│       └── scenes.py
├── training/
│   ├── compare.py
│   ├── config_utils.py
│   ├── infer.py
│   ├── preprocess_utils.py
│   ├── train.py
│   ├── validate.py
│   └── configs/
│       ├── preprocess_auto.yaml
│       └── preprocess_manual_rain.yaml
├── inference_service/
│   ├── adapters/
│   │   ├── mock.py
│   │   └── yolov13.py
│   └── schemas/
│       └── inference.py
├── integrations/
│   └── inference/
│       └── client.py
├── apps/
│   ├── detection/
│   │   ├── migrations/
│   │   │   └── 0003_add_preprocess_fields.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   └── views.py
│   └── training/
│       ├── migrations/
│       │   └── 0004_add_preprocess_fields.py
│       ├── models.py
│       ├── serializers.py
│       ├── services/
│       │   └── job_service.py
│       └── views.py
└── pyproject.toml

docs/
├── weather-preprocess-file-tree.md
└── weather-preprocess-usage.md
```

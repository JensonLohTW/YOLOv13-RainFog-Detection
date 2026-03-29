"""
YOLOv13 真實推理 Adapter（Phase 4）。

依賴：ultralytics + torch
  - Windows / Linux / Apple Silicon：cd backend && uv sync --extra yolo
  - Intel Mac（x86_64）：
      conda install pytorch torchvision cpuonly -c pytorch
      pip install ultralytics

啟用步驟（設定 backend/.env）：
  INFERENCE_MODEL_MODE=yolov13
  INFERENCE_YOLOV13_MODEL_FILE=yolov13n.pt   # 可改 s / l / x
  INFERENCE_MODELS_ROOT=../data/models       # 放置 .pt 的目錄
  INFERENCE_YOLOV13_ROOT=../yolov13-main     # clone 的原始碼目錄
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from common.weather_preprocess import PreprocessOptions, preprocess_image
from inference_service.adapters.base import BaseInferenceAdapter
from inference_service.core.config import Settings
from inference_service.schemas.inference import InferenceRequest

logger = logging.getLogger(__name__)


class YoloV13InferenceAdapter(BaseInferenceAdapter):
    """
    使用本地 yolov13-main/ultralytics 執行真實物件偵測。
    第一次 detect() 呼叫時懶加載模型（單例），避免 FastAPI 啟動延遲。
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None  # 懶加載單例

    # ──────────────────────────────────────────────
    #  describe
    # ──────────────────────────────────────────────

    def describe(self) -> dict:
        model_path = self.settings.get_model_path()
        return {
            "engine_type": "yolov13",
            "engine_version": "13.0",
            "model_name": self.settings.yolov13_model_file,
            "model_version": "v1",
            "ready": model_path.exists(),
            "model_path": str(model_path),
            "note": (
                "Real YOLOv13 inference via ultralytics."
                if model_path.exists()
                else f"Model file not found: {model_path}. "
                     "Download from https://github.com/iMoonLab/yolov13/releases"
            ),
        }

    # ──────────────────────────────────────────────
    #  模型載入（懶加載 / 單例）
    # ──────────────────────────────────────────────

    def _load_model(self):
        if self._model is not None:
            return self._model

        # 把 yolov13-main 加入 sys.path，優先使用本地版本的 ultralytics。
        # 使用 Path.resolve() 規格化路徑（Windows 路徑大小寫 + 分隔符統一）。
        yolov13_root = str(Path(self.settings.yolov13_root).resolve())
        if yolov13_root not in sys.path:
            sys.path.insert(0, yolov13_root)

        try:
            from ultralytics import YOLO  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics 未安裝，無法使用真實推理模式。\n"
                "  Windows / Linux / Apple Silicon：cd backend && uv sync --extra yolo\n"
                "  Intel Mac（x86_64）：\n"
                "    conda install pytorch torchvision cpuonly -c pytorch\n"
                "    pip install ultralytics"
            ) from exc

        model_path = self.settings.get_model_path()
        if not model_path.exists():
            raise FileNotFoundError(
                f"模型權重檔不存在：{model_path}\n"
                f"請下載 {self.settings.yolov13_model_file} 並放至：\n"
                f"  {self.settings.models_root}/\n"
                "可用規格：yolov13n.pt / yolov13s.pt / yolov13l.pt / yolov13x.pt\n"
                "下載連結：https://github.com/iMoonLab/yolov13/releases"
            )

        logger.info("載入模型：%s", model_path)
        self._model = YOLO(str(model_path))
        logger.info("模型載入完成：%s", self.settings.yolov13_model_file)
        return self._model

    def _load_rgb_image(self, image_path: str) -> np.ndarray:
        return np.array(Image.open(image_path).convert("RGB"))

    # ──────────────────────────────────────────────
    #  detect
    # ──────────────────────────────────────────────

    def detect(self, payload: InferenceRequest) -> dict:
        model = self._load_model()
        preprocess_options = PreprocessOptions(
            mode=payload.preprocess_mode,
            profile=payload.preprocess_profile,
            scene=payload.scene,
            algorithms=list(payload.preprocess_algorithms),
            algorithm_params=dict(payload.preprocess_algorithm_params),
            enable_gamma=payload.preprocess_enable_gamma,
        )
        source_image = self._load_rgb_image(payload.image_path)
        preprocess_result = preprocess_image(
            source_image,
            preprocess_options,
            image_path=payload.image_path,
            scene_hint=payload.scene,
        )

        logger.debug("開始推理：task_no=%s  image=%s", payload.task_no, payload.image_path)
        t0 = time.time()
        results = model.predict(
            source=Image.fromarray(preprocess_result.image),
            conf=payload.confidence_threshold,
            iou=payload.iou_threshold,
            save=False,
            verbose=False,
        )
        duration_ms = int((time.time() - t0) * 1000)
        logger.debug("推理完成：%d ms，偵測物件數=%d", duration_ms, len(results[0].boxes) if results[0].boxes is not None else 0)

        result = results[0]

        # ── 提取偵測物件 ──────────────────────────────
        objects = []
        if result.boxes is not None:
            for box in result.boxes:
                x1, y1, x2, y2 = [int(c) for c in box.xyxy[0].tolist()]
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = result.names.get(cls_id, str(cls_id))
                objects.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(conf, 4),
                    "bbox": [x1, y1, x2, y2],
                })

        # ── 儲存標注結果圖 ────────────────────────────
        result_image_path = self._save_result_image(result, payload.task_no)

        return {
            "task_no": payload.task_no,
            "success": True,
            "engine_type": "yolov13",
            "engine_version": "13.0",
            "model_name": self.settings.yolov13_model_file,
            "model_version": "v1",
            "duration_ms": duration_ms,
            "result_image_path": result_image_path,
            "objects": objects,
            "raw": {
                "mock": False,
                "scene": payload.scene,
                "preprocess": preprocess_result.metadata(),
            },
        }

    # ──────────────────────────────────────────────
    #  結果圖存檔
    # ──────────────────────────────────────────────

    def _save_result_image(self, result, task_no: str) -> str:
        """
        將 YOLO 標注後的影像存至 data/results/YYYY/MM/DD/<task_no>_result.jpg。
        回傳絕對路徑字串；存檔失敗時靜默回傳空字串（不中斷主流程）。
        """
        try:
            annotated_bgr = result.plot()  # numpy array, BGR
            annotated_rgb = annotated_bgr[:, :, ::-1]  # BGR → RGB

            today = datetime.now()
            # 逐層 / 拼接，避免格式字串中的 "/" 在 Windows 產生歧義
            out_dir = (
                self.settings.get_results_root()
                / f"{today:%Y}"
                / f"{today:%m}"
                / f"{today:%d}"
            )
            out_dir.mkdir(parents=True, exist_ok=True)

            out_path = out_dir / f"{task_no}_result.jpg"
            Image.fromarray(annotated_rgb.astype(np.uint8)).save(str(out_path), quality=90)
            return str(out_path)
        except Exception:  # noqa: BLE001
            logger.warning("結果圖存檔失敗，task_no=%s", task_no)
            return ""

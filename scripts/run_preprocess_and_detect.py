"""
預處理 + YOLOv13 偵測展示腳本

輸出目錄結構：
  data/demo_output/
    <scene>_<id>/
      1_original.jpg          原始圖
      2_preprocessed.jpg      預處理後
      3_yolo_original.jpg     YOLO 標注（原始圖）
      4_yolo_preprocessed.jpg YOLO 標注（預處理後）
      info.txt                場景 / 演算法 / 偵測數摘要
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
# 優先使用 yolov13-main 的 ultralytics（含自定義 DSC3k2 等模組）
sys.path.insert(0, str(ROOT / "yolov13-main"))
sys.path.insert(1, str(ROOT / "backend"))

from common.weather_preprocess import (
    PREPROCESS_MODE_AUTO,
    PreprocessOptions,
    preprocess_image_file,
)

MODEL_PATH = ROOT / "data/train_runs/rainfog_20260329_121743/weights/best.pt"
DATASET    = ROOT / "data/datasets/dawn-dataset/images"
OUT_DIR    = ROOT / "data/demo_output"

# 每個天氣類型各取 2 張
TEST_IMAGES = [
    DATASET / "foggy-001.jpg",
    DATASET / "foggy-002.jpg",
    DATASET / "rain_storm-001.jpg",
    DATASET / "rain_storm-002.jpg",
    DATASET / "snow_storm-001.jpg",
    DATASET / "snow_storm-002.jpg",
    DATASET / "dusttornado-001.jpg",
    DATASET / "dusttornado-002.jpg",
    DATASET / "sand_storm-001.jpg",
    DATASET / "sand_storm-002.jpg",
]


def load_yolo(model_path: Path):
    from ultralytics import YOLO
    print(f"載入模型：{model_path}")
    return YOLO(str(model_path))


def annotate(model, img_array: np.ndarray, conf: float = 0.15) -> np.ndarray:
    """執行 YOLO 推理，回傳標注後的 RGB numpy array。"""
    pil_img = Image.fromarray(img_array)
    results = model.predict(source=pil_img, conf=conf, iou=0.5,
                            save=False, verbose=False)
    result = results[0]
    annotated_bgr = result.plot()          # BGR
    return annotated_bgr[:, :, ::-1]       # → RGB


def count_detections(model, img_array: np.ndarray, conf: float = 0.15) -> list[dict]:
    pil_img = Image.fromarray(img_array)
    results = model.predict(source=pil_img, conf=conf, iou=0.5,
                            save=False, verbose=False)
    result = results[0]
    detections = []
    if result.boxes is not None:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            detections.append({
                "class": result.names.get(cls_id, str(cls_id)),
                "conf":  round(float(box.conf[0]), 3),
            })
    return detections


def save_img(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.astype(np.uint8)).save(str(path), quality=92)


def main() -> None:
    model = load_yolo(MODEL_PATH)
    opts  = PreprocessOptions(mode=PREPROCESS_MODE_AUTO)

    summary_lines = ["=" * 70, "預處理 + YOLO 偵測摘要", "=" * 70]

    for img_path in TEST_IMAGES:
        if not img_path.exists():
            print(f"  [SKIP] {img_path.name}")
            continue

        tag     = img_path.stem          # e.g. foggy-001
        out_dir = OUT_DIR / tag
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'─'*50}")
        print(f"處理：{img_path.name}")

        # ── 1. 載入原始圖 ─────────────────────────────────
        original = np.array(Image.open(img_path).convert("RGB"))
        save_img(original, out_dir / "1_original.jpg")

        # ── 2. 預處理 ─────────────────────────────────────
        t0 = time.time()
        pp_result = preprocess_image_file(img_path, opts)
        pp_ms = int((time.time() - t0) * 1000)
        save_img(pp_result.image, out_dir / "2_preprocessed.jpg")

        print(f"  scene      : {pp_result.raw_scene} → {pp_result.scene}")
        print(f"  algorithms : {pp_result.algorithms}")
        print(f"  applied    : {pp_result.applied}  ({pp_ms} ms)")

        # ── 3. YOLO 偵測（原始圖）─────────────────────────
        t0 = time.time()
        det_orig = count_detections(model, original)
        yolo_orig_img = annotate(model, original)
        yolo_orig_ms = int((time.time() - t0) * 1000)
        save_img(yolo_orig_img, out_dir / "3_yolo_original.jpg")
        print(f"  原始偵測數  : {len(det_orig)}  ({yolo_orig_ms} ms)  {det_orig[:5]}")

        # ── 4. YOLO 偵測（預處理後）───────────────────────
        t0 = time.time()
        det_pp = count_detections(model, pp_result.image)
        yolo_pp_img = annotate(model, pp_result.image)
        yolo_pp_ms = int((time.time() - t0) * 1000)
        save_img(yolo_pp_img, out_dir / "4_yolo_preprocessed.jpg")
        print(f"  預處理偵測數: {len(det_pp)}  ({yolo_pp_ms} ms)  {det_pp[:5]}")

        # ── 5. info.txt ────────────────────────────────────
        info = (
            f"image     : {img_path.name}\n"
            f"raw_scene : {pp_result.raw_scene}\n"
            f"scene     : {pp_result.scene}\n"
            f"algorithms: {', '.join(pp_result.algorithms) or '(none)'}\n"
            f"applied   : {pp_result.applied}\n"
            f"\n"
            f"YOLO original    : {len(det_orig)} objects\n"
            + "".join(f"  - {d['class']} ({d['conf']})\n" for d in det_orig)
            + f"\nYOLO preprocessed: {len(det_pp)} objects\n"
            + "".join(f"  - {d['class']} ({d['conf']})\n" for d in det_pp)
        )
        (out_dir / "info.txt").write_text(info, encoding="utf-8")

        summary_lines.append(
            f"{tag:<22}  scene={pp_result.scene:<10}  "
            f"orig={len(det_orig):>2}  pp={len(det_pp):>2}  "
            f"algos={','.join(pp_result.algorithms) or '-'}"
        )

    print(f"\n{'='*50}")
    print("\n".join(summary_lines))
    print(f"\n輸出目錄：{OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()

"""
一鍵執行腳本：推論比較 + 啟動繼續訓練

步驟：
  1. 推論比較（約 2~3 分鐘）
     - 用 best.pt 對 10 張圖做 YOLO 偵測
     - 分別對比「原圖」與「預處理後」兩種結果
     - conf threshold = 0.15（較低，提升 Recall）
     - 結果輸出至 data/demo_output/

  2. 啟動繼續訓練（約 18 小時，後台執行）
     - 起點：best.pt（上輪最佳，mAP50=0.750）
     - 改善超參：lr0=0.001, lrf=0.001, cos_lr=True, batch=8
     - 訓練 50 epoch
     - 中間數據每個 epoch 自動更新：
         data/train_runs/rainfog_v2/epoch_report.md
         data/train_runs/rainfog_v2/training_curve.png
         data/train_runs/rainfog_v2/checkpoints/

使用方式：
  cd C:\\Users\\Administrator\\Downloads\\YOLOv13-RainFog-Detection\\backend
  .venv\\Scripts\\python.exe ..\\scripts\\run_pipeline.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

# ── 路徑設定 ──────────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parent.parent
BACKEND  = ROOT / "backend"
PYTHON   = BACKEND / ".venv/Scripts/python.exe"
BEST_PT  = ROOT / "data/train_runs/rainfog_20260329_121743/weights/best.pt"
OUT_DIR  = ROOT / "data/demo_output"
TRAIN_OUT = ROOT / "data/train_runs/rainfog_v2"

# ── yolov13-main 優先載入 ─────────────────────────────────────
sys.path.insert(0, str(ROOT / "yolov13-main"))
sys.path.insert(1, str(BACKEND))


# ═══════════════════════════════════════════════════════════════
#  STEP 1：推論比較
# ═══════════════════════════════════════════════════════════════

def run_inference_comparison() -> None:
    import numpy as np
    from PIL import Image

    from common.weather_preprocess import (
        PREPROCESS_MODE_AUTO,
        PreprocessOptions,
        preprocess_image_file,
    )
    from ultralytics import YOLO

    DATASET = ROOT / "data/datasets/dawn-dataset/images"
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
    CONF = 0.15

    print(f"\n{'═'*60}")
    print("  STEP 1：推論比較（conf=0.15）")
    print(f"{'═'*60}")
    print(f"  模型：{BEST_PT.name}")
    print(f"  圖片數：{len(TEST_IMAGES)} 張（5 種天氣 × 2）")
    print(f"  輸出：{OUT_DIR}\n")

    model = YOLO(str(BEST_PT))
    opts  = PreprocessOptions(mode=PREPROCESS_MODE_AUTO)

    rows = []
    for img_path in TEST_IMAGES:
        if not img_path.exists():
            print(f"  [SKIP] {img_path.name}")
            continue

        tag     = img_path.stem
        out_dir = OUT_DIR / tag
        out_dir.mkdir(parents=True, exist_ok=True)

        # 原始圖
        original = np.array(Image.open(img_path).convert("RGB"))
        Image.fromarray(original).save(str(out_dir / "1_original.jpg"), quality=92)

        # 預處理
        pp = preprocess_image_file(img_path, opts)
        Image.fromarray(pp.image.astype("uint8")).save(str(out_dir / "2_preprocessed.jpg"), quality=92)

        # YOLO 偵測（原圖）
        r_orig = _detect(model, original, CONF)
        _save_annotated(r_orig, out_dir / "3_yolo_original.jpg")

        # YOLO 偵測（預處理後）
        r_pp = _detect(model, pp.image, CONF)
        _save_annotated(r_pp, out_dir / "4_yolo_preprocessed.jpg")

        n_orig = len(r_orig.boxes) if r_orig.boxes else 0
        n_pp   = len(r_pp.boxes)   if r_pp.boxes   else 0
        diff   = n_pp - n_orig
        diff_s = f"▲+{diff}" if diff > 0 else (f"▼{diff}" if diff < 0 else "=")

        # info.txt
        info = _build_info(img_path, pp, r_orig, r_pp)
        (out_dir / "info.txt").write_text(info, encoding="utf-8")

        rows.append((tag, pp.scene, n_orig, n_pp, diff_s,
                     ",".join(pp.algorithms) or "-"))
        print(f"  ✓ {tag:<22}  scene={pp.scene:<10}  "
              f"原圖={n_orig:>2}個  預處理={n_pp:>2}個  {diff_s}")

    # 彙整表
    print(f"\n{'─'*60}")
    print(f"  {'圖片':<22}  {'場景':<10}  原圖  預處理  變化  演算法")
    print(f"{'─'*60}")
    for tag, scene, n_o, n_p, diff_s, algos in rows:
        print(f"  {tag:<22}  {scene:<10}  {n_o:>3}   {n_p:>3}    {diff_s:<4}  {algos}")
    print(f"\n  輸出目錄：{OUT_DIR.resolve()}")
    print("  每個子目錄有：1_original / 2_preprocessed / "
          "3_yolo_original / 4_yolo_preprocessed / info.txt\n")


def _detect(model, img_arr, conf):
    from PIL import Image
    results = model.predict(
        source=Image.fromarray(img_arr.astype("uint8")),
        conf=conf, iou=0.5, save=False, verbose=False,
    )
    return results[0]


def _save_annotated(result, path: Path) -> None:
    import numpy as np
    from PIL import Image
    bgr = result.plot()
    Image.fromarray(bgr[:, :, ::-1].astype("uint8")).save(str(path), quality=92)


def _build_info(img_path, pp, r_orig, r_pp) -> str:
    def _fmt(boxes, names):
        if boxes is None:
            return "  （無偵測）\n"
        lines = ""
        for box in boxes:
            cls  = int(box.cls[0])
            conf = float(box.conf[0])
            lines += f"  - {names.get(cls, str(cls))} ({conf:.3f})\n"
        return lines or "  （無偵測）\n"

    n_orig = len(r_orig.boxes) if r_orig.boxes else 0
    n_pp   = len(r_pp.boxes)   if r_pp.boxes   else 0
    return (
        f"image     : {img_path.name}\n"
        f"raw_scene : {pp.raw_scene}\n"
        f"scene     : {pp.scene}\n"
        f"algorithms: {', '.join(pp.algorithms) or '(none)'}\n"
        f"applied   : {pp.applied}\n\n"
        f"YOLO 原圖（{n_orig} 個）:\n"
        + _fmt(r_orig.boxes, r_orig.names)
        + f"\nYOLO 預處理後（{n_pp} 個）:\n"
        + _fmt(r_pp.boxes, r_pp.names)
    )


# ═══════════════════════════════════════════════════════════════
#  STEP 2：啟動繼續訓練（新視窗後台執行）
# ═══════════════════════════════════════════════════════════════

def launch_training() -> None:
    print(f"\n{'═'*60}")
    print("  STEP 2：啟動繼續訓練（rainfog_v2）")
    print(f"{'═'*60}")
    print(f"  起點模型  : {BEST_PT.name}  (mAP50=0.750)")
    print(f"  超參改善  : lr0=0.001  lrf=0.001  cos_lr=True  batch=8")
    print(f"  訓練 epoch: 50")
    print(f"  輸出目錄  : {TRAIN_OUT}\n")

    cmd = [
        str(PYTHON), "-m", "training.train",
        "--model",    str(BEST_PT),
        "--dataset",  "rainfog_detection",
        "--epochs",   "50",
        "--batch",    "8",
        "--imgsz",    "640",
        "--device",   "0",
        "--workers",  "0",
        "--patience", "20",
        "--lr0",      "0.001",
        "--lrf",      "0.001",
        "--cos-lr",
        "--name",     "rainfog_v2",
    ]

    # Windows：在新的 cmd 視窗中執行，不阻塞當前腳本
    subprocess.Popen(
        ["cmd", "/c", "start", "cmd", "/k"] + cmd,
        cwd=str(BACKEND),
        shell=False,
    )

    print("  訓練已在新視窗啟動。請在新視窗觀察輸出。")
    print(f"\n  即時監控（另開 PowerShell 視窗執行）：")
    print(f"""
    $run = "{TRAIN_OUT}"
    while ($true) {{
        if (Test-Path "$run\\epoch_report.md") {{
            Get-Content "$run\\epoch_report.md" | Select-Object -First 15
        }}
        Write-Host "--- $(Get-Date -Format 'HH:mm:ss') ---"
        Start-Sleep 60
    }}
""")
    print(f"  或直接在檔案總管開啟：")
    print(f"    {TRAIN_OUT}\\epoch_report.md    ← 每 epoch 更新")
    print(f"    {TRAIN_OUT}\\training_curve.png ← 訓練曲線圖")
    print(f"    {TRAIN_OUT}\\checkpoints\\       ← Top/Bottom checkpoint .pt")


# ═══════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    print(f"\n{'█'*60}")
    print("  YOLOv13 RainFog Pipeline")
    print(f"{'█'*60}")

    if not BEST_PT.exists():
        print(f"\n[ERROR] best.pt 不存在：{BEST_PT}")
        sys.exit(1)

    t0 = time.time()
    run_inference_comparison()
    elapsed = int(time.time() - t0)
    print(f"  推論比較完成，耗時 {elapsed} 秒")

    launch_training()

    print(f"\n{'█'*60}")
    print("  全部完成！")
    print(f"{'█'*60}")
    print(f"\n  推論結果 → {OUT_DIR.resolve()}")
    print(f"  訓練進度 → {TRAIN_OUT.resolve()}")
    print()


if __name__ == "__main__":
    main()

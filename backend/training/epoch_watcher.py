"""
EpochWatcher：訓練期間的後台監控執行緒。

每次偵測到 results.csv 新增一行（= 一個 epoch 完成），立即執行：
  1. 複製 last.pt → checkpoints/epoch_NNN_mapX.XXXX.pt
  2. 依 mAP50(B) 排序所有已知 epoch，保留 Top-3 與 Bottom-3 的 .pt 檔案
  3. 更新 epoch_report.md（含「基準 vs 當前最佳」對比表 + Top3 / Bot3 標記）
  4. 更新 training_curve.png（mAP50 折線圖 + 基準水平虛線）

基準指標（baseline_metrics.json）由 train.py 在訓練前自動寫入，
EpochWatcher 以 lazy load 方式讀取，二者完全解耦。
"""
from __future__ import annotations

import csv
import json
import logging
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_TOP_K = 3
_POLL_INTERVAL = 12   # 秒，輪詢間隔
_COPY_DELAY    = 5    # 秒，偵測到新 epoch 後等待 last.pt 寫入完成


# ─── Data model ──────────────────────────────────────────────────────────────

class _EpochRecord:
    __slots__ = ("epoch", "map50", "map50_95", "precision", "recall", "time_sec")

    def __init__(self, row: dict) -> None:
        def _f(k: str) -> float:
            try:
                return float(str(row.get(k, "0")).strip())
            except (ValueError, TypeError):
                return 0.0

        self.epoch     = int(_f("epoch"))
        self.time_sec  = _f("time")
        self.map50     = _f("metrics/mAP50(B)")
        self.map50_95  = _f("metrics/mAP50-95(B)")
        self.precision = _f("metrics/precision(B)")
        self.recall    = _f("metrics/recall(B)")

    @property
    def ckpt_stem(self) -> str:
        return f"epoch_{self.epoch:03d}_map{self.map50:.4f}"


# ─── Watcher ─────────────────────────────────────────────────────────────────

class EpochWatcher:
    """後台執行緒，在 model.train() 執行期間監控 results.csv。"""

    def __init__(self, run_dir: Path, total_epochs: int = 0) -> None:
        self.run_dir      = Path(run_dir)
        self.total_epochs = total_epochs
        self._ckpt_dir    = self.run_dir / "checkpoints"
        self._results_csv = self.run_dir / "results.csv"
        self._last_pt     = self.run_dir / "weights" / "last.pt"

        self._records: list[_EpochRecord] = []
        self._last_epoch_seen = 0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._baseline: dict | None = None
        self._baseline_path = self.run_dir / "baseline_metrics.json"

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._ckpt_dir.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._loop, daemon=True, name="EpochWatcher")
        self._thread.start()
        logger.info("[EpochWatcher] 已啟動，監控：%s", self._results_csv)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=30)
        self._final_update()
        logger.info("[EpochWatcher] 已停止")

    # ── Background loop ───────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001
                logger.debug("[EpochWatcher] tick 異常：%s", exc)
            self._stop_event.wait(timeout=_POLL_INTERVAL)

    def _load_baseline(self) -> None:
        """讀取 baseline_metrics.json（lazy load，檔案存在前靜默跳過）。"""
        if self._baseline is not None:
            return
        if not self._baseline_path.exists():
            return
        try:
            self._baseline = json.loads(self._baseline_path.read_text(encoding="utf-8"))
            logger.info(
                "[EpochWatcher] 已載入基準指標：mAP50=%.4f  mAP50-95=%.4f",
                self._baseline.get("map50", 0.0),
                self._baseline.get("map50_95", 0.0),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("[EpochWatcher] 讀取 baseline_metrics.json 失敗：%s", exc)

    def _tick(self) -> None:
        self._load_baseline()
        if not self._results_csv.exists():
            return

        records = self._read_csv()
        if not records:
            return

        latest = records[-1]
        if latest.epoch <= self._last_epoch_seen:
            return

        # 新 epoch 偵測到，等待 last.pt 寫入穩定
        time.sleep(_COPY_DELAY)

        self._records = records
        self._last_epoch_seen = latest.epoch

        self._save_checkpoint(latest)
        self._prune_checkpoints()
        self._write_report()
        self._write_chart()

        logger.info(
            "[EpochWatcher] Epoch %d/%s  mAP50=%.4f  mAP50-95=%.4f",
            latest.epoch,
            self.total_epochs or "?",
            latest.map50,
            latest.map50_95,
        )

    def _final_update(self) -> None:
        """訓練結束後，強制執行一次最終更新。"""
        if not self._results_csv.exists():
            return
        records = self._read_csv()
        if not records:
            return
        self._records = records
        self._write_report()
        self._write_chart()
        logger.info("[EpochWatcher] 最終報告已更新")

    # ── CSV parsing ───────────────────────────────────────────────────────────

    def _read_csv(self) -> list[_EpochRecord]:
        try:
            with self._results_csv.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = [row for row in reader if row.get("epoch", "").strip()]
            return [_EpochRecord(r) for r in rows]
        except Exception as exc:  # noqa: BLE001
            logger.debug("[EpochWatcher] 讀取 CSV 失敗：%s", exc)
            return []

    # ── Checkpoint management ─────────────────────────────────────────────────

    def _save_checkpoint(self, rec: _EpochRecord) -> None:
        if not self._last_pt.exists():
            logger.debug("[EpochWatcher] last.pt 尚未生成，跳過複製")
            return
        dest = self._ckpt_dir / f"{rec.ckpt_stem}.pt"
        try:
            shutil.copy2(self._last_pt, dest)
            logger.debug("[EpochWatcher] 已儲存 checkpoint：%s", dest.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[EpochWatcher] 複製 last.pt 失敗：%s", exc)

    def _prune_checkpoints(self) -> None:
        """只保留 Top-K 與 Bottom-K 的 checkpoint 檔案。"""
        if len(self._records) <= _TOP_K * 2:
            return  # 不足 2K 筆，全部保留

        sorted_asc = sorted(self._records, key=lambda r: r.map50)
        keep_epochs = {r.epoch for r in sorted_asc[:_TOP_K]}        # bottom-K
        keep_epochs |= {r.epoch for r in sorted_asc[-_TOP_K:]}      # top-K

        for pt_file in self._ckpt_dir.glob("epoch_*.pt"):
            try:
                ep_str = pt_file.stem.split("_")[1]
                ep = int(ep_str)
                if ep not in keep_epochs:
                    pt_file.unlink()
                    logger.debug("[EpochWatcher] 刪除 checkpoint：%s", pt_file.name)
            except (IndexError, ValueError):
                pass

    # ── Report generation ─────────────────────────────────────────────────────

    def _tag(self, rec: _EpochRecord) -> str:
        if len(self._records) < 2:
            return ""
        sorted_asc = sorted(self._records, key=lambda r: r.map50)
        bottom_eps = {r.epoch for r in sorted_asc[:_TOP_K]}
        top_eps    = {r.epoch for r in sorted_asc[-_TOP_K:]}
        if rec.epoch in top_eps and rec.epoch in bottom_eps:
            return "🏆 Top / ⚠️ Bot"
        if rec.epoch in top_eps:
            return "🏆 Top"
        if rec.epoch in bottom_eps:
            return "⚠️ Bot"
        return ""

    def _delta_str(self, fine: float, base: float) -> str:
        """計算提升量，回傳帶方向符號的字串。"""
        diff = fine - base
        sign = "▲" if diff >= 0 else "▼"
        return f"{sign} {diff:+.4f}"

    def _write_report(self) -> None:
        if not self._records:
            return

        sorted_asc = sorted(self._records, key=lambda r: r.map50)
        total      = self.total_epochs or "?"
        best       = sorted_asc[-1] if sorted_asc else None

        lines: list[str] = [
            f"# 訓練進度報告（實時更新）\n\n",
            f"**最後更新**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n",
            f"**已完成**：{self._last_epoch_seen} / {total} epoch  \n",
        ]
        if best:
            lines.append(f"**當前最佳** Epoch {best.epoch}：mAP50={best.map50:.4f}  mAP50-95={best.map50_95:.4f}  \n")
        lines.append("\n---\n\n")

        if self._baseline and best:
            b = self._baseline
            lines.append("## 基準 vs 當前最佳微調\n\n")
            lines.append(f"基準模型：`{b.get('model', 'YOLOv13')}` （訓練前原始權重）  \n\n")
            lines.append("| 指標 | 基準 YOLOv13 | 當前最佳微調 | 提升 |\n")
            lines.append("|------|:-----------:|:-----------:|:----:|\n")
            rows = [
                ("mAP50",     b.get("map50",      0.0), best.map50),
                ("mAP50-95",  b.get("map50_95",   0.0), best.map50_95),
                ("Precision", b.get("precision",  0.0), best.precision),
                ("Recall",    b.get("recall",     0.0), best.recall),
            ]
            for name, base_val, fine_val in rows:
                delta = self._delta_str(fine_val, base_val)
                lines.append(f"| {name} | {base_val:.4f} | {fine_val:.4f} | {delta} |\n")
            lines.append("\n---\n\n")

        lines.append("## 各 Epoch 指標\n\n")
        lines.append("| Epoch | mAP50 | mAP50-95 | Precision | Recall | 標記 |\n")
        lines.append("|------:|------:|---------:|----------:|-------:|------|\n")
        for rec in reversed(self._records):  # 最新在上
            tag = self._tag(rec)
            lines.append(
                f"| {rec.epoch:>5} | {rec.map50:.4f} | {rec.map50_95:.4f} "
                f"| {rec.precision:.4f} | {rec.recall:.4f} | {tag} |\n"
            )

        lines.append("\n---\n\n")
        lines.append(f"## Top-{_TOP_K} Checkpoint\n\n")
        lines.append("| 排名 | Epoch | mAP50 | 檔案 |\n")
        lines.append("|-----:|------:|------:|------|\n")
        for rank, rec in enumerate(reversed(sorted_asc[-_TOP_K:]), 1):
            ckpt = f"`checkpoints/{rec.ckpt_stem}.pt`"
            exists = (self._ckpt_dir / f"{rec.ckpt_stem}.pt").exists()
            ckpt_str = ckpt if exists else f"~~{ckpt}~~ (已刪除)"
            lines.append(f"| #{rank} | {rec.epoch} | {rec.map50:.4f} | {ckpt_str} |\n")

        lines.append(f"\n## Bottom-{_TOP_K} Checkpoint\n\n")
        lines.append("| 排名 | Epoch | mAP50 | 檔案 |\n")
        lines.append("|-----:|------:|------:|------|\n")
        for rank, rec in enumerate(sorted_asc[:_TOP_K], 1):
            ckpt = f"`checkpoints/{rec.ckpt_stem}.pt`"
            exists = (self._ckpt_dir / f"{rec.ckpt_stem}.pt").exists()
            ckpt_str = ckpt if exists else f"~~{ckpt}~~ (已刪除)"
            lines.append(f"| #{rank} | {rec.epoch} | {rec.map50:.4f} | {ckpt_str} |\n")

        out = self.run_dir / "epoch_report.md"
        out.write_text("".join(lines), encoding="utf-8")

    def _write_chart(self) -> None:
        if not self._records:
            return
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            logger.debug("[EpochWatcher] matplotlib 不可用，跳過圖表")
            return

        epochs = [r.epoch    for r in self._records]
        map50  = [r.map50    for r in self._records]
        map95  = [r.map50_95 for r in self._records]

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(epochs, map50, "o-", color="#0ea5e9", linewidth=2,  label="mAP50")
        ax.plot(epochs, map95, "s--", color="#f59e0b", linewidth=1.5, label="mAP50-95")

        if self._baseline:
            b_map50   = self._baseline.get("map50", 0.0)
            b_map95   = self._baseline.get("map50_95", 0.0)
            b_model   = self._baseline.get("model", "YOLOv13")
            x_max = max(self.total_epochs or 1, max(epochs) if epochs else 1) + 1
            ax.axhline(b_map50, color="#6b7280", linestyle="--", linewidth=1.2,
                       label=f"Baseline mAP50 ({b_model}: {b_map50:.4f})")
            ax.axhline(b_map95, color="#9ca3af", linestyle=":",  linewidth=1.0,
                       label=f"Baseline mAP50-95 ({b_map95:.4f})")
            ax.text(x_max * 0.01, b_map50 + 0.01, f"{b_map50:.4f}",
                    color="#6b7280", fontsize=7, va="bottom")

        # 標記 Top-3 / Bottom-3
        sorted_asc = sorted(self._records, key=lambda r: r.map50)
        bot_set = {r.epoch for r in sorted_asc[:_TOP_K]}
        top_set = {r.epoch for r in sorted_asc[-_TOP_K:]}
        for rec in self._records:
            if rec.epoch in top_set:
                ax.annotate(f"Top\n{rec.map50:.3f}", xy=(rec.epoch, rec.map50),
                            xytext=(0, 8), textcoords="offset points",
                            ha="center", fontsize=7, color="#16a34a")
            elif rec.epoch in bot_set:
                ax.annotate(f"Bot\n{rec.map50:.3f}", xy=(rec.epoch, rec.map50),
                            xytext=(0, -16), textcoords="offset points",
                            ha="center", fontsize=7, color="#dc2626")

        total = self.total_epochs or (max(epochs) if epochs else 1)
        ax.set_xlim(0, max(total + 1, max(epochs) + 1))
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Score")
        ax.set_title(
            f"訓練曲線（已完成 {self._last_epoch_seen}/{self.total_epochs or '?'} epoch）\n"
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        ax.legend()
        ax.grid(linestyle="--", alpha=0.4)
        fig.tight_layout()

        out = self.run_dir / "training_curve.png"
        fig.savefig(out, dpi=150)
        plt.close(fig)

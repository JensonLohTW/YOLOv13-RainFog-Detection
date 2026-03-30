"""
TrainingVisualizer：訓練視覺化模組。

與 EpochWatcher 完全解耦——透過純資料物件 (EpochMetrics / BaselineMetrics) 驅動，
不依賴任何訓練框架或監控執行緒的內部狀態。

每次呼叫 render() 輸出（全部儲存於 run_dir/）：
  training_curve.png     — 概覽：mAP50 / mAP50-95 折線 + 基準水平線
  chart_metrics.png      — 2×2 詳細指標（mAP50 / mAP50-95 / Precision / Recall + 各自基準線）
  chart_losses.png       — 1×3 損失曲線（box / cls / dfl，train vs val）
  chart_improvement.png  — 2×2 逐 epoch 相對基準 Δ 提升條形圖
  metrics_raw.json       — 完整原始數據（baseline + 各 epoch 指標 + Δ 值）
  metrics_raw.csv        — 同上，CSV 格式（含 delta_ 欄位）
"""
from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Data transfer objects ─────────────────────────────────────────────────────

@dataclass
class EpochMetrics:
    """單一 epoch 的全量指標，作為 EpochWatcher → TrainingVisualizer 的資料載體。"""
    epoch: int
    map50: float
    map50_95: float
    precision: float
    recall: float
    train_box_loss: float = 0.0
    train_cls_loss: float = 0.0
    train_dfl_loss: float = 0.0
    val_box_loss: float = 0.0
    val_cls_loss: float = 0.0
    val_dfl_loss: float = 0.0
    lr: float = 0.0


@dataclass
class BaselineMetrics:
    """訓練前基準評估快照，作為提升量計算的參考零點。"""
    map50: float
    map50_95: float
    precision: float
    recall: float
    model: str = ""


# ── Visualizer ────────────────────────────────────────────────────────────────

class TrainingVisualizer:
    """
    訓練指標視覺化器。

    設計原則：
      - 高內聚：所有視覺化與原始資料匯出邏輯集中於此類
      - 低耦合：呼叫端只需傳入 EpochMetrics / BaselineMetrics，不暴露訓練框架細節
      - 無副作用：每次 render() 獨立完整更新，不累積內部狀態
    """

    def __init__(self, run_dir: Path, total_epochs: int = 0) -> None:
        self._run_dir = Path(run_dir)
        self._total_epochs = total_epochs

    # ── Public API ────────────────────────────────────────────────────────────

    def render(
        self,
        records: list[EpochMetrics],
        baseline: Optional[BaselineMetrics],
        last_epoch: int,
    ) -> None:
        """
        渲染全部視覺化產物，更新 run_dir 下的所有圖表與資料檔。

        Args:
            records    — 目前為止所有已完成 epoch 的指標列表（按 epoch 升冪排列）
            baseline   — 訓練前基準評估（可為 None，此時不產生 Δ 圖與基準線）
            last_epoch — 最新完成的 epoch 編號（用於標題顯示）
        """
        if not records:
            return
        try:
            self._export_raw_data(records, baseline)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Visualizer] 原始資料匯出失敗：%s", exc)
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            self._chart_overview(records, baseline, last_epoch, plt)
            self._chart_metrics(records, baseline, last_epoch, plt)
            self._chart_losses(records, last_epoch, plt)
            if baseline:
                self._chart_improvement(records, baseline, last_epoch, plt)
        except ImportError:
            logger.debug("[Visualizer] matplotlib 不可用，跳過圖表渲染")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Visualizer] 圖表渲染失敗：%s", exc)

    # ── Raw data export ───────────────────────────────────────────────────────

    def _export_raw_data(
        self,
        records: list[EpochMetrics],
        baseline: Optional[BaselineMetrics],
    ) -> None:
        """匯出 metrics_raw.json 與 metrics_raw.csv（含 delta_ 欄位）。"""
        epoch_dicts = [asdict(r) for r in records]
        if baseline:
            for d in epoch_dicts:
                d["delta_map50"]     = round(d["map50"]     - baseline.map50,     6)
                d["delta_map50_95"]  = round(d["map50_95"]  - baseline.map50_95,  6)
                d["delta_precision"] = round(d["precision"] - baseline.precision, 6)
                d["delta_recall"]    = round(d["recall"]    - baseline.recall,    6)

        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "baseline": asdict(baseline) if baseline else None,
            "epochs": epoch_dicts,
        }
        (self._run_dir / "metrics_raw.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if epoch_dicts:
            with (self._run_dir / "metrics_raw.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(epoch_dicts[0].keys()))
                writer.writeheader()
                writer.writerows(epoch_dicts)

    # ── Chart helpers ─────────────────────────────────────────────────────────

    def _x_range(self, epochs: list[int]) -> tuple[float, float]:
        lo = max(0, min(epochs) - 1) if epochs else 0
        hi = max(self._total_epochs or 1, max(epochs) if epochs else 1) + 1
        return float(lo), float(hi)

    @staticmethod
    def _draw_baseline(ax, value: float, label: str, color: str, x_lo: float) -> None:
        ax.axhline(value, color=color, linestyle="--", linewidth=1.0, alpha=0.8, label=label)
        ax.text(x_lo + 0.3, value + 0.003, f"{value:.4f}",
                color=color, fontsize=7, va="bottom", alpha=0.9)

    @staticmethod
    def _annotate_best(ax, epochs: list[int], values: list[float], color: str) -> None:
        if not values:
            return
        best_i = values.index(max(values))
        ax.annotate(
            f"best {values[best_i]:.4f}",
            xy=(epochs[best_i], values[best_i]),
            xytext=(0, 8), textcoords="offset points",
            ha="center", fontsize=7, color=color,
        )

    def _ts(self, last_epoch: int) -> str:
        return (
            f"Epoch {last_epoch}/{self._total_epochs or '?'}  "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    # ── Chart 1: overview (training_curve.png) ────────────────────────────────

    def _chart_overview(
        self,
        records: list[EpochMetrics],
        baseline: Optional[BaselineMetrics],
        last_epoch: int,
        plt,
    ) -> None:
        """簡潔概覽圖（向後相容）：mAP50 / mAP50-95 折線 + 基準水平虛線。"""
        epochs = [r.epoch for r in records]
        map50  = [r.map50    for r in records]
        map95  = [r.map50_95 for r in records]
        x_lo, x_hi = self._x_range(epochs)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(epochs, map50, "o-",  color="#0ea5e9", linewidth=2,   label="mAP50")
        ax.plot(epochs, map95, "s--", color="#f59e0b", linewidth=1.5, label="mAP50-95")

        if baseline:
            self._draw_baseline(ax, baseline.map50,    f"Baseline mAP50 {baseline.map50:.4f}",    "#6b7280", x_lo)
            self._draw_baseline(ax, baseline.map50_95, f"Baseline mAP50-95 {baseline.map50_95:.4f}", "#9ca3af", x_lo)

        # 標記 Top-3
        sorted_asc = sorted(records, key=lambda r: r.map50)
        top_set = {r.epoch for r in sorted_asc[-3:]}
        for rec in records:
            if rec.epoch in top_set:
                ax.annotate(f"Top\n{rec.map50:.3f}", xy=(rec.epoch, rec.map50),
                            xytext=(0, 8), textcoords="offset points",
                            ha="center", fontsize=7, color="#16a34a")

        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Score")
        ax.set_title(f"訓練曲線概覽  {self._ts(last_epoch)}")
        ax.legend()
        ax.grid(linestyle="--", alpha=0.4)
        fig.tight_layout()
        fig.savefig(self._run_dir / "training_curve.png", dpi=150)
        plt.close(fig)

    # ── Chart 2: metrics 2×2 (chart_metrics.png) ─────────────────────────────

    def _chart_metrics(
        self,
        records: list[EpochMetrics],
        baseline: Optional[BaselineMetrics],
        last_epoch: int,
        plt,
    ) -> None:
        """2×2 格圖：mAP50 / mAP50-95 / Precision / Recall，各含基準虛線與最佳標注。"""
        epochs = [r.epoch for r in records]
        x_lo, x_hi = self._x_range(epochs)
        series = [
            ("mAP50",     [r.map50     for r in records], getattr(baseline, "map50",     None), "#0ea5e9"),
            ("mAP50-95",  [r.map50_95  for r in records], getattr(baseline, "map50_95",  None), "#f59e0b"),
            ("Precision", [r.precision for r in records], getattr(baseline, "precision", None), "#10b981"),
            ("Recall",    [r.recall    for r in records], getattr(baseline, "recall",    None), "#8b5cf6"),
        ]
        fig, axes = plt.subplots(2, 2, figsize=(14, 8))
        fig.suptitle(f"訓練指標曲線（含基準對比）  {self._ts(last_epoch)}", fontsize=11)

        for ax, (title, values, base_val, color) in zip(axes.flat, series):
            ax.plot(epochs, values, "o-", color=color, linewidth=1.8, markersize=3, label=title)
            self._annotate_best(ax, epochs, values, "#16a34a")
            if base_val is not None:
                self._draw_baseline(ax, base_val, f"Baseline {base_val:.4f}", "#6b7280", x_lo)
            ax.set_title(title, fontsize=9)
            ax.set_xlabel("Epoch", fontsize=8)
            ax.set_ylim(0, 1.05)
            ax.set_xlim(x_lo, x_hi)
            ax.legend(fontsize=7)
            ax.grid(linestyle="--", alpha=0.35)

        fig.tight_layout()
        fig.savefig(self._run_dir / "chart_metrics.png", dpi=150)
        plt.close(fig)

    # ── Chart 3: losses 1×3 (chart_losses.png) ───────────────────────────────

    def _chart_losses(
        self,
        records: list[EpochMetrics],
        last_epoch: int,
        plt,
    ) -> None:
        """1×3 損失曲線：train vs val，box / cls / dfl。無損失資料時靜默跳過。"""
        has_train = any(r.train_box_loss for r in records)
        has_val   = any(r.val_box_loss   for r in records)
        if not has_train and not has_val:
            return

        epochs = [r.epoch for r in records]
        x_lo, x_hi = self._x_range(epochs)
        loss_defs = [
            ("Box Loss", "train_box_loss", "val_box_loss"),
            ("Cls Loss", "train_cls_loss", "val_cls_loss"),
            ("DFL Loss", "train_dfl_loss", "val_dfl_loss"),
        ]
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        fig.suptitle(f"損失曲線  {self._ts(last_epoch)}", fontsize=11)

        for ax, (title, train_key, val_key) in zip(axes, loss_defs):
            if has_train:
                ax.plot(epochs, [getattr(r, train_key) for r in records],
                        "o-", color="#0ea5e9", linewidth=1.5, markersize=3, label="train")
            if has_val:
                ax.plot(epochs, [getattr(r, val_key) for r in records],
                        "s--", color="#f59e0b", linewidth=1.5, markersize=3, label="val")
            ax.set_title(title, fontsize=9)
            ax.set_xlabel("Epoch", fontsize=8)
            ax.set_xlim(x_lo, x_hi)
            ax.legend(fontsize=8)
            ax.grid(linestyle="--", alpha=0.35)

        fig.tight_layout()
        fig.savefig(self._run_dir / "chart_losses.png", dpi=150)
        plt.close(fig)

    # ── Chart 4: improvement 2×2 (chart_improvement.png) ─────────────────────

    def _chart_improvement(
        self,
        records: list[EpochMetrics],
        baseline: BaselineMetrics,
        last_epoch: int,
        plt,
    ) -> None:
        """2×2 逐 epoch 相對基準 Δ 提升條形圖：正值綠色，負值紅色，標注最佳 epoch。"""
        epochs = [r.epoch for r in records]
        x_lo, x_hi = self._x_range(epochs)
        series = [
            ("Δ mAP50",     [r.map50     - baseline.map50     for r in records], "#0ea5e9"),
            ("Δ mAP50-95",  [r.map50_95  - baseline.map50_95  for r in records], "#f59e0b"),
            ("Δ Precision", [r.precision - baseline.precision for r in records], "#10b981"),
            ("Δ Recall",    [r.recall    - baseline.recall    for r in records], "#8b5cf6"),
        ]
        fig, axes = plt.subplots(2, 2, figsize=(14, 8))
        fig.suptitle(
            f"相對基準提升量 Δ  {self._ts(last_epoch)}\n"
            f"Baseline：mAP50={baseline.map50:.4f}  mAP50-95={baseline.map50_95:.4f}  "
            f"P={baseline.precision:.4f}  R={baseline.recall:.4f}",
            fontsize=10,
        )
        for ax, (title, deltas, color) in zip(axes.flat, series):
            bar_colors = [color if d >= 0 else "#ef4444" for d in deltas]
            ax.bar(epochs, deltas, color=bar_colors, alpha=0.75, width=0.6)
            ax.axhline(0, color="#111827", linewidth=1.0)

            if deltas:
                best_i = deltas.index(max(deltas))
                sign = "+" if deltas[best_i] >= 0 else ""
                ax.annotate(
                    f"{sign}{deltas[best_i]:.4f}\nEp{epochs[best_i]}",
                    xy=(epochs[best_i], deltas[best_i]),
                    xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=7, color="#16a34a",
                )
                worst_i = deltas.index(min(deltas))
                if worst_i != best_i:
                    ax.annotate(
                        f"{deltas[worst_i]:.4f}\nEp{epochs[worst_i]}",
                        xy=(epochs[worst_i], deltas[worst_i]),
                        xytext=(0, -14), textcoords="offset points",
                        ha="center", fontsize=7, color="#dc2626",
                    )

            ax.set_title(title, fontsize=9)
            ax.set_xlabel("Epoch", fontsize=8)
            ax.set_xlim(x_lo - 0.5, x_hi)
            ax.grid(axis="y", linestyle="--", alpha=0.35)

        fig.tight_layout()
        fig.savefig(self._run_dir / "chart_improvement.png", dpi=150)
        plt.close(fig)

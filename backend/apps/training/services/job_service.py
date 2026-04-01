"""訓練任務服務：subprocess 管理、進度讀取、模型部署。"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.training.models import TrainingDataset, TrainingJob
from common.weather_preprocess import PreprocessOptions

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(settings.REPO_ROOT)
_BACKEND_DIR = _REPO_ROOT / "backend"
_TRAIN_RUNS_DIR = _REPO_ROOT / "data" / "train_runs"
_MODELS_DIR = _REPO_ROOT / "data" / "models"
_PREPARED_DATASETS_DIR = _REPO_ROOT / "data" / "datasets" / "_prepared"
_ENV_FILE = _BACKEND_DIR / ".env"


class TrainingJobService:
    def create_job(
        self,
        dataset: TrainingDataset,
        model_file: str = "yolov13l.pt",
        epochs: int = 50,
        batch: int = 4,
        imgsz: int = 640,
        device: str = "0",
        workers: int = 0,
        patience: int = 20,
        preprocess_mode: str = "off",
        preprocess_profile: str = "",
        preprocess_algorithms: list[str] | None = None,
        preprocess_algorithm_params: dict | None = None,
        preprocess_enable_gamma: bool = False,
    ) -> TrainingJob:
        run_name = f"rainfog_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_dir = _TRAIN_RUNS_DIR / run_name
        preprocess = PreprocessOptions(
            mode=preprocess_mode,
            profile=preprocess_profile,
            algorithms=list(preprocess_algorithms or []),
            algorithm_params=dict(preprocess_algorithm_params or {}),
            enable_gamma=preprocess_enable_gamma,
        )
        prepared_dataset_path = ""
        preprocess_manifest_path = ""
        if preprocess.is_enabled():
            prepared_name = f"{dataset.name}__{preprocess.signature()}"
            prepared_dataset_path = str(_PREPARED_DATASETS_DIR / prepared_name)
            preprocess_manifest_path = str(_PREPARED_DATASETS_DIR / prepared_name / "preprocess_manifest.json")
        job = TrainingJob.objects.create(
            dataset=dataset,
            model_file=model_file,
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
            device=device,
            workers=workers,
            patience=patience,
            preprocess_mode=preprocess.normalized_mode(),
            preprocess_profile=preprocess.normalized_profile(),
            preprocess_algorithms=preprocess.normalized_algorithms(),
            preprocess_algorithm_params=preprocess.algorithm_params,
            preprocess_enable_gamma=preprocess.enable_gamma,
            run_name=run_name,
            run_dir=str(run_dir),
            log_path=str(run_dir / f"{run_name}.log"),
            prepared_dataset_path=prepared_dataset_path,
            preprocess_manifest_path=preprocess_manifest_path,
            total_epochs=epochs,
            status=TrainingJob.Status.PENDING,
        )
        return job

    def start_job(self, job: TrainingJob) -> TrainingJob:
        dataset_name = job.dataset.name if job.dataset else "rainfog_detection"
        run_dir = Path(job.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        config_path = run_dir / "training_request.json"
        config_payload = {
            "model": job.model_file,
            "dataset": dataset_name,
            "epochs": job.epochs,
            "batch": job.batch,
            "imgsz": job.imgsz,
            "device": job.device,
            "workers": job.workers,
            "patience": job.patience,
            "project": str(_TRAIN_RUNS_DIR),
            "name": job.run_name,
            "preprocess": {
                "mode": job.preprocess_mode,
                "profile": job.preprocess_profile,
                "algorithms": job.preprocess_algorithms,
                "algorithm_params": job.preprocess_algorithm_params,
                "enable_gamma": job.preprocess_enable_gamma,
            },
            "prepared_datasets_root": str(_PREPARED_DATASETS_DIR),
        }
        config_path.write_text(json.dumps(config_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        cmd = [
            sys.executable, "-m", "training.train",
            "--config", str(config_path),
            "--model", job.model_file,
            "--dataset", dataset_name,
            "--epochs", str(job.epochs),
            "--batch", str(job.batch),
            "--imgsz", str(job.imgsz),
            "--workers", str(job.workers),
            "--patience", str(job.patience),
            "--name", job.run_name,
        ]
        if job.device:
            cmd += ["--device", job.device]

        env = os.environ.copy()
        env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

        log_file = open(job.log_path, "a", encoding="utf-8")  # noqa: WPS515
        proc = subprocess.Popen(
            cmd,
            cwd=str(_BACKEND_DIR),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        job.pid = proc.pid
        job.status = TrainingJob.Status.RUNNING
        job.started_at = timezone.now()
        job.save(update_fields=["pid", "status", "started_at", "updated_at"])
        logger.info("訓練任務 %s 已啟動，PID=%s", job.job_no, proc.pid)
        return job

    def refresh_job(self, job: TrainingJob) -> TrainingJob:
        job = self.refresh_progress(job)
        job = self.refresh_baseline(job)
        return job

    def refresh_jobs(self, jobs: list[TrainingJob]) -> list[TrainingJob]:
        return [self.refresh_job(job) for job in jobs]

    def retry_job(self, job: TrainingJob) -> TrainingJob:
        if job.status in (TrainingJob.Status.PENDING, TrainingJob.Status.RUNNING):
            raise ValueError("執行中的任務不可重試。")
        if not job.dataset or job.dataset.status != TrainingDataset.Status.READY:
            raise ValueError("原任務資料集不存在或尚未就緒，無法重試。")
        retried_job = self.create_job(
            dataset=job.dataset,
            model_file=job.model_file,
            epochs=job.epochs,
            batch=job.batch,
            imgsz=job.imgsz,
            device=job.device,
            workers=job.workers,
            patience=job.patience,
            preprocess_mode=job.preprocess_mode,
            preprocess_profile=job.preprocess_profile,
            preprocess_algorithms=job.preprocess_algorithms,
            preprocess_algorithm_params=job.preprocess_algorithm_params,
            preprocess_enable_gamma=job.preprocess_enable_gamma,
        )
        return self.start_job(retried_job)

    def get_visualization_payload(self, job: TrainingJob) -> dict[str, Any]:
        job = self.refresh_job(job)
        run_dir = Path(job.run_dir)
        epochs, baseline, generated_at, source = self._read_epoch_metrics(run_dir)
        summary_rows = self._read_summary_csv(run_dir / "training_summary.csv")
        warnings = self._build_warnings(job, epochs, baseline)
        return {
            "generated_at": generated_at or timezone.now().isoformat(),
            "source": source,
            "artifacts": self._build_artifacts_payload(run_dir),
            "baseline": baseline,
            "epochs": epochs,
            "summary": self._build_training_summary(job, epochs, baseline, summary_rows, warnings),
            "summary_rows": summary_rows,
            "report_excerpt": self._read_text_excerpt(run_dir / "epoch_report.md", max_lines=60),
        }

    def refresh_progress(self, job: TrainingJob) -> TrainingJob:
        """讀取 results.csv 更新 epoch/mAP，並偵測進程是否已結束。"""
        if job.status not in (TrainingJob.Status.RUNNING, TrainingJob.Status.PENDING):
            return job

        run_dir = Path(job.run_dir)
        results_csv = run_dir / "results.csv"

        update_fields = ["updated_at"]

        if results_csv.exists():
            try:
                row = self._read_last_csv_row(results_csv)
                if row:
                    epoch_val = self._parse_float(row.get("epoch", ""))
                    map50_val = self._parse_float(row.get("metrics/mAP50(B)", ""))
                    map95_val = self._parse_float(row.get("metrics/mAP50-95(B)", ""))
                    if epoch_val is not None:
                        job.current_epoch = max(0, min(job.total_epochs or int(epoch_val), int(epoch_val)))
                        update_fields.append("current_epoch")
                    if map50_val is not None:
                        job.best_map50 = map50_val
                        update_fields.append("best_map50")
                    if map95_val is not None:
                        job.best_map50_95 = map95_val
                        update_fields.append("best_map50_95")
            except Exception as exc:  # noqa: BLE001
                logger.debug("讀取 results.csv 失敗：%s", exc)

        if job.pid:
            alive = self._is_process_alive(job.pid)
            if not alive:
                best_pt = run_dir / "weights" / "best.pt"
                if best_pt.exists():
                    job.status = TrainingJob.Status.COMPLETED
                    job.best_pt_path = str(best_pt)
                    job.current_epoch = job.total_epochs
                    update_fields += ["status", "best_pt_path", "current_epoch"]
                else:
                    log_tail = self._read_log_tail(job.log_path)
                    job.status = TrainingJob.Status.FAILED
                    job.error_message = log_tail
                    update_fields += ["status", "error_message"]
                job.finished_at = timezone.now()
                update_fields.append("finished_at")

        job.save(update_fields=list(set(update_fields)))
        return job

    def validate_baseline(self, job: TrainingJob) -> TrainingJob:
        """在原始基礎模型上跑 val()，結果寫入 baseline_metrics.json。"""
        if job.baseline_status == "RUNNING":
            raise ValueError("基線驗證已在執行中。")

        dataset_name = job.dataset.name if job.dataset else "rainfog_detection"
        output_path = Path(job.run_dir) / "baseline_metrics.json"
        model_path = _MODELS_DIR / job.model_file

        cmd = [
            sys.executable, "-m", "training.validate",
            "--model", str(model_path),
            "--dataset", dataset_name,
            "--output", str(output_path),
            "--device", job.device,
            "--imgsz", str(job.imgsz),
            "--preprocess-mode", "off",
        ]

        log_path = Path(job.run_dir) / "baseline_validate.log"
        Path(job.run_dir).mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "a", encoding="utf-8")  # noqa: WPS515
        subprocess.Popen(
            cmd,
            cwd=str(_BACKEND_DIR),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        job.baseline_status = "RUNNING"
        job.save(update_fields=["baseline_status", "updated_at"])
        logger.info("基線驗證已啟動（job=%s, model=%s）", job.job_no, job.model_file)
        return job

    def refresh_baseline(self, job: TrainingJob) -> TrainingJob:
        """讀取 baseline_metrics.json，若存在則更新基線指標。"""
        if job.baseline_status not in ("RUNNING", "NONE"):
            return job

        result_path = Path(job.run_dir) / "baseline_metrics.json"
        if not result_path.exists():
            return job

        try:
            import json as _json
            data = _json.loads(result_path.read_text(encoding="utf-8"))
            job.baseline_map50 = data.get("map50")
            job.baseline_map50_95 = data.get("map50_95")
            job.baseline_precision = data.get("precision")
            job.baseline_recall = data.get("recall")
            job.baseline_status = "DONE"
            job.save(update_fields=[
                "baseline_map50", "baseline_map50_95",
                "baseline_precision", "baseline_recall",
                "baseline_status", "updated_at",
            ])
            logger.info("基線指標已更新（job=%s）: mAP50=%.4f", job.job_no, job.baseline_map50 or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("讀取 baseline_metrics.json 失敗：%s", exc)
            job.baseline_status = "FAILED"
            job.save(update_fields=["baseline_status", "updated_at"])
        return job

    def cancel_job(self, job: TrainingJob) -> TrainingJob:
        if job.pid and self._is_process_alive(job.pid):
            try:
                if sys.platform == "win32":
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(job.pid)])
                else:
                    os.killpg(os.getpgid(job.pid), signal.SIGTERM)
            except Exception as exc:  # noqa: BLE001
                logger.warning("無法終止進程 %s：%s", job.pid, exc)

        job.status = TrainingJob.Status.CANCELED
        job.pid = None
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "pid", "finished_at", "updated_at"])
        return job

    def deploy_job(self, job: TrainingJob, model_alias: str | None = None) -> dict:
        """將 best.pt 複製到 data/models/ 並更新 .env。"""
        if job.status != TrainingJob.Status.COMPLETED:
            raise ValueError("只有 COMPLETED 狀態的任務才能部署。")

        best_pt = Path(job.best_pt_path)
        if not best_pt.exists():
            raise FileNotFoundError(f"best.pt 不存在：{best_pt}")

        if not model_alias:
            model_alias = f"yolov13_rainfog_{job.job_no}.pt"

        dest = _MODELS_DIR / model_alias
        _MODELS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best_pt, dest)

        self._update_env(model_alias)

        logger.info("模型已部署：%s → %s", best_pt, dest)
        return {"model_file": model_alias, "model_path": str(dest)}

    def _update_env(self, model_file: str) -> None:
        if not _ENV_FILE.exists():
            return
        content = _ENV_FILE.read_text(encoding="utf-8")

        def replace_or_append(key: str, value: str, text: str) -> str:
            pattern = rf"^{re.escape(key)}=.*$"
            replacement = f"{key}={value}"
            new_text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
            if count == 0:
                new_text = new_text.rstrip("\n") + f"\n{replacement}\n"
            return new_text

        content = replace_or_append("INFERENCE_MODEL_MODE", "yolov13", content)
        content = replace_or_append("INFERENCE_YOLOV13_MODEL_FILE", model_file, content)
        _ENV_FILE.write_text(content, encoding="utf-8")

    def _read_epoch_metrics(self, run_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str | None, str]:
        results_csv = run_dir / "results.csv"
        metrics_raw_path = run_dir / "metrics_raw.json"
        baseline_path = run_dir / "baseline_metrics.json"

        baseline_payload = self._read_json_file(baseline_path)
        csv_epochs = self._read_results_csv(results_csv)
        csv_epoch_map = {item["epoch"]: item for item in csv_epochs if item.get("epoch") is not None}

        if metrics_raw_path.exists():
            payload = self._read_json_file(metrics_raw_path) or {}
            raw_epochs = payload.get("epochs", []) if isinstance(payload, dict) else []
            epochs = [self._normalize_epoch_metric(item, csv_epoch_map) for item in raw_epochs if isinstance(item, dict)]
            normalized_baseline = payload.get("baseline") if isinstance(payload, dict) else None
            baseline = normalized_baseline if isinstance(normalized_baseline, dict) else baseline_payload
            self._apply_delta_fields(epochs, baseline)
            return epochs, baseline, payload.get("generated_at"), "metrics_raw.json"

        self._apply_delta_fields(csv_epochs, baseline_payload)
        return csv_epochs, baseline_payload, None, "results.csv"

    def _read_results_csv(self, csv_path: Path) -> list[dict[str, Any]]:
        if not csv_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with csv_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if not str(row.get("epoch", "")).strip():
                    continue
                rows.append(
                    {
                        "epoch": int(self._parse_float(row.get("epoch", "")) or 0),
                        "time_sec": self._parse_float(row.get("time", "")),
                        "map50": self._parse_float(row.get("metrics/mAP50(B)", "")),
                        "map50_95": self._parse_float(row.get("metrics/mAP50-95(B)", "")),
                        "precision": self._parse_float(row.get("metrics/precision(B)", "")),
                        "recall": self._parse_float(row.get("metrics/recall(B)", "")),
                        "train_box_loss": self._parse_float(row.get("train/box_loss", "")),
                        "train_cls_loss": self._parse_float(row.get("train/cls_loss", "")),
                        "train_dfl_loss": self._parse_float(row.get("train/dfl_loss", "")),
                        "val_box_loss": self._parse_float(row.get("val/box_loss", "")),
                        "val_cls_loss": self._parse_float(row.get("val/cls_loss", "")),
                        "val_dfl_loss": self._parse_float(row.get("val/dfl_loss", "")),
                        "lr": self._parse_float(row.get("lr/pg0", "")),
                    }
                )
        return rows

    def _normalize_epoch_metric(self, item: dict[str, Any], csv_epoch_map: dict[int, dict[str, Any]]) -> dict[str, Any]:
        epoch = int(self._parse_float(item.get("epoch", 0)) or 0)
        csv_row = csv_epoch_map.get(epoch, {})
        normalized = {
            "epoch": epoch,
            "time_sec": item.get("time_sec", csv_row.get("time_sec")),
            "map50": item.get("map50"),
            "map50_95": item.get("map50_95"),
            "precision": item.get("precision"),
            "recall": item.get("recall"),
            "train_box_loss": item.get("train_box_loss"),
            "train_cls_loss": item.get("train_cls_loss"),
            "train_dfl_loss": item.get("train_dfl_loss"),
            "val_box_loss": item.get("val_box_loss"),
            "val_cls_loss": item.get("val_cls_loss"),
            "val_dfl_loss": item.get("val_dfl_loss"),
            "lr": item.get("lr"),
            "delta_map50": item.get("delta_map50"),
            "delta_map50_95": item.get("delta_map50_95"),
            "delta_precision": item.get("delta_precision"),
            "delta_recall": item.get("delta_recall"),
        }
        for key in (
            "time_sec", "map50", "map50_95", "precision", "recall",
            "train_box_loss", "train_cls_loss", "train_dfl_loss",
            "val_box_loss", "val_cls_loss", "val_dfl_loss", "lr",
            "delta_map50", "delta_map50_95", "delta_precision", "delta_recall",
        ):
            normalized[key] = self._parse_float(normalized.get(key))
        return normalized

    def _apply_delta_fields(self, epochs: list[dict[str, Any]], baseline: dict[str, Any] | None) -> None:
        if not baseline:
            return
        pairs = (
            ("map50", "delta_map50", baseline.get("map50")),
            ("map50_95", "delta_map50_95", baseline.get("map50_95")),
            ("precision", "delta_precision", baseline.get("precision")),
            ("recall", "delta_recall", baseline.get("recall")),
        )
        for epoch in epochs:
            for source_key, delta_key, baseline_value in pairs:
                source_value = self._parse_float(epoch.get(source_key))
                base_value = self._parse_float(baseline_value)
                if source_value is None or base_value is None:
                    epoch.setdefault(delta_key, None)
                else:
                    epoch[delta_key] = round(source_value - base_value, 6)

    def _read_summary_csv(self, csv_path: Path) -> dict[str, Any]:
        if not csv_path.exists():
            return {}
        summary: dict[str, Any] = {}
        with csv_path.open(encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) < 2:
                    continue
                summary[row[0]] = self._maybe_number(row[1])
        return summary

    def _build_training_summary(
        self,
        job: TrainingJob,
        epochs: list[dict[str, Any]],
        baseline: dict[str, Any] | None,
        summary_rows: dict[str, Any],
        warnings: list[str],
    ) -> dict[str, Any]:
        first_epoch = epochs[0] if epochs else None
        latest_epoch = epochs[-1] if epochs else None
        best_epoch = max(
            epochs,
            key=lambda item: item.get("map50") if item.get("map50") is not None else float("-inf"),
            default=None,
        )
        trend_conclusion: list[str] = []
        if first_epoch and latest_epoch:
            first_map50 = self._parse_float(first_epoch.get("map50"))
            latest_map50 = self._parse_float(latest_epoch.get("map50"))
            if first_map50 is not None and latest_map50 is not None:
                diff = latest_map50 - first_map50
                direction = "上升" if diff >= 0 else "下降"
                trend_conclusion.append(f"mAP50 相較首輪整體{direction} {diff:+.4f}。")
            first_loss = self._parse_float(first_epoch.get("val_box_loss"))
            latest_loss = self._parse_float(latest_epoch.get("val_box_loss"))
            if first_loss is not None and latest_loss is not None:
                diff = latest_loss - first_loss
                direction = "下降" if diff <= 0 else "上升"
                trend_conclusion.append(f"Val box loss 相較首輪整體{direction} {diff:+.4f}。")
        if baseline and best_epoch:
            baseline_map50 = self._parse_float(baseline.get("map50"))
            best_map50 = self._parse_float(best_epoch.get("map50"))
            if baseline_map50 is not None and best_map50 is not None:
                trend_conclusion.append(f"最佳 mAP50 相對基線變化 {best_map50 - baseline_map50:+.4f}。")
        if latest_epoch and self._parse_float(latest_epoch.get("lr")) is not None:
            trend_conclusion.append(f"最新學習率為 {float(latest_epoch['lr']):.6f}。")
        return {
            "status": job.status,
            "current_epoch": job.current_epoch,
            "total_epochs": job.total_epochs,
            "completed_epochs": len(epochs),
            "best_epoch": best_epoch.get("epoch") if best_epoch else None,
            "best_metrics": best_epoch,
            "latest_metrics": latest_epoch,
            "runtime_seconds": self._resolve_runtime_seconds(job, latest_epoch),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "final_metrics": {
                "map50": self._parse_float(summary_rows.get("mAP50", job.best_map50)),
                "map50_95": self._parse_float(summary_rows.get("mAP50-95", job.best_map50_95)),
                "precision": self._parse_float(summary_rows.get("Precision", latest_epoch.get("precision") if latest_epoch else None)),
                "recall": self._parse_float(summary_rows.get("Recall", latest_epoch.get("recall") if latest_epoch else None)),
            },
            "trend_conclusion": trend_conclusion,
            "warnings": warnings,
            "summary_rows": summary_rows,
        }

    def _build_artifacts_payload(self, run_dir: Path) -> dict[str, bool]:
        return {
            "results_csv": (run_dir / "results.csv").exists(),
            "metrics_raw_json": (run_dir / "metrics_raw.json").exists(),
            "epoch_report_md": (run_dir / "epoch_report.md").exists(),
            "training_summary_csv": (run_dir / "training_summary.csv").exists(),
            "training_curve_png": (run_dir / "training_curve.png").exists(),
            "chart_metrics_png": (run_dir / "chart_metrics.png").exists(),
            "chart_losses_png": (run_dir / "chart_losses.png").exists(),
            "chart_improvement_png": (run_dir / "chart_improvement.png").exists(),
        }

    def _build_warnings(
        self,
        job: TrainingJob,
        epochs: list[dict[str, Any]],
        baseline: dict[str, Any] | None,
    ) -> list[str]:
        warnings: list[str] = []
        if job.status == TrainingJob.Status.CANCELED:
            warnings.append("訓練已被中斷，指標與摘要僅反映中斷前已完成的 epoch。")
        if job.status == TrainingJob.Status.FAILED:
            warnings.append("訓練失敗，請優先檢查錯誤訊息與日誌內容。")
        if not epochs:
            warnings.append("目前尚無可視化 epoch 資料，可能尚未產生 results.csv 或訓練尚未完成第一輪。")
        if baseline and epochs:
            best_epoch = max(
                epochs,
                key=lambda item: item.get("map50") if item.get("map50") is not None else float("-inf"),
                default=None,
            )
            if best_epoch:
                baseline_map50 = self._parse_float(baseline.get("map50"))
                best_map50 = self._parse_float(best_epoch.get("map50"))
                if baseline_map50 is not None and best_map50 is not None and best_map50 < baseline_map50:
                    warnings.append("最佳 mAP50 尚未超過原始基線模型表現。")
        if job.error_message:
            warnings.append(job.error_message[:200])
        return warnings

    def _resolve_runtime_seconds(self, job: TrainingJob, latest_epoch: dict[str, Any] | None) -> float | None:
        if latest_epoch and self._parse_float(latest_epoch.get("time_sec")) is not None:
            return float(latest_epoch["time_sec"])
        if job.started_at and job.finished_at:
            return round((job.finished_at - job.started_at).total_seconds(), 3)
        if job.started_at:
            return round((timezone.now() - job.started_at).total_seconds(), 3)
        return None

    @staticmethod
    def _read_json_file(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("讀取 JSON 失敗：%s (%s)", path, exc)
            return None

    @staticmethod
    def _read_text_excerpt(path: Path, max_lines: int = 40) -> str:
        try:
            if not path.exists():
                return ""
            return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:max_lines])
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _maybe_number(value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()
        if text == "":
            return ""
        try:
            number = float(text)
            return int(number) if number.is_integer() else number
        except ValueError:
            return text

    def _read_last_csv_row(self, csv_path: Path) -> dict | None:
        with csv_path.open(encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r.get("epoch", "").strip()]
        return rows[-1] if rows else None

    @staticmethod
    def _parse_float(value: str) -> float | None:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True, text=True,
                )
                return str(pid) in result.stdout
            else:
                os.kill(pid, 0)
                return True
        except (ProcessLookupError, PermissionError, OSError):
            return False

    @staticmethod
    def _read_log_tail(log_path: str, lines: int = 30) -> str:
        try:
            path = Path(log_path)
            if not path.exists():
                return ""
            all_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(all_lines[-lines:])
        except Exception:  # noqa: BLE001
            return ""

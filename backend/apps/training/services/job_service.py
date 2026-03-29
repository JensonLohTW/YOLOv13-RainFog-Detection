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
                        job.current_epoch = int(epoch_val)
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
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at", "updated_at"])
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

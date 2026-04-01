import { useAuthStore } from "@/stores/auth-store";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const REQUEST_TIMEOUT_MS = 20000;
const UPLOAD_TIMEOUT_MS = 120000;

type ApiEnvelope<T> = { code: number; message: string; data: T };

function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Token ${token}` } : {};
}

async function unwrap<T>(res: Response): Promise<T> {
  const payload = (await res.json()) as ApiEnvelope<T>;
  if (!res.ok) throw new Error(payload.message ?? `HTTP ${res.status}`);
  return payload.data;
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, { ...init, signal: controller.signal });
    return await unwrap<T>(res);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("請求逾時，請稍後再試。");
    }
    throw error instanceof Error ? error : new Error("請求失敗");
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function get<T>(path: string, timeoutMs?: number): Promise<T> {
  return request(path, { headers: getAuthHeaders() }, timeoutMs);
}

function post<T>(path: string, body: unknown = {}, timeoutMs?: number): Promise<T> {
  return request(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(body),
    },
    timeoutMs,
  );
}

function del<T>(path: string): Promise<T> {
  return request(path, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
}

// ─── Types ───────────────────────────────────────────────────────────────────

export type DatasetStatus = "UPLOADING" | "READY" | "FAILED";
export type JobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELED";
export type PreprocessMode = "off" | "auto" | "manual";

export interface TrainingDataset {
  id: number;
  name: string;
  description: string;
  zip_original_name: string;
  dataset_path: string;
  num_train: number;
  num_val: number;
  num_classes: number;
  class_names: string[];
  status: DatasetStatus;
  error_message: string;
  created_at: string;
}

export type BaselineStatus = "NONE" | "RUNNING" | "DONE" | "FAILED";

export interface TrainingJob {
  id: number;
  job_no: string;
  dataset_id: number | null;
  dataset_name: string;
  model_file: string;
  epochs: number;
  batch: number;
  imgsz: number;
  device: string;
  workers: number;
  patience: number;
  preprocess_mode: PreprocessMode;
  preprocess_profile: string;
  preprocess_algorithms: string[];
  preprocess_algorithm_params: Record<string, Record<string, unknown>>;
  preprocess_enable_gamma: boolean;
  run_name: string;
  run_dir: string;
  log_path: string;
  best_pt_path: string;
  status: JobStatus;
  pid: number | null;
  current_epoch: number;
  total_epochs: number;
  best_map50: number | null;
  best_map50_95: number | null;
  error_message: string;
  baseline_map50: number | null;
  baseline_map50_95: number | null;
  baseline_precision: number | null;
  baseline_recall: number | null;
  baseline_status: BaselineStatus;
  improvement_map50: number | null;
  progress_pct: number;
  can_cancel: boolean;
  can_retry: boolean;
  can_deploy: boolean;
  has_metrics: boolean;
  has_summary: boolean;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface CreateJobParams {
  dataset_id: number;
  model_file: string;
  epochs: number;
  batch: number;
  imgsz: number;
  device: string;
  workers: number;
  patience: number;
  preprocess_mode: PreprocessMode;
  preprocess_profile: string;
  preprocess_algorithms: string[];
  preprocess_algorithm_params: Record<string, Record<string, unknown>>;
  preprocess_enable_gamma: boolean;
}

export interface TrainingVisualizationBaseline {
  map50: number | null;
  map50_95: number | null;
  precision: number | null;
  recall: number | null;
  model?: string;
}

export interface TrainingEpochMetric {
  epoch: number;
  time_sec: number | null;
  map50: number | null;
  map50_95: number | null;
  precision: number | null;
  recall: number | null;
  train_box_loss: number | null;
  train_cls_loss: number | null;
  train_dfl_loss: number | null;
  val_box_loss: number | null;
  val_cls_loss: number | null;
  val_dfl_loss: number | null;
  lr: number | null;
  delta_map50: number | null;
  delta_map50_95: number | null;
  delta_precision: number | null;
  delta_recall: number | null;
}

export interface TrainingVisualizationSummary {
  status: JobStatus;
  current_epoch: number;
  total_epochs: number;
  completed_epochs: number;
  best_epoch: number | null;
  best_metrics: TrainingEpochMetric | null;
  latest_metrics: TrainingEpochMetric | null;
  runtime_seconds: number | null;
  started_at: string | null;
  finished_at: string | null;
  final_metrics: {
    map50: number | null;
    map50_95: number | null;
    precision: number | null;
    recall: number | null;
  };
  trend_conclusion: string[];
  warnings: string[];
  summary_rows: Record<string, string | number | null>;
}

export interface TrainingVisualizationPayload {
  generated_at: string;
  source: string;
  artifacts: Record<string, boolean>;
  baseline: TrainingVisualizationBaseline | null;
  epochs: TrainingEpochMetric[];
  summary: TrainingVisualizationSummary;
  summary_rows: Record<string, string | number | null>;
  report_excerpt: string;
}

// ─── Dataset API ─────────────────────────────────────────────────────────────

export function uploadDataset(
  file: File,
  name: string,
  description: string,
  valRatio: number,
): Promise<TrainingDataset> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  formData.append("description", description);
  formData.append("val_ratio", String(valRatio));
  return request(
    "/training/datasets/upload",
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    },
    UPLOAD_TIMEOUT_MS,
  );
}

export function listDatasets(): Promise<{ items: TrainingDataset[]; total: number }> {
  return get("/training/datasets");
}

export function getDataset(id: number): Promise<TrainingDataset> {
  return get(`/training/datasets/${id}`);
}

export function deleteDataset(id: number): Promise<unknown> {
  return del(`/training/datasets/${id}`);
}

// ─── Job API ─────────────────────────────────────────────────────────────────

export function listJobs(statusFilter?: string): Promise<{ items: TrainingJob[]; total: number }> {
  const qs = statusFilter ? `?status=${statusFilter}` : "";
  return get(`/training/jobs${qs}`);
}

export function getJob(id: number): Promise<TrainingJob> {
  return get(`/training/jobs/${id}`);
}

export function createJob(params: CreateJobParams): Promise<TrainingJob> {
  return post("/training/jobs", params);
}

export function cancelJob(id: number): Promise<TrainingJob> {
  return post(`/training/jobs/${id}/cancel`);
}

export function retryJob(id: number): Promise<TrainingJob> {
  return post(`/training/jobs/${id}/retry`);
}

export function deployJob(id: number, modelAlias?: string): Promise<{ model_file: string; model_path: string }> {
  return post(`/training/jobs/${id}/deploy`, { model_alias: modelAlias ?? "" });
}

export function getJobLog(id: number): Promise<{ log: string; log_path: string }> {
  return get(`/training/jobs/${id}/log`);
}

export function validateBaseline(id: number): Promise<TrainingJob> {
  return post(`/training/jobs/${id}/validate-baseline`);
}

export function getJobVisualization(id: number): Promise<TrainingVisualizationPayload> {
  return get(`/training/jobs/${id}/visualization`);
}

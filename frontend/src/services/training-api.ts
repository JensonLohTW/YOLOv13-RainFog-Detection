import { useAuthStore } from "@/stores/auth-store";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

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

function get<T>(path: string): Promise<T> {
  return fetch(`${API_BASE_URL}${path}`, { headers: getAuthHeaders() }).then(unwrap<T>);
}

function post<T>(path: string, body: unknown = {}): Promise<T> {
  return fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(body),
  }).then(unwrap<T>);
}

function del<T>(path: string): Promise<T> {
  return fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  }).then(unwrap<T>);
}

// ─── Types ───────────────────────────────────────────────────────────────────

export type DatasetStatus = "UPLOADING" | "READY" | "FAILED";
export type JobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELED";

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
  dataset_name: string;
  model_file: string;
  epochs: number;
  batch: number;
  imgsz: number;
  device: string;
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
  return fetch(`${API_BASE_URL}/training/datasets/upload`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  }).then(unwrap<TrainingDataset>);
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

export function deployJob(id: number, modelAlias?: string): Promise<{ model_file: string; model_path: string }> {
  return post(`/training/jobs/${id}/deploy`, { model_alias: modelAlias ?? "" });
}

export function getJobLog(id: number): Promise<{ log: string; log_path: string }> {
  return get(`/training/jobs/${id}/log`);
}

export function validateBaseline(id: number): Promise<TrainingJob> {
  return post(`/training/jobs/${id}/validate-baseline`);
}

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Database,
  FileArchive,
  Loader2,
  Play,
  RefreshCw,
  Rocket,
  ServerCrash,
  Square,
  Trash2,
  Upload,
} from "lucide-react";

import {
  cancelJob,
  createJob,
  deleteDataset,
  deployJob,
  getJobLog,
  listDatasets,
  listJobs,
  uploadDataset,
  validateBaseline,
  type CreateJobParams,
  type JobStatus,
  type TrainingJob,
  type TrainingDataset,
} from "@/services/training-api";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    READY: "bg-green-100 text-green-700",
    UPLOADING: "bg-yellow-100 text-yellow-700",
    FAILED: "bg-red-100 text-red-700",
    PENDING: "bg-slate-100 text-slate-600",
    RUNNING: "bg-blue-100 text-blue-700",
    COMPLETED: "bg-green-100 text-green-700",
    CANCELED: "bg-slate-100 text-slate-500",
  };
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${map[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status}
    </span>
  );
}

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div
        className="h-full rounded-full bg-sky-500 transition-all duration-500"
        style={{ width: `${Math.min(100, pct)}%` }}
      />
    </div>
  );
}

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("zh-TW", { hour12: false });
}

// ─── Dataset Tab ─────────────────────────────────────────────────────────────

function DatasetTab({ onDatasetReady }: { onDatasetReady: () => void }) {
  const [datasets, setDatasets] = useState<TrainingDataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const [form, setForm] = useState({ name: "", description: "", val_ratio: "0.2" });
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listDatasets();
      setDatasets(res.items);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f?.name.endsWith(".zip")) setFile(f);
    else setError("請拖入 .zip 格式的資料集壓縮包。");
  }

  async function handleUpload() {
    if (!file) { setError("請選擇 ZIP 檔案。"); return; }
    if (!form.name.trim()) { setError("請填寫資料集名稱。"); return; }
    setError(""); setSuccess(""); setUploading(true);
    try {
      await uploadDataset(file, form.name.trim(), form.description, parseFloat(form.val_ratio));
      setSuccess("資料集上傳並分割完成！");
      setFile(null);
      setForm({ name: "", description: "", val_ratio: "0.2" });
      await load();
      onDatasetReady();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "上傳失敗");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("確認刪除此資料集？")) return;
    try {
      await deleteDataset(id);
      await load();
      onDatasetReady();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "刪除失敗");
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-slate-800">
          <Upload className="h-4 w-4 text-sky-600" /> 上傳新資料集
        </h2>

        <div
          className={`mb-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors ${dragOver ? "border-sky-400 bg-sky-50" : "border-slate-300 hover:border-sky-400"}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
        >
          <FileArchive className="mb-2 h-10 w-10 text-slate-400" />
          {file ? (
            <p className="text-sm font-medium text-sky-700">{file.name}</p>
          ) : (
            <>
              <p className="text-sm text-slate-600">拖拽 ZIP 至此，或點擊選取</p>
              <p className="mt-1 text-xs text-slate-400">ZIP 結構：images/ + labels/ + classes.txt</p>
            </>
          )}
          <input ref={fileRef} type="file" accept=".zip" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }} />
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="sm:col-span-1">
            <label className="mb-1 block text-xs font-medium text-slate-600">資料集名稱 *</label>
            <input
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
              placeholder="my_dataset"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
          </div>
          <div className="sm:col-span-1">
            <label className="mb-1 block text-xs font-medium text-slate-600">描述（選填）</label>
            <input
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
              placeholder="雨霧場景資料集"
              value={form.description}
              onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">驗證集比例</label>
            <input
              type="number" min="0.05" max="0.5" step="0.05"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
              value={form.val_ratio}
              onChange={(e) => setForm((p) => ({ ...p, val_ratio: e.target.value }))}
            />
          </div>
        </div>

        {error && <p className="mt-3 flex items-center gap-1.5 text-sm text-red-600"><AlertCircle className="h-4 w-4" />{error}</p>}
        {success && <p className="mt-3 flex items-center gap-1.5 text-sm text-green-600"><CheckCircle2 className="h-4 w-4" />{success}</p>}

        <button
          onClick={handleUpload}
          disabled={uploading}
          className="mt-4 flex items-center gap-2 rounded-xl bg-sky-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-sky-700 disabled:opacity-50"
        >
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          {uploading ? "處理中…" : "上傳並分割"}
        </button>
      </div>

      {/* Dataset list */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-base font-semibold text-slate-800">
            <Database className="h-4 w-4 text-sky-600" /> 資料集列表
          </h2>
          <button onClick={load} className="flex items-center gap-1 text-xs text-slate-500 hover:text-sky-600">
            <RefreshCw className="h-3.5 w-3.5" /> 刷新
          </button>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-10 text-slate-400"><Loader2 className="h-5 w-5 animate-spin" /></div>
        ) : datasets.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">尚無資料集，請先上傳。</p>
        ) : (
          <div className="space-y-3">
            {datasets.map((ds) => (
              <div key={ds.id} className="flex items-start justify-between rounded-xl border border-slate-100 bg-slate-50 p-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-800">{ds.name}</span>
                    <StatusBadge status={ds.status} />
                  </div>
                  {ds.description && <p className="mt-0.5 text-xs text-slate-500">{ds.description}</p>}
                  <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span>訓練：{ds.num_train} 張</span>
                    <span>驗證：{ds.num_val} 張</span>
                    <span>類別：{ds.num_classes} 個</span>
                    {ds.class_names.length > 0 && (
                      <span className="truncate max-w-xs">[{ds.class_names.join(", ")}]</span>
                    )}
                  </div>
                  {ds.error_message && <p className="mt-1 text-xs text-red-500">{ds.error_message}</p>}
                </div>
                <button onClick={() => handleDelete(ds.id)} className="ml-4 shrink-0 text-slate-400 hover:text-red-500">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Create Job Form ──────────────────────────────────────────────────────────

function CreateJobForm({ onCreated }: { onCreated: () => void }) {
  const [datasets, setDatasets] = useState<TrainingDataset[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<CreateJobParams>({
    dataset_id: 0,
    model_file: "yolov13l.pt",
    epochs: 50,
    batch: 4,
    imgsz: 640,
    device: "0",
    workers: 0,
    patience: 20,
  });

  useEffect(() => {
    listDatasets().then((r) => {
      const ready = r.items.filter((d) => d.status === "READY");
      setDatasets(ready);
      if (ready.length > 0) setForm((p) => ({ ...p, dataset_id: ready[0].id }));
    });
  }, []);

  function field(key: keyof CreateJobParams, label: string, type = "text", opts?: Record<string, unknown>) {
    return (
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">{label}</label>
        <input
          type={type}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
          value={String(form[key])}
          onChange={(e) => setForm((p) => ({ ...p, [key]: type === "number" ? Number(e.target.value) : e.target.value }))}
          {...opts}
        />
      </div>
    );
  }

  async function handleSubmit() {
    if (!form.dataset_id) { setError("請選擇資料集。"); return; }
    setError(""); setSubmitting(true);
    try {
      await createJob(form);
      onCreated();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "創建失敗");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-slate-800">
        <Play className="h-4 w-4 text-sky-600" /> 新建訓練任務
      </h2>

      <div className="mb-3">
        <label className="mb-1 block text-xs font-medium text-slate-600">選擇資料集 *</label>
        {datasets.length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-200 p-3 text-sm text-slate-400">尚無 READY 狀態資料集，請先上傳。</p>
        ) : (
          <select
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
            value={form.dataset_id}
            onChange={(e) => setForm((p) => ({ ...p, dataset_id: Number(e.target.value) }))}
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>{d.name}（訓練 {d.num_train} / 驗證 {d.num_val}）</option>
            ))}
          </select>
        )}
      </div>

      <div className="mb-3">
        <label className="mb-1 block text-xs font-medium text-slate-600">模型規格</label>
        <select
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
          value={form.model_file}
          onChange={(e) => setForm((p) => ({ ...p, model_file: e.target.value }))}
        >
          {["yolov13n.pt", "yolov13s.pt", "yolov13l.pt", "yolov13x.pt"].map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {field("epochs", "Epochs", "number", { min: 1, max: 500 })}
        {field("batch", "Batch Size", "number", { min: 1 })}
        {field("imgsz", "Image Size", "number")}
        {field("device", "Device (0=GPU, cpu)")}
        {field("workers", "Workers", "number", { min: 0 })}
        {field("patience", "Patience", "number", { min: 1 })}
      </div>

      {error && <p className="mt-3 flex items-center gap-1.5 text-sm text-red-600"><AlertCircle className="h-4 w-4" />{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={submitting || datasets.length === 0}
        className="mt-4 flex items-center gap-2 rounded-xl bg-sky-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-sky-700 disabled:opacity-50"
      >
        {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
        {submitting ? "啟動中…" : "啟動訓練"}
      </button>
    </div>
  );
}

// ─── Job Detail Panel ─────────────────────────────────────────────────────────

function ImprovementBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="text-slate-400">—</span>;
  const pct = (value * 100).toFixed(2);
  if (value > 0) return <span className="font-semibold text-green-600">+{pct}%</span>;
  if (value < 0) return <span className="font-semibold text-red-500">{pct}%</span>;
  return <span className="text-slate-500">0%</span>;
}

function BaselineCompareTable({ job }: { job: TrainingJob }) {
  const rows = [
    { label: "mAP50", baseline: job.baseline_map50, finetuned: job.best_map50, diff: job.improvement_map50 },
    {
      label: "mAP50-95",
      baseline: job.baseline_map50_95,
      finetuned: job.best_map50_95,
      diff: job.best_map50_95 != null && job.baseline_map50_95 != null
        ? job.best_map50_95 - job.baseline_map50_95 : null,
    },
    {
      label: "Precision",
      baseline: job.baseline_precision,
      finetuned: null,
      diff: null,
    },
    {
      label: "Recall",
      baseline: job.baseline_recall,
      finetuned: null,
      diff: null,
    },
  ];

  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b border-slate-100 text-left text-slate-500">
          <th className="pb-1.5 font-medium">指標</th>
          <th className="pb-1.5 font-medium">基礎模型（{job.model_file}）</th>
          <th className="pb-1.5 font-medium">微調後（best.pt）</th>
          <th className="pb-1.5 font-medium">提升</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-50">
        {rows.map((r) => (
          <tr key={r.label}>
            <td className="py-1.5 font-medium text-slate-700">{r.label}</td>
            <td className="py-1.5 text-slate-600">{r.baseline != null ? r.baseline.toFixed(4) : "—"}</td>
            <td className="py-1.5 text-slate-600">{r.finetuned != null ? r.finetuned.toFixed(4) : "—"}</td>
            <td className="py-1.5"><ImprovementBadge value={r.diff ?? null} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function JobDetailPanel({ job, onClose, onRefresh }: { job: TrainingJob; onClose: () => void; onRefresh: () => void }) {
  const [log, setLog] = useState("");
  const [logLoading, setLogLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState("");
  const [canceling, setCanceling] = useState(false);
  const [baselining, setBaselining] = useState(false);

  async function loadLog() {
    setLogLoading(true);
    try {
      const res = await getJobLog(job.id);
      setLog(res.log);
    } catch { /* silent */ }
    finally { setLogLoading(false); }
  }

  async function handleCancel() {
    if (!confirm("確認取消此訓練任務？")) return;
    setCanceling(true);
    try { await cancelJob(job.id); onRefresh(); } catch { /* silent */ }
    finally { setCanceling(false); }
  }

  async function handleDeploy() {
    if (!confirm("確認將此模型部署為推理服務的當前模型？")) return;
    setDeploying(true);
    try {
      const res = await deployJob(job.id);
      setDeployResult(`已部署：${res.model_file}`);
      onRefresh();
    } catch (e: unknown) {
      setDeployResult(e instanceof Error ? e.message : "部署失敗");
    } finally {
      setDeploying(false);
    }
  }

  async function handleBaseline() {
    if (!confirm(`將在原始 ${job.model_file} 上執行驗證，需要數分鐘，確認啟動？`)) return;
    setBaselining(true);
    try { await validateBaseline(job.id); onRefresh(); } catch { /* silent */ }
    finally { setBaselining(false); }
  }

  const baselineStatusLabel: Record<string, string> = {
    NONE: "", RUNNING: "驗證中…", DONE: "完成", FAILED: "失敗",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-2xl overflow-y-auto max-h-screen rounded-2xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h3 className="font-semibold text-slate-800">{job.job_no}</h3>
            <p className="text-xs text-slate-500">{job.dataset_name} · {job.model_file}</p>
          </div>
          <StatusBadge status={job.status} />
        </div>
        <div className="space-y-4 px-6 py-4">
          {/* Progress */}
          <div>
            <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
              <span>進度 {job.current_epoch}/{job.total_epochs} epoch</span>
              <span>{job.progress_pct}%</span>
            </div>
            <ProgressBar pct={job.progress_pct} />
          </div>

          {/* Basic metrics */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div className="text-slate-500">mAP50<span className="ml-2 font-medium text-slate-800">{job.best_map50 != null ? job.best_map50.toFixed(4) : "—"}</span></div>
            <div className="text-slate-500">mAP50-95<span className="ml-2 font-medium text-slate-800">{job.best_map50_95 != null ? job.best_map50_95.toFixed(4) : "—"}</span></div>
            <div className="text-slate-500">開始<span className="ml-2 font-medium text-slate-800">{fmtDate(job.started_at)}</span></div>
            <div className="text-slate-500">結束<span className="ml-2 font-medium text-slate-800">{fmtDate(job.finished_at)}</span></div>
          </div>

          {/* Baseline comparison */}
          <div className="rounded-xl border border-slate-200 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="text-xs font-semibold text-slate-700">📊 基線對比（原始模型 vs 微調後）</h4>
              {job.baseline_status !== "NONE" && (
                <span className="text-xs text-slate-400">{baselineStatusLabel[job.baseline_status]}</span>
              )}
            </div>
            {job.baseline_status === "DONE" ? (
              <BaselineCompareTable job={job} />
            ) : job.baseline_status === "RUNNING" ? (
              <div className="flex items-center gap-2 text-xs text-blue-600">
                <Loader2 className="h-4 w-4 animate-spin" /> 正在對原始模型執行驗證，請稍後…
              </div>
            ) : (
              <p className="text-xs text-slate-400">
                點擊「對比基線」後，系統將在原始 {job.model_file} 上執行 val()，
                完成後顯示 mAP50 / mAP50-95 提升幅度。
              </p>
            )}
          </div>

          {job.error_message && (
            <div className="rounded-lg bg-red-50 p-3 text-xs text-red-700">
              <ServerCrash className="mb-1 h-4 w-4" />{job.error_message.slice(0, 300)}
            </div>
          )}
          {deployResult && <p className="text-sm text-green-600">{deployResult}</p>}

          <div className="flex flex-wrap gap-2">
            {job.status === "RUNNING" && (
              <button onClick={handleCancel} disabled={canceling} className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-50">
                {canceling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Square className="h-3.5 w-3.5" />} 取消訓練
              </button>
            )}
            {job.status === "COMPLETED" && (
              <button onClick={handleDeploy} disabled={deploying} className="flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700 disabled:opacity-50">
                {deploying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Rocket className="h-3.5 w-3.5" />} 部署模型
              </button>
            )}
            {job.baseline_status !== "RUNNING" && job.baseline_status !== "DONE" && (
              <button onClick={handleBaseline} disabled={baselining} className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50">
                {baselining ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} 對比基線
              </button>
            )}
            <button onClick={loadLog} disabled={logLoading} className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50">
              {logLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} 查看日誌
            </button>
          </div>

          {log && (
            <pre className="max-h-48 overflow-auto rounded-lg bg-slate-900 p-3 text-xs leading-5 text-green-300 whitespace-pre-wrap">{log}</pre>
          )}
        </div>
        <div className="flex justify-end border-t border-slate-100 px-6 py-3">
          <button onClick={onClose} className="text-sm text-slate-500 hover:text-slate-800">關閉</button>
        </div>
      </div>
    </div>
  );
}

// ─── Jobs Tab ─────────────────────────────────────────────────────────────────

const RUNNING_STATUSES: JobStatus[] = ["RUNNING", "PENDING"];

function JobsTab() {
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<TrainingJob | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listJobs();
      setJobs(res.items);
      if (selected) {
        const updated = res.items.find((j) => j.id === selected.id);
        if (updated) setSelected(updated);
      }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, [selected]);

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, 6000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [load]);

  const hasRunning = jobs.some((j) => RUNNING_STATUSES.includes(j.status));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          {hasRunning && <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-400" />}
          {hasRunning ? "有訓練任務執行中（每 6 秒自動刷新）" : "無執行中任務"}
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="flex items-center gap-1 text-xs text-slate-500 hover:text-sky-600">
            <RefreshCw className="h-3.5 w-3.5" /> 刷新
          </button>
          <button
            onClick={() => setShowCreate((p) => !p)}
            className="flex items-center gap-1.5 rounded-xl bg-sky-600 px-4 py-2 text-xs font-medium text-white hover:bg-sky-700"
          >
            <Play className="h-3.5 w-3.5" /> 新建任務
          </button>
        </div>
      </div>

      {showCreate && <CreateJobForm onCreated={() => { setShowCreate(false); load(); }} />}

      <div className="rounded-2xl border border-slate-200 bg-white">
        {loading && jobs.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-slate-400"><Loader2 className="h-5 w-5 animate-spin" /></div>
        ) : jobs.length === 0 ? (
          <p className="py-12 text-center text-sm text-slate-400">尚無訓練任務，點擊「新建任務」開始。</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {jobs.map((job) => (
              <button
                key={job.id}
                className="flex w-full items-center gap-4 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
                onClick={() => setSelected(job)}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-800">{job.job_no}</span>
                    <StatusBadge status={job.status} />
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {job.dataset_name} · {job.model_file} · epochs={job.total_epochs} batch={job.batch}
                  </p>
                  <div className="mt-2">
                    <ProgressBar pct={job.progress_pct} />
                    <p className="mt-1 text-xs text-slate-400">
                      {job.current_epoch}/{job.total_epochs} epoch
                      {job.best_map50 != null && ` · mAP50=${job.best_map50.toFixed(3)}`}
                    </p>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <JobDetailPanel
          job={selected}
          onClose={() => setSelected(null)}
          onRefresh={load}
        />
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function TrainingPage() {
  const [tab, setTab] = useState<"datasets" | "jobs">("datasets");
  const [dsRefreshKey, setDsRefreshKey] = useState(0);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">模型訓練</h1>
        <p className="mt-1 text-sm text-slate-500">上傳資料集、啟動微調訓練、監控進度並部署模型。</p>
      </div>

      <div className="mb-6 flex gap-1 rounded-xl bg-slate-100 p-1">
        {(["datasets", "jobs"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition-colors ${tab === t ? "bg-white text-sky-700 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
          >
            {t === "datasets" ? "📦 資料集管理" : "🚀 訓練任務"}
          </button>
        ))}
      </div>

      {tab === "datasets" && <DatasetTab key={dsRefreshKey} onDatasetReady={() => setDsRefreshKey((k) => k + 1)} />}
      {tab === "jobs" && <JobsTab />}
    </div>
  );
}

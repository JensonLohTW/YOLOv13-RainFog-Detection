import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Database,
  FileArchive,
  HelpCircle,
  Loader2,
  Play,
  RefreshCw,
  Rocket,
  RotateCcw,
  ServerCrash,
  Square,
  Trash2,
  TrendingUp,
  Upload,
} from "lucide-react";

import {
  cancelJob,
  createJob,
  deleteDataset,
  deployJob,
  getJobLog,
  getJobVisualization,
  listDatasets,
  listJobs,
  retryJob,
  uploadDataset,
  validateBaseline,
  type CreateJobParams,
  type JobStatus,
  type PreprocessMode,
  type TrainingDataset,
  type TrainingJob,
  type TrainingVisualizationPayload,
} from "@/services/training-api";
import { EpochChart } from "@/features/training/EpochChart";

// ─── Shared helpers ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    READY: "bg-green-100 text-green-700",
    UPLOADING: "bg-yellow-100 text-yellow-700",
    FAILED: "bg-red-100 text-red-700",
    PENDING: "bg-slate-100 text-slate-600",
    RUNNING: "bg-blue-100 text-blue-700",
    COMPLETED: "bg-green-100 text-green-700",
    CANCELED: "bg-amber-100 text-amber-700",
  };
  const labels: Record<string, string> = {
    READY: "就緒",
    UPLOADING: "上傳中",
    FAILED: "失敗",
    PENDING: "等待中",
    RUNNING: "訓練中",
    COMPLETED: "完成",
    CANCELED: "已中斷",
  };
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${map[status] ?? "bg-slate-100 text-slate-600"}`}
    >
      {labels[status] ?? status}
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

function fmtSecs(s: number | null | undefined) {
  if (s == null) return "—";
  if (s < 60) return `${s.toFixed(0)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}

// ─── Usage Guide ──────────────────────────────────────────────────────────────

function UsageGuide() {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-2xl border border-sky-200 bg-sky-50">
      <button
        className="flex w-full items-center justify-between px-5 py-4 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-sky-800">
          <HelpCircle className="h-4 w-4" />
          使用說明 — 如何完成一次模型訓練？
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4 text-sky-600" />
        ) : (
          <ChevronDown className="h-4 w-4 text-sky-600" />
        )}
      </button>

      {open && (
        <div className="border-t border-sky-200 px-5 pb-5 pt-4 text-xs text-slate-700 space-y-5">
          {/* Step flow */}
          <div>
            <p className="mb-2 font-semibold text-slate-800">操作流程（依序完成）</p>
            <ol className="space-y-1.5 list-none">
              {[
                ["1", "切換至「📦 資料集管理」分頁，上傳符合格式的 ZIP 資料集。"],
                ["2", "等待資料集狀態變為「就緒」後，切換至「🚀 訓練任務」分頁。"],
                ["3", "點擊「新建任務」，選擇資料集與訓練參數，點擊「啟動訓練」。"],
                ["4", "任務卡片會每 6 秒自動刷新，點擊任意任務查看詳情與圖表。"],
                ["5", "（可選）在詳情面板點擊「對比基線」，對原始模型執行一次 val() 驗證。"],
                ["6", "訓練完成後點擊「部署模型」，將 best.pt 設為推理服務的當前模型。"],
              ].map(([n, text]) => (
                <li key={n} className="flex gap-2">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-200 font-semibold text-sky-800">
                    {n}
                  </span>
                  <span>{text}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* Dataset format */}
          <div>
            <p className="mb-2 font-semibold text-slate-800">資料集 ZIP 格式要求</p>
            <div className="rounded-lg bg-white border border-slate-200 p-3 font-mono text-xs leading-relaxed text-slate-600">
              <div>your_dataset.zip</div>
              <div className="ml-4">├── images/</div>
              <div className="ml-8">├── img001.jpg</div>
              <div className="ml-8">└── img002.jpg  <span className="text-slate-400">（支援 jpg / png）</span></div>
              <div className="ml-4">├── labels/</div>
              <div className="ml-8">├── img001.txt  <span className="text-slate-400">（YOLO 格式：class cx cy w h，正規化 0-1）</span></div>
              <div className="ml-8">└── img002.txt</div>
              <div className="ml-4">└── classes.txt  <span className="text-slate-400">（每行一個類別名稱）</span></div>
            </div>
            <p className="mt-1.5 text-slate-500">
              上傳時可指定「驗證集比例」（預設 0.2），系統自動隨機分割 train / val 並生成 data.yaml。
            </p>
          </div>

          {/* Parameter guide */}
          <div>
            <p className="mb-2 font-semibold text-slate-800">訓練參數說明</p>
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="pb-1 font-medium w-28">參數</th>
                  <th className="pb-1 font-medium w-24">預設值</th>
                  <th className="pb-1 font-medium">說明</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[
                  ["model_file", "yolov13l.pt", "模型規格：n（輕量）→ s → l → x（最強）"],
                  ["epochs", "50", "訓練總輪次，建議 30–150，GPU 充足可設 100+"],
                  ["batch", "4", "批次大小，依 VRAM 調整；CPU 訓練建議 2–4"],
                  ["imgsz", "640", "輸入影像尺寸（像素），建議保持 640"],
                  ["device", "0", "0 = 第一顆 GPU；cpu = 強制 CPU 訓練"],
                  ["workers", "0", "DataLoader 工作執行緒數；Windows 建議設 0"],
                  ["patience", "20", "Early-stopping 容忍輪數，超過則提前結束"],
                  ["preprocess_mode", "off", "雨霧預處理：off / auto（自動偵測）/ manual（手動指定）"],
                ].map(([p, d, desc]) => (
                  <tr key={p}>
                    <td className="py-1 font-mono text-sky-700">{p}</td>
                    <td className="py-1 text-slate-500">{d}</td>
                    <td className="py-1 text-slate-600">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Chart guide */}
          <div>
            <p className="mb-1 font-semibold text-slate-800">可視化圖表說明</p>
            <p className="text-slate-500">
              點擊任務後在詳情面板切換「圖表」分頁，可查看每輪 mAP、損失函數（loss）、學習率趨勢。
              訓練未完成前亦可即時查看；若尚無資料，請稍等訓練完成第一輪後再點擊「刷新圖表」。
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Dataset Tab ──────────────────────────────────────────────────────────────

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

  useEffect(() => {
    load();
  }, [load]);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f?.name.endsWith(".zip")) setFile(f);
    else setError("請拖入 .zip 格式的資料集壓縮包。");
  }

  async function handleUpload() {
    if (!file) {
      setError("請選擇 ZIP 檔案。");
      return;
    }
    if (!form.name.trim()) {
      setError("請填寫資料集名稱。");
      return;
    }
    setError("");
    setSuccess("");
    setUploading(true);
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
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-slate-800">
          <Upload className="h-4 w-4 text-sky-600" /> 上傳新資料集
        </h2>

        <div
          className={`mb-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors ${dragOver ? "border-sky-400 bg-sky-50" : "border-slate-300 hover:border-sky-400"}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
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
              <p className="mt-1 text-xs text-slate-400">
                ZIP 結構：images/ + labels/ + classes.txt
              </p>
            </>
          )}
          <input
            ref={fileRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) setFile(f);
            }}
          />
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
              type="number"
              min="0.05"
              max="0.5"
              step="0.05"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
              value={form.val_ratio}
              onChange={(e) => setForm((p) => ({ ...p, val_ratio: e.target.value }))}
            />
          </div>
        </div>

        {error && (
          <p className="mt-3 flex items-center gap-1.5 text-sm text-red-600">
            <AlertCircle className="h-4 w-4" />
            {error}
          </p>
        )}
        {success && (
          <p className="mt-3 flex items-center gap-1.5 text-sm text-green-600">
            <CheckCircle2 className="h-4 w-4" />
            {success}
          </p>
        )}

        <button
          onClick={handleUpload}
          disabled={uploading}
          className="mt-4 flex items-center gap-2 rounded-xl bg-sky-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-sky-700 disabled:opacity-50"
        >
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          {uploading ? "處理中…" : "上傳並分割"}
        </button>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-base font-semibold text-slate-800">
            <Database className="h-4 w-4 text-sky-600" /> 資料集列表
          </h2>
          <button
            onClick={load}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-sky-600"
          >
            <RefreshCw className="h-3.5 w-3.5" /> 刷新
          </button>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-10 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : datasets.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">尚無資料集，請先上傳。</p>
        ) : (
          <div className="space-y-3">
            {datasets.map((ds) => (
              <div
                key={ds.id}
                className="flex items-start justify-between rounded-xl border border-slate-100 bg-slate-50 p-4"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-800">{ds.name}</span>
                    <StatusBadge status={ds.status} />
                  </div>
                  {ds.description && (
                    <p className="mt-0.5 text-xs text-slate-500">{ds.description}</p>
                  )}
                  <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span>訓練：{ds.num_train} 張</span>
                    <span>驗證：{ds.num_val} 張</span>
                    <span>類別：{ds.num_classes} 個</span>
                    {ds.class_names.length > 0 && (
                      <span className="max-w-xs truncate">[{ds.class_names.join(", ")}]</span>
                    )}
                  </div>
                  {ds.error_message && (
                    <p className="mt-1 text-xs text-red-500">{ds.error_message}</p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(ds.id)}
                  className="ml-4 shrink-0 text-slate-400 hover:text-red-500"
                >
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

// ─── Create Job Form ───────────────────────────────────────────────────────────

const PREPROCESS_MODE_LABELS: Record<PreprocessMode, string> = {
  off: "off — 不預處理",
  auto: "auto — 自動偵測雨霧",
  manual: "manual — 手動指定算法",
};

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
    preprocess_mode: "off",
    preprocess_profile: "",
    preprocess_algorithms: [],
    preprocess_algorithm_params: {},
    preprocess_enable_gamma: false,
  });

  useEffect(() => {
    listDatasets().then((r) => {
      const ready = r.items.filter((d) => d.status === "READY");
      setDatasets(ready);
      if (ready.length > 0) setForm((p) => ({ ...p, dataset_id: ready[0].id }));
    });
  }, []);

  function numField(
    key: keyof CreateJobParams,
    label: string,
    opts?: Record<string, unknown>,
  ) {
    return (
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">{label}</label>
        <input
          type="number"
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
          value={String(form[key])}
          onChange={(e) => setForm((p) => ({ ...p, [key]: Number(e.target.value) }))}
          {...opts}
        />
      </div>
    );
  }

  async function handleSubmit() {
    if (!form.dataset_id) {
      setError("請選擇資料集。");
      return;
    }
    setError("");
    setSubmitting(true);
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
          <p className="rounded-lg border border-dashed border-slate-200 p-3 text-sm text-slate-400">
            尚無 READY 狀態資料集，請先上傳。
          </p>
        ) : (
          <select
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
            value={form.dataset_id}
            onChange={(e) => setForm((p) => ({ ...p, dataset_id: Number(e.target.value) }))}
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}（訓練 {d.num_train} / 驗證 {d.num_val}）
              </option>
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
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-3 grid gap-3 sm:grid-cols-3">
        {numField("epochs", "Epochs（輪次）", { min: 1, max: 500 })}
        {numField("batch", "Batch Size", { min: 1 })}
        {numField("imgsz", "Image Size（px）", { min: 320, max: 1280, step: 32 })}
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Device（0=GPU, cpu）
          </label>
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
            value={form.device}
            onChange={(e) => setForm((p) => ({ ...p, device: e.target.value }))}
          />
        </div>
        {numField("workers", "Workers（0=推薦）", { min: 0 })}
        {numField("patience", "Patience（Early-stop）", { min: 1 })}
      </div>

      <div className="mb-3">
        <label className="mb-1 block text-xs font-medium text-slate-600">
          雨霧預處理模式
        </label>
        <select
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
          value={form.preprocess_mode}
          onChange={(e) =>
            setForm((p) => ({ ...p, preprocess_mode: e.target.value as PreprocessMode }))
          }
        >
          {(["off", "auto", "manual"] as PreprocessMode[]).map((m) => (
            <option key={m} value={m}>
              {PREPROCESS_MODE_LABELS[m]}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p className="mt-3 flex items-center gap-1.5 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          {error}
        </p>
      )}

      <button
        onClick={handleSubmit}
        disabled={submitting || datasets.length === 0}
        className="mt-4 flex items-center gap-2 rounded-xl bg-sky-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-sky-700 disabled:opacity-50"
      >
        {submitting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {submitting ? "啟動中…" : "啟動訓練"}
      </button>
    </div>
  );
}

// ─── Baseline compare table ────────────────────────────────────────────────────

function ImprovementBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="text-slate-400">—</span>;
  const pct = (value * 100).toFixed(2);
  if (value > 0) return <span className="font-semibold text-green-600">+{pct}%</span>;
  if (value < 0) return <span className="font-semibold text-red-500">{pct}%</span>;
  return <span className="text-slate-500">0%</span>;
}

function BaselineCompareTable({ job }: { job: TrainingJob }) {
  const rows = [
    {
      label: "mAP50",
      baseline: job.baseline_map50,
      finetuned: job.best_map50,
      diff: job.improvement_map50,
    },
    {
      label: "mAP50-95",
      baseline: job.baseline_map50_95,
      finetuned: job.best_map50_95,
      diff:
        job.best_map50_95 != null && job.baseline_map50_95 != null
          ? job.best_map50_95 - job.baseline_map50_95
          : null,
    },
    { label: "Precision", baseline: job.baseline_precision, finetuned: null, diff: null },
    { label: "Recall", baseline: job.baseline_recall, finetuned: null, diff: null },
  ];

  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b border-slate-100 text-left text-slate-500">
          <th className="pb-1.5 font-medium">指標</th>
          <th className="pb-1.5 font-medium">基礎（{job.model_file}）</th>
          <th className="pb-1.5 font-medium">微調後（best.pt）</th>
          <th className="pb-1.5 font-medium">提升</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-50">
        {rows.map((r) => (
          <tr key={r.label}>
            <td className="py-1.5 font-medium text-slate-700">{r.label}</td>
            <td className="py-1.5 text-slate-600">
              {r.baseline != null ? r.baseline.toFixed(4) : "—"}
            </td>
            <td className="py-1.5 text-slate-600">
              {r.finetuned != null ? r.finetuned.toFixed(4) : "—"}
            </td>
            <td className="py-1.5">
              <ImprovementBadge value={r.diff ?? null} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ─── Training Summary Block ────────────────────────────────────────────────────

function TrainingSummaryBlock({ viz }: { viz: TrainingVisualizationPayload }) {
  const s = viz.summary;
  const fm = s.final_metrics;

  return (
    <div className="space-y-3">
      {/* Warnings */}
      {s.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-1">
          {s.warnings.map((w, i) => (
            <p key={i} className="flex items-start gap-1.5 text-xs text-amber-800">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {w}
            </p>
          ))}
        </div>
      )}

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          { label: "mAP50", value: fm.map50?.toFixed(4) ?? "—" },
          { label: "mAP50-95", value: fm.map50_95?.toFixed(4) ?? "—" },
          { label: "Precision", value: fm.precision?.toFixed(4) ?? "—" },
          { label: "Recall", value: fm.recall?.toFixed(4) ?? "—" },
        ].map((m) => (
          <div key={m.label} className="rounded-lg bg-slate-50 border border-slate-200 p-2.5 text-center">
            <p className="text-xs text-slate-500">{m.label}</p>
            <p className="mt-0.5 text-base font-semibold text-slate-800">{m.value}</p>
          </div>
        ))}
      </div>

      {/* Best epoch + runtime */}
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
        {s.best_epoch != null && (
          <span>
            最佳 epoch：<span className="font-medium text-slate-700">#{s.best_epoch}</span>
          </span>
        )}
        {s.runtime_seconds != null && (
          <span>
            耗時：<span className="font-medium text-slate-700">{fmtSecs(s.runtime_seconds)}</span>
          </span>
        )}
        <span>
          完成輪次：
          <span className="font-medium text-slate-700">
            {s.completed_epochs} / {s.total_epochs}
          </span>
        </span>
      </div>

      {/* Trend conclusions */}
      {s.trend_conclusion.length > 0 && (
        <div className="rounded-lg bg-green-50 border border-green-200 p-3 space-y-1">
          <p className="flex items-center gap-1 text-xs font-semibold text-green-800">
            <TrendingUp className="h-3.5 w-3.5" /> 趨勢結論
          </p>
          {s.trend_conclusion.map((t, i) => (
            <p key={i} className="text-xs text-green-700 pl-5">
              {t}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Visualization Panel (charts) ─────────────────────────────────────────────

type ChartTab = "metrics" | "losses" | "lr";

function VisualizationPanel({ viz }: { viz: TrainingVisualizationPayload }) {
  const [chartTab, setChartTab] = useState<ChartTab>("metrics");
  const epochs = viz.epochs;

  return (
    <div>
      <div className="mb-3 flex gap-1 rounded-lg bg-slate-100 p-0.5">
        {(
          [
            ["metrics", "mAP 指標"],
            ["losses", "損失函數"],
            ["lr", "學習率"],
          ] as [ChartTab, string][]
        ).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setChartTab(t)}
            className={`flex-1 rounded-md py-1 text-xs font-medium transition-colors ${chartTab === t ? "bg-white text-sky-700 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {chartTab === "metrics" && (
        <EpochChart
          epochs={epochs}
          title="每輪 mAP / Precision / Recall"
          series={[
            { key: "map50", label: "mAP50", color: "#0ea5e9" },
            { key: "map50_95", label: "mAP50-95", color: "#6366f1" },
            { key: "precision", label: "Precision", color: "#10b981" },
            { key: "recall", label: "Recall", color: "#f59e0b" },
          ]}
          height={180}
        />
      )}

      {chartTab === "losses" && (
        <EpochChart
          epochs={epochs}
          title="每輪訓練 / 驗證損失"
          series={[
            { key: "train_box_loss", label: "Train Box Loss", color: "#ef4444" },
            { key: "val_box_loss", label: "Val Box Loss", color: "#f97316" },
            { key: "train_cls_loss", label: "Train Cls Loss", color: "#8b5cf6" },
            { key: "val_cls_loss", label: "Val Cls Loss", color: "#ec4899" },
          ]}
          height={180}
        />
      )}

      {chartTab === "lr" && (
        <EpochChart
          epochs={epochs}
          title="學習率（lr/pg0）"
          series={[{ key: "lr", label: "Learning Rate", color: "#64748b" }]}
          height={150}
        />
      )}

      {epochs.length > 0 && (
        <p className="mt-1 text-right text-xs text-slate-400">
          已記錄 {epochs.length} 輪 · 來源：{viz.source}
        </p>
      )}
    </div>
  );
}

// ─── Job Detail Panel ──────────────────────────────────────────────────────────

type DetailTab = "overview" | "chart" | "log";

function JobDetailPanel({
  job,
  onClose,
  onRefresh,
}: {
  job: TrainingJob;
  onClose: () => void;
  onRefresh: (newJobId?: number) => void;
}) {
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [log, setLog] = useState("");
  const [logLoading, setLogLoading] = useState(false);
  const [viz, setViz] = useState<TrainingVisualizationPayload | null>(null);
  const [vizLoading, setVizLoading] = useState(false);
  const [vizError, setVizError] = useState("");
  const [deploying, setDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState("");
  const [canceling, setCanceling] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [baselining, setBaselining] = useState(false);
  const [actionError, setActionError] = useState("");

  const loadViz = useCallback(async () => {
    setVizLoading(true);
    setVizError("");
    try {
      const payload = await getJobVisualization(job.id);
      setViz(payload);
    } catch (e: unknown) {
      setVizError(e instanceof Error ? e.message : "載入圖表資料失敗");
    } finally {
      setVizLoading(false);
    }
  }, [job.id]);

  // Load viz on mount (or when switching to chart tab)
  useEffect(() => {
    if (activeTab === "chart" && !viz && !vizLoading) {
      loadViz();
    }
  }, [activeTab, viz, vizLoading, loadViz]);

  // Auto-poll viz while job is running
  useEffect(() => {
    if (job.status !== "RUNNING") return;
    const id = setInterval(() => {
      if (activeTab === "chart") loadViz();
    }, 10000);
    return () => clearInterval(id);
  }, [job.status, activeTab, loadViz]);

  async function loadLog() {
    setLogLoading(true);
    try {
      const res = await getJobLog(job.id);
      setLog(res.log);
    } catch {
      /* silent */
    } finally {
      setLogLoading(false);
    }
  }

  useEffect(() => {
    if (activeTab === "log") loadLog();
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCancel() {
    if (!confirm("確認取消此訓練任務？訓練進程將被強制終止。")) return;
    setActionError("");
    setCanceling(true);
    try {
      await cancelJob(job.id);
      onRefresh();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "取消失敗");
    } finally {
      setCanceling(false);
    }
  }

  async function handleRetry() {
    if (!confirm("確認以相同參數重新建立並啟動訓練任務？")) return;
    setActionError("");
    setRetrying(true);
    try {
      const newJob = await retryJob(job.id);
      onRefresh(newJob.id);
      onClose();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "重試失敗");
    } finally {
      setRetrying(false);
    }
  }

  async function handleDeploy() {
    if (!confirm("確認將此模型部署為推理服務的當前模型？")) return;
    setDeploying(true);
    setActionError("");
    try {
      const res = await deployJob(job.id);
      setDeployResult(`已部署：${res.model_file}`);
      onRefresh();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "部署失敗");
    } finally {
      setDeploying(false);
    }
  }

  async function handleBaseline() {
    if (!confirm(`將在原始 ${job.model_file} 上執行驗證，需要數分鐘，確認啟動？`)) return;
    setBaselining(true);
    setActionError("");
    try {
      await validateBaseline(job.id);
      onRefresh();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "基線驗證啟動失敗");
    } finally {
      setBaselining(false);
    }
  }

  const baselineStatusLabel: Record<string, string> = {
    NONE: "",
    RUNNING: "驗證中…",
    DONE: "完成",
    FAILED: "失敗",
  };

  const DETAIL_TABS: [DetailTab, string][] = [
    ["overview", "概覽"],
    ["chart", "圖表"],
    ["log", "日誌"],
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="flex w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
        style={{ maxHeight: "90vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4 shrink-0">
          <div>
            <h3 className="font-semibold text-slate-800">{job.job_no}</h3>
            <p className="text-xs text-slate-500">
              {job.dataset_name} · {job.model_file} · epochs={job.total_epochs}
            </p>
          </div>
          <StatusBadge status={job.status} />
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 border-b border-slate-100 px-6 pt-3 shrink-0">
          {DETAIL_TABS.map(([t, label]) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`px-4 py-1.5 text-sm font-medium rounded-t-lg transition-colors border-b-2 ${activeTab === t ? "border-sky-500 text-sky-700" : "border-transparent text-slate-500 hover:text-slate-700"}`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Scrollable body */}
        <div className="overflow-y-auto flex-1 px-6 py-4 space-y-4">
          {/* ── Overview tab ── */}
          {activeTab === "overview" && (
            <>
              {/* Progress */}
              <div>
                <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                  <span>
                    進度 {job.current_epoch}/{job.total_epochs} epoch
                  </span>
                  <span>{job.progress_pct}%</span>
                </div>
                <ProgressBar pct={job.progress_pct} />
              </div>

              {/* Basic metrics */}
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
                <div className="text-slate-500">
                  mAP50{" "}
                  <span className="ml-2 font-medium text-slate-800">
                    {job.best_map50 != null ? job.best_map50.toFixed(4) : "—"}
                  </span>
                </div>
                <div className="text-slate-500">
                  mAP50-95{" "}
                  <span className="ml-2 font-medium text-slate-800">
                    {job.best_map50_95 != null ? job.best_map50_95.toFixed(4) : "—"}
                  </span>
                </div>
                <div className="text-slate-500">
                  開始{" "}
                  <span className="ml-2 font-medium text-slate-800">
                    {fmtDate(job.started_at)}
                  </span>
                </div>
                <div className="text-slate-500">
                  結束{" "}
                  <span className="ml-2 font-medium text-slate-800">
                    {fmtDate(job.finished_at)}
                  </span>
                </div>
              </div>

              {/* Error message */}
              {job.error_message && (
                <div className="rounded-lg bg-red-50 p-3 text-xs text-red-700">
                  <div className="flex items-center gap-1.5 mb-1 font-semibold">
                    <ServerCrash className="h-4 w-4" /> 錯誤訊息
                  </div>
                  {job.error_message.slice(0, 400)}
                </div>
              )}

              {/* Baseline comparison */}
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-slate-700">
                    📊 基線對比（原始模型 vs 微調後）
                  </h4>
                  {job.baseline_status !== "NONE" && (
                    <span className="text-xs text-slate-400">
                      {baselineStatusLabel[job.baseline_status]}
                    </span>
                  )}
                </div>
                {job.baseline_status === "DONE" ? (
                  <BaselineCompareTable job={job} />
                ) : job.baseline_status === "RUNNING" ? (
                  <div className="flex items-center gap-2 text-xs text-blue-600">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    正在對原始模型執行驗證，請稍後…
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">
                    點擊「對比基線」後，系統將在原始 {job.model_file} 上執行 val()，完成後顯示
                    mAP50 / mAP50-95 提升幅度。
                  </p>
                )}
              </div>

              {deployResult && (
                <p className="text-sm text-green-600">
                  <CheckCircle2 className="mr-1 inline h-4 w-4" />
                  {deployResult}
                </p>
              )}
            </>
          )}

          {/* ── Chart tab ── */}
          {activeTab === "chart" && (
            <>
              {vizLoading && (
                <div className="flex items-center justify-center py-10 text-slate-400">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span className="ml-2 text-sm">載入圖表資料…</span>
                </div>
              )}
              {vizError && (
                <div className="rounded-lg bg-red-50 p-3 text-xs text-red-600">
                  <AlertCircle className="mr-1 inline h-3.5 w-3.5" />
                  {vizError}
                </div>
              )}
              {viz && !vizLoading && (
                <>
                  <VisualizationPanel viz={viz} />
                  <div className="border-t border-slate-100 pt-3">
                    <TrainingSummaryBlock viz={viz} />
                  </div>
                </>
              )}
              {!viz && !vizLoading && !vizError && (
                <p className="py-8 text-center text-sm text-slate-400">
                  尚無圖表資料，請等待訓練開始後點擊刷新。
                </p>
              )}
              <button
                onClick={loadViz}
                disabled={vizLoading}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${vizLoading ? "animate-spin" : ""}`} />
                刷新圖表
              </button>
            </>
          )}

          {/* ── Log tab ── */}
          {activeTab === "log" && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-500">顯示最後 100 行日誌</p>
                <button
                  onClick={loadLog}
                  disabled={logLoading}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${logLoading ? "animate-spin" : ""}`} />
                  刷新日誌
                </button>
              </div>
              {logLoading && (
                <div className="flex items-center justify-center py-6 text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              )}
              {log ? (
                <pre className="max-h-72 overflow-auto rounded-lg bg-slate-900 p-3 text-xs leading-5 text-green-300 whitespace-pre-wrap">
                  {log}
                </pre>
              ) : (
                !logLoading && (
                  <p className="py-6 text-center text-sm text-slate-400">暫無日誌內容。</p>
                )
              )}
            </>
          )}

          {/* Action error */}
          {actionError && (
            <p className="flex items-center gap-1.5 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              {actionError}
            </p>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-6 py-3 shrink-0">
          <div className="flex flex-wrap gap-2">
            {/* Cancel — available for PENDING or RUNNING */}
            {job.can_cancel && (
              <button
                onClick={handleCancel}
                disabled={canceling}
                className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-50"
              >
                {canceling ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Square className="h-3.5 w-3.5" />
                )}
                中斷訓練
              </button>
            )}

            {/* Retry — available for COMPLETED / FAILED / CANCELED */}
            {job.can_retry && (
              <button
                onClick={handleRetry}
                disabled={retrying}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
              >
                {retrying ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RotateCcw className="h-3.5 w-3.5" />
                )}
                重試訓練
              </button>
            )}

            {/* Deploy */}
            {job.can_deploy && (
              <button
                onClick={handleDeploy}
                disabled={deploying}
                className="flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700 disabled:opacity-50"
              >
                {deploying ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Rocket className="h-3.5 w-3.5" />
                )}
                部署模型
              </button>
            )}

            {/* Baseline */}
            {job.baseline_status !== "RUNNING" && job.baseline_status !== "DONE" && (
              <button
                onClick={handleBaseline}
                disabled={baselining}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
              >
                {baselining ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5" />
                )}
                對比基線
              </button>
            )}
          </div>

          <button onClick={onClose} className="text-sm text-slate-500 hover:text-slate-800">
            關閉
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Jobs Tab ──────────────────────────────────────────────────────────────────

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
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, [selected]);

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, 6000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [load]);

  const hasRunning = jobs.some((j) => RUNNING_STATUSES.includes(j.status));

  function handlePanelRefresh(newJobId?: number) {
    load();
    if (newJobId) {
      // Clear selected so new job can be selected from fresh list
      setSelected(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          {hasRunning && (
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-400" />
          )}
          {hasRunning ? "有訓練任務執行中（每 6 秒自動刷新）" : "無執行中任務"}
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-sky-600"
          >
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

      {showCreate && (
        <CreateJobForm
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}

      <div className="rounded-2xl border border-slate-200 bg-white">
        {loading && jobs.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : jobs.length === 0 ? (
          <p className="py-12 text-center text-sm text-slate-400">
            尚無訓練任務，點擊「新建任務」開始。
          </p>
        ) : (
          <div className="divide-y divide-slate-100">
            {jobs.map((job) => (
              <button
                key={job.id}
                className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-slate-50"
                onClick={() => setSelected(job)}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-800">{job.job_no}</span>
                    <StatusBadge status={job.status} />
                    {job.status === "RUNNING" && (
                      <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-400" />
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {job.dataset_name} · {job.model_file} · epochs={job.total_epochs} batch=
                    {job.batch}
                  </p>
                  <div className="mt-2">
                    <ProgressBar pct={job.progress_pct} />
                    <p className="mt-1 text-xs text-slate-400">
                      {job.current_epoch}/{job.total_epochs} epoch
                      {job.best_map50 != null && ` · mAP50=${job.best_map50.toFixed(3)}`}
                      {job.status === "CANCELED" && " · 已中斷"}
                      {job.status === "FAILED" && " · 訓練失敗"}
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
          onRefresh={handlePanelRefresh}
        />
      )}
    </div>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export function TrainingPage() {
  const [tab, setTab] = useState<"datasets" | "jobs">("datasets");
  const [dsRefreshKey, setDsRefreshKey] = useState(0);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">模型訓練</h1>
        <p className="mt-1 text-sm text-slate-500">
          上傳資料集、啟動微調訓練、監控進度並部署模型。
        </p>
      </div>

      <div className="mb-6 space-y-4">
        <UsageGuide />
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

      {tab === "datasets" && (
        <DatasetTab
          key={dsRefreshKey}
          onDatasetReady={() => setDsRefreshKey((k) => k + 1)}
        />
      )}
      {tab === "jobs" && <JobsTab />}
    </div>
  );
}

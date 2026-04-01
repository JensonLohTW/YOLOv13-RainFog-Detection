import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { startTransition, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  createDetectionTask,
  fetchImages,
  previewPreprocess,
  uploadImage,
} from "@/features/detection/detection-api";
import { PreprocessConfigForm } from "@/features/detection/preprocess-config-form";
import type { PreprocessConfig, PreprocessPreviewResponse } from "@/features/detection/detection-types";
import { getMediaUrl } from "@/services/api";

const DEFAULT_CONFIG: PreprocessConfig = {
  preprocess_mode: "auto",
  preprocess_profile: "",
  preprocess_algorithms: [],
  preprocess_algorithm_params: {},
  preprocess_enable_gamma: false,
  scene_hint: "",
};

type Step = 1 | 2 | 3;

export function PreprocessDetectionPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [step, setStep] = useState<Step>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedImageId, setSelectedImageId] = useState<number | null>(null);
  const [selectedImageName, setSelectedImageName] = useState("");
  const [config, setConfig] = useState<PreprocessConfig>(DEFAULT_CONFIG);
  const [preview, setPreview] = useState<PreprocessPreviewResponse | null>(null);
  const [error, setError] = useState("");

  const imagesQuery = useQuery({
    queryKey: ["images"],
    queryFn: fetchImages,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadImage(file),
    onSuccess: (img) => {
      startTransition(() => {
        setSelectedImageId(img.id);
        setSelectedImageName(img.original_name);
      });
      void queryClient.invalidateQueries({ queryKey: ["images"] });
    },
    onError: (e) => setError(e instanceof Error ? e.message : "上傳失敗"),
  });

  const previewMutation = useMutation({
    mutationFn: ({ imageId, cfg }: { imageId: number; cfg: PreprocessConfig }) =>
      previewPreprocess(imageId, cfg),
    onSuccess: (data) => {
      setPreview(data);
      setStep(3);
    },
    onError: (e) => setError(e instanceof Error ? e.message : "預覽失敗"),
  });

  const createTaskMutation = useMutation({
    mutationFn: createDetectionTask,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["detection-tasks"] });
      navigate(`/detection/${data.task_no}`);
    },
    onError: (e) => setError(e instanceof Error ? e.message : "建立任務失敗"),
  });

  async function handleProceedToStep2() {
    setError("");
    let imageId = selectedImageId;
    if (selectedFile) {
      try {
        const img = await uploadMutation.mutateAsync(selectedFile);
        imageId = img.id;
      } catch {
        return;
      }
    }
    if (!imageId) {
      setError("請先上傳或選擇一張圖片。");
      return;
    }
    startTransition(() => {
      setSelectedImageId(imageId);
      setStep(2);
    });
  }

  function handlePreview() {
    if (!selectedImageId) return;
    setError("");
    setPreview(null);
    previewMutation.mutate({ imageId: selectedImageId, cfg: config });
  }

  function handleRunDetection() {
    if (!selectedImageId) return;
    setError("");
    createTaskMutation.mutate({
      image_id: selectedImageId,
      recognition_mode: "image",
      ...config,
    });
  }

  const uploading = uploadMutation.isPending;
  const isPreviewing = previewMutation.isPending;
  const isCreating = createTaskMutation.isPending;

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] text-sky-700">Preprocess + Detection</p>
        <h2 className="text-3xl font-semibold text-slate-900">預處理識別</h2>
        <p className="text-sm text-slate-600">
          先對圖片套用天氣預處理演算法，預覽效果確認後再執行 YOLO 識別。
        </p>
      </header>

      <StepIndicator current={step} />

      {error ? (
        <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>
      ) : null}

      {step === 1 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-lg font-medium text-slate-900">Step 1 — 選擇圖片</h3>
          <div className="mt-5 space-y-4">
            <div className="space-y-2">
              <label className="text-sm text-slate-600">上傳新圖片</label>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="block w-full rounded-xl border border-slate-200 px-4 py-3 text-sm"
                onChange={(e) => {
                  const f = e.target.files?.[0] ?? null;
                  setSelectedFile(f);
                  if (f) {
                    setSelectedImageId(null);
                    setSelectedImageName(f.name);
                  }
                }}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm text-slate-600">或從已上傳圖片中選擇</label>
              <select
                className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm"
                value={selectedImageId ?? ""}
                onChange={(e) => {
                  const val = e.target.value;
                  startTransition(() => {
                    setSelectedImageId(val ? Number(val) : null);
                    setSelectedImageName(
                      imagesQuery.data?.items.find((i) => i.id === Number(val))?.original_name ?? "",
                    );
                    if (val) setSelectedFile(null);
                  });
                }}
              >
                <option value="">請選擇…</option>
                {(imagesQuery.data?.items ?? []).map((img) => (
                  <option key={img.id} value={img.id}>
                    {img.original_name}
                  </option>
                ))}
              </select>
            </div>

            {selectedImageName ? (
              <p className="text-sm text-slate-500">已選：{selectedImageName}</p>
            ) : null}

            <Button
              className="w-full"
              onClick={() => void handleProceedToStep2()}
              disabled={(!selectedFile && !selectedImageId) || uploading}
            >
              {uploading ? "上傳中..." : "下一步：設定預處理 →"}
            </Button>
          </div>
        </div>
      )}

      {step >= 2 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-medium text-slate-900">Step 2 — 設定預處理參數</h3>
            <button
              onClick={() => { setStep(1); setPreview(null); }}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              ← 重新選擇圖片
            </button>
          </div>
          <p className="mb-4 text-sm text-slate-500">圖片：{selectedImageName}</p>

          <PreprocessConfigForm
            value={config}
            onChange={setConfig}
            onPreview={handlePreview}
            isPreviewing={isPreviewing}
          />
        </div>
      )}

      {step >= 3 && preview && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-6">
            <h3 className="mb-4 text-lg font-medium text-slate-900">Step 3 — 預覽結果</h3>

            {preview.applied ? (
              <div className="mb-3 rounded-xl bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
                已套用演算法：{preview.algorithms.join(", ")}
                {preview.scene !== "unknown" ? ` ｜ 偵測場景：${preview.scene}` : ""}
                {` ｜ 來源：${getSceneSourceLabel(preview.scene_source)}`}
              </div>
            ) : (
              <div className="mb-3 rounded-xl bg-amber-50 px-4 py-2 text-sm text-amber-700">
                <p className="font-medium">預處理未套用</p>
                <p className="mt-0.5 text-xs">
                  {getPreviewGuidance(preview.scene, preview.scene_source)}
                </p>
              </div>
            )}

            <div className="mb-4 flex flex-wrap gap-2 text-xs">
              <span className="rounded-md bg-slate-100 px-2 py-1 text-slate-600">
                場景來源：{getSceneSourceLabel(preview.scene_source)}
              </span>
              <span className="rounded-md bg-slate-100 px-2 py-1 text-slate-600">
                檔名標籤：{preview.raw_scene || "unknown"}
              </span>
              <span className="rounded-md bg-slate-100 px-2 py-1 text-slate-600">
                最終場景：{preview.scene || "unknown"}
              </span>
            </div>

            {preview.scene_source === "image_heuristic" ? (
              <div className="mb-4 rounded-xl bg-sky-50 px-4 py-3 text-xs text-sky-800">
                已由影像內容自動推斷場景，不依賴檔名。若效果不理想，可返回上一步手動指定場景或改為 manual。
              </div>
            ) : null}

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-sm font-medium text-slate-600">原始圖片</p>
                <div className="overflow-hidden rounded-xl bg-slate-50">
                  {preview.original_image_url ? (
                    <img
                      src={getMediaUrl(preview.original_image_url)}
                      alt="original"
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    <div className="flex h-48 items-center justify-center text-sm text-slate-400">
                      無預覽
                    </div>
                  )}
                </div>
              </div>

              <div>
                <p className="mb-2 text-sm font-medium text-slate-600">
                  預處理後圖片
                  {!preview.applied && (
                    <span className="ml-2 rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-400">
                      無變化
                    </span>
                  )}
                </p>
                <div className="overflow-hidden rounded-xl bg-slate-50">
                  {preview.preview_image_url ? (
                    <img
                      src={getMediaUrl(preview.preview_image_url)}
                      alt="preprocessed"
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    <div className="flex h-48 items-center justify-center text-sm text-slate-400">
                      載入中…
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => { setStep(2); setPreview(null); }}
            >
              ← 調整參數
            </Button>
            <Button
              className="flex-1"
              onClick={handleRunDetection}
              disabled={isCreating}
            >
              {isCreating ? "識別中..." : "執行識別 →"}
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

function StepIndicator({ current }: { current: Step }) {
  const steps = [
    { n: 1, label: "選擇圖片" },
    { n: 2, label: "設定預處理" },
    { n: 3, label: "預覽 & 識別" },
  ];
  return (
    <div className="flex items-center gap-2">
      {steps.map((s, i) => (
        <div key={s.n} className="flex items-center gap-2">
          <div
            className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
              current === s.n
                ? "bg-sky-600 text-white"
                : current > s.n
                  ? "bg-emerald-500 text-white"
                  : "bg-slate-200 text-slate-500"
            }`}
          >
            {current > s.n ? "✓" : s.n}
          </div>
          <span
            className={`text-sm ${current === s.n ? "font-medium text-slate-900" : "text-slate-400"}`}
          >
            {s.label}
          </span>
          {i < steps.length - 1 && (
            <div className={`h-px w-8 ${current > s.n ? "bg-emerald-400" : "bg-slate-200"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

function getSceneSourceLabel(source: string): string {
  switch (source) {
    case "filename":
      return "檔名/路徑";
    case "image_heuristic":
      return "影像內容啟發式";
    case "profile":
      return "場景提示 Profile";
    case "hint":
      return "scene_hint";
    default:
      return "未識別";
  }
}

function getPreviewGuidance(scene: string, source: string): string {
  if (scene === "unknown") {
    if (source === "unknown") {
      return "auto 模式已嘗試檔名與影像內容判斷，但仍無法穩定識別場景。請在「場景提示」中手動選擇場景，或切換為 manual 模式並勾選演算法。";
    }
    return "目前未配對到可用的預處理演算法，請切換為 manual 模式並勾選演算法。";
  }
  return "已識別出場景，但目前未配對到任何演算法。請切換為 manual 模式並勾選演算法。";
}

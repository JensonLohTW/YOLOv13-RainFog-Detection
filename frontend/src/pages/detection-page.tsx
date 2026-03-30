import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { startTransition, useDeferredValue, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { apiGet, apiPost, apiUpload } from "@/services/api";

type ImageAsset = {
  id: number;
  original_name: string;
  file_url: string;
};

type ImageAssetListResponse = {
  items: ImageAsset[];
  total: number;
};

type DetectionTaskSummary = {
  task_no: string;
  status: string;
  recognition_mode: string;
  weather_scene: string;
  object_count: number;
  can_retry: boolean;
  latest_record: {
    engine_type: string;
    duration_ms: number;
    is_mock: boolean;
  } | null;
};

type DetectionTaskListResponse = {
  items: DetectionTaskSummary[];
  total: number;
};

type DetectionTaskCreateResponse = {
  task_no: string;
  status: string;
  recognition_mode: string;
};

export function DetectionPage() {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [recognitionMode, setRecognitionMode] = useState("scene_default");
  const [createScene, setCreateScene] = useState("rain_fog");
  const [uploadedImageId, setUploadedImageId] = useState<number | null>(null);
  const [uploadedImageName, setUploadedImageName] = useState("");
  const [localError, setLocalError] = useState("");
  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sceneFilter, setSceneFilter] = useState("");
  const deferredKeyword = useDeferredValue(keyword);
  const params = new URLSearchParams();
  if (deferredKeyword) params.set("keyword", deferredKeyword);
  if (statusFilter) params.set("status", statusFilter);
  if (sceneFilter) params.set("weather_scene", sceneFilter);
  const queryString = params.toString() ? `?${params.toString()}` : "";

  const imagesQuery = useQuery({
    queryKey: ["images"],
    queryFn: () => apiGet<ImageAssetListResponse>("/images"),
  });

  const tasksQuery = useQuery({
    queryKey: ["detection-tasks", queryString],
    queryFn: () => apiGet<DetectionTaskListResponse>(`/detection/tasks${queryString}`),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => apiUpload<ImageAsset>("/images/upload", file),
    onSuccess: (image) => {
      startTransition(() => {
        setUploadedImageId(image.id);
        setUploadedImageName(image.original_name);
      });
      void queryClient.invalidateQueries({ queryKey: ["images"] });
    },
  });

  const createTaskMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiPost<DetectionTaskCreateResponse, Record<string, unknown>>("/detection/tasks", payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["detection-tasks"] });
    },
  });

  async function handleUploadAndCreate() {
    try {
      setLocalError("");
      let imageId = uploadedImageId;
      if (selectedFile) {
        const uploaded = await uploadMutation.mutateAsync(selectedFile);
        imageId = uploaded.id;
      }
      if (!imageId) {
        setLocalError("請先上傳新圖片，或從已上傳列表中選擇一張圖片。");
        return;
      }
      const payload: Record<string, unknown> = { image_id: imageId };
      if (recognitionMode === "image") {
        payload.recognition_mode = "image";
        payload.weather_scene = createScene;
        payload.confidence_threshold = 0.25;
        payload.iou_threshold = 0.45;
      }
      await createTaskMutation.mutateAsync(payload);
    } catch (error) {
      if (error instanceof Error) {
        setLocalError(error.message);
      } else {
        setLocalError("建立任務失敗，請稍後再試。");
      }
    }
  }

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] text-sky-700">Detection</p>
        <h2 className="text-3xl font-semibold text-slate-900">識別任務管理</h2>
        <p className="text-sm text-slate-600">
          這裡會對接圖片上傳、任務建立、結果查詢與詳情預覽。
        </p>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-lg font-medium text-slate-900">建立識別任務</h3>
          <div className="mt-5 space-y-4">
            <div className="space-y-2">
              <label className="text-sm text-slate-600">上傳新圖片</label>
              <input
                className="block w-full rounded-xl border border-slate-200 px-4 py-3 text-sm"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm text-slate-600">或選擇已上傳圖片</label>
              <select
                className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm"
                value={uploadedImageId ?? ""}
                onChange={(event) => {
                  const value = event.target.value;
                  startTransition(() => {
                    setUploadedImageId(value ? Number(value) : null);
                    setUploadedImageName(
                      imagesQuery.data?.items.find((item) => item.id === Number(value))?.original_name ?? "",
                    );
                  });
                }}
              >
                <option value="">請選擇圖片</option>
                {(imagesQuery.data?.items ?? []).map((image) => (
                  <option key={image.id} value={image.id}>
                    {image.original_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm text-slate-600">識別模式</label>
              <select
                className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm"
                value={recognitionMode}
                onChange={(event) => setRecognitionMode(event.target.value)}
              >
                <option value="scene_default">默認場景模式</option>
                <option value="image">圖片模式</option>
              </select>
            </div>
            {recognitionMode === "image" ? (
              <div className="space-y-2">
                <label className="text-sm text-slate-600">天氣場景</label>
                <select
                  className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm"
                  value={createScene}
                  onChange={(event) => setCreateScene(event.target.value)}
                >
                  <option value="rain_fog">雨霧</option>
                  <option value="rain">雨天</option>
                  <option value="fog">霧天</option>
                  <option value="unknown">未知</option>
                </select>
              </div>
            ) : (
              <p className="rounded-xl bg-sky-50 px-3 py-2 text-sm text-sky-800">
                未手動指定模式時，系統會自動套用默認場景配置。
              </p>
            )}
            <Button
              className="w-full"
              onClick={() => void handleUploadAndCreate()}
              disabled={uploadMutation.isPending || createTaskMutation.isPending}
            >
              {uploadMutation.isPending || createTaskMutation.isPending ? "提交中..." : "上傳並建立任務"}
            </Button>
            {uploadedImageName ? (
              <p className="text-sm text-slate-600">已選圖片：{uploadedImageName}</p>
            ) : null}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-lg font-medium text-slate-900">目前狀態</h3>
          <div className="mt-4 space-y-3 text-sm text-slate-600">
            <p>已上傳圖片數：{imagesQuery.data?.total ?? 0}</p>
            <p>任務總數：{tasksQuery.data?.total ?? 0}</p>
            {createTaskMutation.data ? (
              <p className="rounded-xl bg-emerald-50 px-3 py-2 text-emerald-700">
                最新任務：{createTaskMutation.data.task_no} / {createTaskMutation.data.status} / {createTaskMutation.data.recognition_mode}
              </p>
            ) : null}
            {uploadMutation.error instanceof Error ? (
              <p className="rounded-xl bg-rose-50 px-3 py-2 text-rose-700">{uploadMutation.error.message}</p>
            ) : null}
            {createTaskMutation.error instanceof Error ? (
              <p className="rounded-xl bg-rose-50 px-3 py-2 text-rose-700">{createTaskMutation.error.message}</p>
            ) : null}
            {localError ? (
              <p className="rounded-xl bg-amber-50 px-3 py-2 text-amber-700">{localError}</p>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 lg:grid-cols-[1.2fr_1fr_1fr]">
        <input
          className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm"
          placeholder="按任務編號或圖片名稱搜尋"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <select
          className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="">全部狀態</option>
          <option value="SUCCESS">成功</option>
          <option value="FAILED">失敗</option>
          <option value="PROCESSING">處理中</option>
          <option value="QUEUED">排隊中</option>
        </select>
        <select
          className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm"
          value={sceneFilter}
          onChange={(event) => setSceneFilter(event.target.value)}
        >
          <option value="">全部場景</option>
          <option value="rain_fog">雨霧</option>
          <option value="rain">雨天</option>
          <option value="fog">霧天</option>
          <option value="unknown">未知</option>
        </select>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">任務編號</th>
              <th className="px-4 py-3 font-medium">狀態</th>
              <th className="px-4 py-3 font-medium">模式</th>
              <th className="px-4 py-3 font-medium">場景</th>
              <th className="px-4 py-3 font-medium">目標數</th>
              <th className="px-4 py-3 font-medium">引擎</th>
              <th className="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {(tasksQuery.data?.items ?? []).map((task) => (
              <tr key={task.task_no} className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">{task.task_no}</td>
                <td className="px-4 py-3 text-slate-600">{task.status}</td>
                <td className="px-4 py-3 text-slate-600">{task.recognition_mode}</td>
                <td className="px-4 py-3 text-slate-600">{task.weather_scene}</td>
                <td className="px-4 py-3 text-slate-600">{task.object_count}</td>
                <td className="px-4 py-3 text-slate-600">{task.latest_record?.engine_type ?? "--"}</td>
                <td className="px-4 py-3 text-slate-600">
                  <Button asChild size="sm" variant="outline">
                    <Link to={`/detection/${task.task_no}`}>查看詳情</Link>
                  </Button>
                </td>
              </tr>
            ))}
            {!tasksQuery.data?.items?.length && !tasksQuery.isLoading ? (
              <tr className="border-t border-slate-100">
                <td className="px-4 py-6 text-slate-500" colSpan={7}>
                  暫無識別任務
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

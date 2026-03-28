import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { apiGet, apiPost } from "@/services/api";

type DetectionObject = {
  class_id: number;
  class_name: string;
  confidence: number;
  bbox: number[];
  bbox_width: number;
  bbox_height: number;
};

type InferenceRecord = {
  engine_type: string;
  engine_version: string;
  model_name: string;
  model_version: string;
  result_image_path: string;
  result_image_url: string;
  object_count: number;
  avg_confidence: number | null;
  duration_ms: number;
  is_mock: boolean;
  created_at: string;
  objects: DetectionObject[];
};

type DetectionTaskDetail = {
  task_no: string;
  status: string;
  weather_scene: string;
  confidence_threshold: number;
  iou_threshold: number;
  error_message: string;
  can_retry: boolean;
  image: {
    original_name: string;
    file_url: string;
  };
  latest_record: InferenceRecord | null;
  inference_records: InferenceRecord[];
  created_at: string;
  updated_at: string;
};

export function DetectionDetailPage() {
  const { taskNo = "" } = useParams();
  const queryClient = useQueryClient();

  const detailQuery = useQuery({
    queryKey: ["detection-task-detail", taskNo],
    queryFn: () => apiGet<DetectionTaskDetail>(`/detection/tasks/${taskNo}`),
    enabled: Boolean(taskNo),
  });

  const retryMutation = useMutation({
    mutationFn: () => apiPost<DetectionTaskDetail, Record<string, never>>(`/detection/tasks/${taskNo}/retry`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["detection-task-detail", taskNo] });
      void queryClient.invalidateQueries({ queryKey: ["detection-tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
    },
  });

  const detail = detailQuery.data;
  const latestRecord = detail?.latest_record;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-sky-700">Task Detail</p>
          <h2 className="text-3xl font-semibold text-slate-900">任務詳情</h2>
          <p className="text-sm text-slate-600">查看單個識別任務的推理結果、目標明細與重試狀態。</p>
        </div>
        <div className="flex gap-3">
          <Button asChild variant="outline">
            <Link to="/detection">返回列表</Link>
          </Button>
          <Button
            onClick={() => retryMutation.mutate()}
            disabled={!detail?.can_retry || retryMutation.isPending}
          >
            {retryMutation.isPending ? "重試中..." : "重新執行任務"}
          </Button>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-lg font-medium text-slate-900">任務概況</h3>
          <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
            <p>任務編號：{detail?.task_no ?? "--"}</p>
            <p>當前狀態：{detail?.status ?? "--"}</p>
            <p>天氣場景：{detail?.weather_scene ?? "--"}</p>
            <p>置信度閾值：{detail?.confidence_threshold ?? "--"}</p>
            <p>IOU 閾值：{detail?.iou_threshold ?? "--"}</p>
            <p>建立時間：{detail?.created_at ?? "--"}</p>
          </div>
          {detail?.error_message ? (
            <p className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{detail.error_message}</p>
          ) : null}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-lg font-medium text-slate-900">運行資訊</h3>
          <div className="mt-4 space-y-3 text-sm text-slate-600">
            <p>引擎：{latestRecord?.engine_type ?? "--"}</p>
            <p>模型：{latestRecord?.model_name ?? "--"} / {latestRecord?.model_version ?? "--"}</p>
            <p>耗時：{latestRecord?.duration_ms ?? 0} ms</p>
            <p>目標數：{latestRecord?.object_count ?? 0}</p>
            <p>平均置信度：{latestRecord?.avg_confidence ?? "--"}</p>
            <p>模式：{latestRecord?.is_mock ? "Mock" : "Real"}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-lg font-medium text-slate-900">原始圖片</h3>
          <div className="mt-4 overflow-hidden rounded-2xl bg-slate-50">
            {detail?.image.file_url ? (
              <img alt={detail.image.original_name} className="h-full w-full object-contain" src={detail.image.file_url} />
            ) : (
              <div className="flex h-64 items-center justify-center text-sm text-slate-400">暫無圖片</div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-lg font-medium text-slate-900">結果圖片</h3>
          <div className="mt-4 overflow-hidden rounded-2xl bg-slate-50">
            {latestRecord?.result_image_url ? (
              <img alt="result" className="h-full w-full object-contain" src={latestRecord.result_image_url} />
            ) : latestRecord?.result_image_path ? (
              <div className="flex h-64 items-center justify-center px-6 text-center text-sm text-slate-500">
                當前為 Mock / 開發階段，結果圖尚未實際生成，可先參考結果路徑：
                <br />
                {latestRecord.result_image_path}
              </div>
            ) : (
              <div className="flex h-64 items-center justify-center text-sm text-slate-400">暫無結果圖</div>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-6 py-4">
          <h3 className="text-lg font-medium text-slate-900">檢測目標明細</h3>
        </div>
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">類別</th>
              <th className="px-4 py-3 font-medium">置信度</th>
              <th className="px-4 py-3 font-medium">BBox</th>
              <th className="px-4 py-3 font-medium">寬</th>
              <th className="px-4 py-3 font-medium">高</th>
            </tr>
          </thead>
          <tbody>
            {(latestRecord?.objects ?? []).map((item, index) => (
              <tr key={`${item.class_name}-${index}`} className="border-t border-slate-100">
                <td className="px-4 py-3 text-slate-700">{item.class_name}</td>
                <td className="px-4 py-3 text-slate-700">{item.confidence}</td>
                <td className="px-4 py-3 text-slate-700">{item.bbox.join(", ")}</td>
                <td className="px-4 py-3 text-slate-700">{item.bbox_width}</td>
                <td className="px-4 py-3 text-slate-700">{item.bbox_height}</td>
              </tr>
            ))}
            {!latestRecord?.objects?.length && !detailQuery.isLoading ? (
              <tr className="border-t border-slate-100">
                <td className="px-4 py-6 text-slate-500" colSpan={5}>
                  暫無檢測目標
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { startTransition, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  askDetectionExplanation,
  fetchDetectionTaskDetail,
  retryDetectionTask,
} from "@/features/detection/detection-api";
import type {
  DetectionExplanationResponse,
  DetectionTaskDetail,
} from "@/features/detection/detection-types";
import { getMediaUrl } from "@/services/api";

const QUICK_QUESTIONS = [
  "這張圖偵測到哪些目標？",
  "有哪些結果比較不確定，可能誤判原因是什麼？",
  "如果我要人工複核，下一步建議怎麼做？",
] as const;

export function DetectionDetailPage() {
  const { taskNo = "" } = useParams();
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("");
  const [localError, setLocalError] = useState("");
  const [explanation, setExplanation] = useState<DetectionExplanationResponse | null>(null);

  const detailQuery = useQuery({
    queryKey: ["detection-task-detail", taskNo],
    queryFn: () => fetchDetectionTaskDetail(taskNo),
    enabled: Boolean(taskNo),
  });

  const retryMutation = useMutation({
    mutationFn: () => retryDetectionTask(taskNo),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["detection-task-detail", taskNo] });
      void queryClient.invalidateQueries({ queryKey: ["detection-tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
      startTransition(() => {
        setExplanation(null);
      });
    },
  });

  const explanationMutation = useMutation({
    mutationFn: (payload: { task_no: string; question: string }) => askDetectionExplanation(payload),
    onSuccess: (response) => {
      startTransition(() => {
        setExplanation(response);
      });
    },
    onError: (error) => {
      if (error instanceof Error) {
        setLocalError(error.message);
      } else {
        setLocalError("對話說明生成失敗，請稍後再試。");
      }
    },
  });

  const detail = detailQuery.data;
  const latestRecord = detail?.latest_record;

  function submitQuestion(nextQuestion?: string) {
    const resolvedQuestion = (nextQuestion ?? question).trim();
    if (!resolvedQuestion || !taskNo) {
      setLocalError("請先輸入問題。");
      return;
    }
    setLocalError("");
    explanationMutation.mutate({ task_no: taskNo, question: resolvedQuestion });
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-sky-700">Task Detail</p>
          <h2 className="text-3xl font-semibold text-slate-900">任務詳情</h2>
          <p className="text-sm text-slate-600">查看單個識別任務的推理結果、目標明細與 LLM 解讀。</p>
        </div>
        <div className="flex gap-3">
          <Button asChild variant="outline">
            <Link to="/detection">返回列表</Link>
          </Button>
          <Button onClick={() => retryMutation.mutate()} disabled={!detail?.can_retry || retryMutation.isPending}>
            {retryMutation.isPending ? "重試中..." : "重新執行任務"}
          </Button>
        </div>
      </header>

      <OverviewCards detail={detail} />

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <ImageCard
          title="原始圖片"
          alt={detail?.image.original_name ?? "original"}
          imageUrl={detail?.image.file_url ? getMediaUrl(detail.image.file_url) : ""}
          emptyText="暫無圖片"
        />
        <ImageCard
          title="結果圖片"
          alt="result"
          imageUrl={latestRecord?.result_image_url ? getMediaUrl(latestRecord.result_image_url) : ""}
          emptyText={
            latestRecord?.result_image_path
              ? `結果圖已生成，路徑：\n${latestRecord.result_image_path}`
              : "暫無結果圖"
          }
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_0.95fr]">
        <DetectionObjectsTable detail={detail} />

        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.3em] text-emerald-700">LLM Explain</p>
            <h3 className="text-lg font-medium text-slate-900">對話說明工具</h3>
            <p className="text-sm text-slate-600">
              針對這次檢測結果提問，例如目標類別、置信度、可能誤判原因與建議下一步。
            </p>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {QUICK_QUESTIONS.map((item) => (
              <button
                key={item}
                type="button"
                className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs text-emerald-800 transition hover:bg-emerald-100"
                onClick={() => {
                  startTransition(() => {
                    setQuestion(item);
                  });
                  submitQuestion(item);
                }}
              >
                {item}
              </button>
            ))}
          </div>

          <div className="mt-4 space-y-3">
            <textarea
              className="min-h-32 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
              placeholder="輸入你的問題，例如：這張圖裡哪個目標最不可靠？"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
            <Button
              className="w-full"
              onClick={() => submitQuestion()}
              disabled={explanationMutation.isPending || !latestRecord}
            >
              {explanationMutation.isPending ? "生成說明中..." : "送出問題"}
            </Button>
          </div>

          {localError ? (
            <p className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{localError}</p>
          ) : null}

          {explanation ? (
            <div className="mt-5 space-y-4">
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                  <span>Provider: {explanation.llm.provider}</span>
                  <span>Model: {explanation.llm.model}</span>
                  <span>Config: {explanation.llm.config_source}</span>
                </div>
                <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                  {explanation.answer}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-100 p-4">
                <h4 className="text-sm font-medium text-slate-900">結果依據</h4>
                <div className="mt-3 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
                  <p>目標總數：{explanation.grounding.object_count}</p>
                  <p>耗時：{explanation.grounding.inference.duration_ms} ms</p>
                  <p>引擎：{explanation.grounding.inference.engine_type}</p>
                  <p>場景：{explanation.grounding.weather_scene}</p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {explanation.grounding.class_summary.map((item) => (
                    <span
                      key={item.class_name}
                      className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700"
                    >
                      {item.class_name} x{item.count} / avg {item.avg_confidence.toFixed(2)}
                    </span>
                  ))}
                </div>
                {explanation.grounding.warnings.length ? (
                  <div className="mt-4 space-y-2">
                    {explanation.grounding.warnings.map((item) => (
                      <p key={item} className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">
                        {item}
                      </p>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
              {latestRecord ? "送出問題後，這裡會顯示基於檢測結果的文字解讀。" : "尚無可用推理結果，暫時不能提問。"}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function OverviewCards({ detail }: { detail?: DetectionTaskDetail }) {
  const latestRecord = detail?.latest_record;

  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-medium text-slate-900">任務概況</h3>
        <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
          <p>任務編號：{detail?.task_no ?? "--"}</p>
          <p>當前狀態：{detail?.status ?? "--"}</p>
          <p>識別模式：{detail?.recognition_mode ?? "--"}</p>
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
          <p>
            模型：{latestRecord?.model_name ?? "--"} / {latestRecord?.model_version ?? "--"}
          </p>
          <p>耗時：{latestRecord?.duration_ms ?? 0} ms</p>
          <p>目標數：{latestRecord?.object_count ?? 0}</p>
          <p>平均置信度：{latestRecord?.avg_confidence ?? "--"}</p>
          <p>推理類型：{latestRecord?.is_mock ? "Mock" : "Real"}</p>
          <p>模型配置：{String(detail?.runtime_options?.model_profile ?? "--")}</p>
        </div>
      </div>
    </div>
  );
}

function ImageCard({
  title,
  alt,
  imageUrl,
  emptyText,
}: {
  title: string;
  alt: string;
  imageUrl: string;
  emptyText: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <h3 className="text-lg font-medium text-slate-900">{title}</h3>
      <div className="mt-4 overflow-hidden rounded-2xl bg-slate-50">
        {imageUrl ? (
          <img alt={alt} className="h-full w-full object-contain" src={imageUrl} />
        ) : (
          <div className="flex h-64 items-center justify-center px-6 text-center text-sm whitespace-pre-wrap text-slate-400">
            {emptyText}
          </div>
        )}
      </div>
    </div>
  );
}

function DetectionObjectsTable({ detail }: { detail?: DetectionTaskDetail }) {
  const latestRecord = detail?.latest_record;

  return (
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
          {!latestRecord?.objects?.length && !detail ? null : null}
          {!latestRecord?.objects?.length && detail ? (
            <tr className="border-t border-slate-100">
              <td className="px-4 py-6 text-slate-500" colSpan={5}>
                暫無檢測目標
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

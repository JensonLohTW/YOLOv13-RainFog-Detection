import { useMutation, useQuery } from "@tanstack/react-query";
import { startTransition, useState } from "react";

import { Button } from "@/components/ui/button";
import { askAnalyticsQuestion } from "@/features/agent/agent-api";
import type { AnalyticsAgentResponse } from "@/features/agent/agent-types";
import { apiGet } from "@/services/api";

type DashboardOverview = {
  task_total: number;
  success_total: number;
  failed_total: number;
  processing_total: number;
  top_classes: Array<{ class_name: string; count: number }>;
};

const QUICK_QUESTIONS = [
  "近期哪些類別出現最多？",
  "最近 7 天的檢測趨勢如何？",
  "最近一週成功與失敗任務情況如何？",
] as const;

export function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: () => apiGet<DashboardOverview>("/dashboard/overview"),
  });
  const [question, setQuestion] = useState("");
  const [analyticsAnswer, setAnalyticsAnswer] = useState<AnalyticsAgentResponse | null>(null);
  const [localError, setLocalError] = useState("");

  const askMutation = useMutation({
    mutationFn: (nextQuestion: string) => askAnalyticsQuestion(nextQuestion),
    onSuccess: (response) => {
      setLocalError("");
      startTransition(() => {
        setAnalyticsAnswer(response);
      });
    },
    onError: (error) => {
      if (error instanceof Error) {
        setLocalError(error.message);
        return;
      }
      setLocalError("資料問答失敗，請稍後再試。");
    },
  });

  const metrics = [
    { label: "任務總量", value: data?.task_total ?? 0 },
    { label: "成功任務", value: data?.success_total ?? 0 },
    { label: "失敗任務", value: data?.failed_total ?? 0 },
    { label: "處理中", value: data?.processing_total ?? 0 },
  ];

  function submitQuestion(nextQuestion?: string) {
    const resolvedQuestion = (nextQuestion ?? question).trim();
    if (!resolvedQuestion) {
      setLocalError("請先輸入問題。");
      return;
    }
    askMutation.mutate(resolvedQuestion);
  }

  return (
    <section className="space-y-8">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] text-sky-700">Dashboard</p>
        <h2 className="text-3xl font-semibold text-slate-900">雨霧天氣識別概覽</h2>
        <p className="max-w-2xl text-sm text-slate-600">
          這裡提供任務統計、熱門類別，以及基於白名單聚合工具的自然語言資料問答。
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className="rounded-2xl border border-slate-200 bg-white p-5">
            <p className="text-sm text-slate-500">{metric.label}</p>
            <p className="mt-3 text-3xl font-semibold text-slate-900">
              {isLoading ? "--" : metric.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="text-lg font-medium text-slate-900">近期熱門識別類別</h3>
          <ul className="mt-4 space-y-3 text-sm text-slate-600">
            {(data?.top_classes ?? []).map((item) => (
              <li key={item.class_name}>
                {item.class_name} / {item.count}
              </li>
            ))}
            {!data?.top_classes?.length && !isLoading ? <li>暫無資料</li> : null}
          </ul>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.3em] text-emerald-700">Analytics Agent</p>
            <h3 className="text-lg font-medium text-slate-900">資料查詢問答</h3>
            <p className="text-sm text-slate-600">
              目前支援近期熱門類別、趨勢變化與任務狀態摘要。
            </p>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {QUICK_QUESTIONS.map((item) => (
              <button
                key={item}
                type="button"
                className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs text-emerald-800 transition hover:bg-emerald-100"
                onClick={() => {
                  setQuestion(item);
                  submitQuestion(item);
                }}
              >
                {item}
              </button>
            ))}
          </div>

          <div className="mt-4 space-y-3">
            <textarea
              className="min-h-28 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
              placeholder="例如：最近 14 天哪些類別出現最多？"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
            <Button className="w-full" onClick={() => submitQuestion()} disabled={askMutation.isPending}>
              {askMutation.isPending ? "分析中..." : "送出問題"}
            </Button>
          </div>

          {localError ? (
            <p className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{localError}</p>
          ) : null}

          {analyticsAnswer ? (
            <div className="mt-5 space-y-4">
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                  <span>Provider: {analyticsAnswer.llm.provider}</span>
                  <span>Model: {analyticsAnswer.llm.model}</span>
                  <span>Intent: {analyticsAnswer.grounding.intent}</span>
                </div>
                <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                  {analyticsAnswer.answer}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-100 p-4">
                <h4 className="text-sm font-medium text-slate-900">查詢依據</h4>
                <div className="mt-3 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
                  <p>區間起點：{analyticsAnswer.grounding.window.date_from}</p>
                  <p>區間終點：{analyticsAnswer.grounding.window.date_to}</p>
                  <p>任務總數：{analyticsAnswer.grounding.status_summary.task_total}</p>
                  <p>成功任務：{analyticsAnswer.grounding.status_summary.success_total}</p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {analyticsAnswer.grounding.top_classes.map((item) => (
                    <span
                      key={item.class_name}
                      className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700"
                    >
                      {item.class_name} x{item.count}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
              送出問題後，這裡會顯示基於白名單統計查詢的回答。
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

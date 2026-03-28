import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/services/api";

type DashboardOverview = {
  task_total: number;
  success_total: number;
  failed_total: number;
  processing_total: number;
  top_classes: Array<{ class_name: string; count: number }>;
};

export function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: () => apiGet<DashboardOverview>("/dashboard/overview"),
  });

  const metrics = [
    { label: "任務總量", value: data?.task_total ?? 0 },
    { label: "成功任務", value: data?.success_total ?? 0 },
    { label: "失敗任務", value: data?.failed_total ?? 0 },
    { label: "處理中", value: data?.processing_total ?? 0 },
  ];

  return (
    <section className="space-y-8">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] text-sky-700">Dashboard</p>
        <h2 className="text-3xl font-semibold text-slate-900">雨霧天氣識別概覽</h2>
        <p className="max-w-2xl text-sm text-slate-600">
          這裡會承接 Django 儀表盤統計接口，展示任務數、成功率、類別分佈與時間趨勢。
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

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="text-lg font-medium text-slate-900">近期識別趨勢</h3>
          <div className="mt-6 h-64 rounded-2xl bg-slate-50" />
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="text-lg font-medium text-slate-900">熱門識別類別</h3>
          <ul className="mt-4 space-y-3 text-sm text-slate-600">
            {(data?.top_classes ?? []).map((item) => (
              <li key={item.class_name}>
                {item.class_name} / {item.count}
              </li>
            ))}
            {!data?.top_classes?.length && !isLoading ? <li>暫無資料</li> : null}
          </ul>
        </div>
      </div>
    </section>
  );
}

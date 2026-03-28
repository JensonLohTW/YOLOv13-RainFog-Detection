import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/services/api";

type AuditLogItem = {
  id: number;
  module: string;
  action: string;
  method: string;
  path: string;
  response_code: number;
  status: string;
  duration_ms: number;
  user_name: string;
  created_at: string;
};

type AuditLogResponse = {
  items: AuditLogItem[];
  total: number;
};

export function AuditPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => apiGet<AuditLogResponse>("/audit/logs"),
  });

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] text-sky-700">Audit</p>
        <h2 className="text-3xl font-semibold text-slate-900">操作審計</h2>
        <p className="text-sm text-slate-600">展示近期 API 操作記錄與請求狀態。</p>
      </header>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
        {isLoading ? `載入中...` : `共 ${data?.total ?? 0} 條操作記錄`}
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">模組</th>
              <th className="px-4 py-3 font-medium">方法</th>
              <th className="px-4 py-3 font-medium">路徑</th>
              <th className="px-4 py-3 font-medium">狀態</th>
              <th className="px-4 py-3 font-medium">耗時</th>
              <th className="px-4 py-3 font-medium">時間</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((item) => (
              <tr key={item.id} className="border-t border-slate-100">
                <td className="px-4 py-3 text-slate-700">{item.module || "-"}</td>
                <td className="px-4 py-3 text-slate-700">{item.method}</td>
                <td className="px-4 py-3 text-slate-700">{item.path}</td>
                <td className="px-4 py-3 text-slate-700">
                  {item.status} / {item.response_code}
                </td>
                <td className="px-4 py-3 text-slate-700">{item.duration_ms} ms</td>
                <td className="px-4 py-3 text-slate-700">{item.created_at}</td>
              </tr>
            ))}
            {!data?.items?.length && !isLoading ? (
              <tr className="border-t border-slate-100">
                <td className="px-4 py-6 text-slate-500" colSpan={6}>
                  暫無操作日誌
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

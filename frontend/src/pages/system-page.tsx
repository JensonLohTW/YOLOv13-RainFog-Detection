import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { startTransition, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiGet, apiPut } from "@/services/api";

type SystemSummary = {
  inference_base_url: string;
  inference_use_mock: boolean;
  inference_model_mode: string;
  inference_model_name: string;
  redis: {
    host: string;
    port: number;
    db: number;
  };
  runtime: {
    health_status: string;
    service: string;
    model: {
      engine_type: string;
      model_name: string;
      model_version: string;
      ready?: boolean;
      note?: string;
    };
  };
};

type SystemConfigItem = {
  id: number;
  config_key: string;
  config_value: string;
  parsed_value: string | number | boolean;
  value_type: string;
  description: string;
};

type SystemConfigResponse = {
  summary: SystemSummary;
  items: SystemConfigItem[];
};

export function SystemPage() {
  const queryClient = useQueryClient();
  const [drafts, setDrafts] = useState<Record<number, string>>({});

  const { data } = useQuery({
    queryKey: ["system-configs"],
    queryFn: () => apiGet<SystemConfigResponse>("/system/configs"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, value }: { id: number; value: string }) =>
      apiPut<SystemConfigItem, { config_value: string }>(`/system/configs/${id}`, {
        config_value: value,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["system-configs"] });
    },
  });

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] text-sky-700">System</p>
        <h2 className="text-3xl font-semibold text-slate-900">系統配置</h2>
        <p className="text-sm text-slate-600">
          這裡將承接推理服務地址、Mock 開關、Redis 配置與後續模型版本配置。
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">推理服務</p>
          <p className="mt-2 text-lg font-medium text-slate-900">{data?.summary.inference_base_url ?? "--"}</p>
          <p className="mt-1 text-sm text-slate-600">
            當前模式：{data?.summary.inference_use_mock ? "Mock" : "Real"}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            適配器：{data?.summary.inference_model_mode ?? "--"} / {data?.summary.inference_model_name ?? "--"}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">緩存服務</p>
          <p className="mt-2 text-lg font-medium text-slate-900">
            Redis / {data?.summary.redis.host ?? "--"}:{data?.summary.redis.port ?? "--"}
          </p>
          <p className="mt-1 text-sm text-slate-600">DB：{data?.summary.redis.db ?? "--"}</p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-medium text-slate-900">推理運行時狀態</h3>
        <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
          <p>服務名稱：{data?.summary.runtime.service ?? "--"}</p>
          <p>健康狀態：{data?.summary.runtime.health_status ?? "--"}</p>
          <p>引擎類型：{data?.summary.runtime.model.engine_type ?? "--"}</p>
          <p>模型名稱：{data?.summary.runtime.model.model_name ?? "--"}</p>
          <p>模型版本：{data?.summary.runtime.model.model_version ?? "--"}</p>
          <p>可用狀態：{String(data?.summary.runtime.model.ready ?? false)}</p>
        </div>
        {data?.summary.runtime.model.note ? (
          <p className="mt-4 rounded-xl bg-sky-50 px-4 py-3 text-sm text-sky-800">
            {data.summary.runtime.model.note}
          </p>
        ) : null}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-medium text-slate-900">配置中心</h3>
        <div className="mt-5 space-y-4">
          {(data?.items ?? []).map((item) => (
            <div key={item.id} className="grid gap-3 rounded-2xl border border-slate-100 p-4 lg:grid-cols-[1fr_1fr_auto]">
              <div>
                <p className="text-sm font-medium text-slate-900">{item.config_key}</p>
                <p className="mt-1 text-sm text-slate-500">{item.description || "無描述"}</p>
              </div>
              <input
                className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm"
                value={drafts[item.id] ?? item.config_value}
                onChange={(event) => {
                  const value = event.target.value;
                  startTransition(() => {
                    setDrafts((current) => ({ ...current, [item.id]: value }));
                  });
                }}
              />
              <Button
                variant="outline"
                onClick={() =>
                  updateMutation.mutate({
                    id: item.id,
                    value: drafts[item.id] ?? item.config_value,
                  })
                }
                disabled={updateMutation.isPending}
              >
                保存
              </Button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

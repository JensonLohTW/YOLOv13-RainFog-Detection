import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { startTransition, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiGet, apiPut } from "@/services/api";

type SystemSummary = {
  inference_base_url: string;
  inference_use_mock: boolean;
  inference_model_mode: string;
  inference_model_name: string;
  detection_defaults: {
    recognition_mode: string;
    scene: string;
    confidence_threshold: number;
    iou_threshold: number;
    preprocess_mode: string;
    preprocess_profile: string;
    model_profile: string;
  };
  redis: {
    host: string;
    port: number;
    db: number;
  };
  llm: {
    provider: string;
    base_url: string;
    model: string;
    temperature: number;
    max_tokens: number;
    timeout: number;
    api_key_configured: boolean;
    api_key_source: string;
    config_source: string;
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
  is_sensitive: boolean;
  display_value: string;
  effective_source: string;
  has_effective_value: boolean;
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
    onSuccess: (_, variables) => {
      startTransition(() => {
        setDrafts((current) => {
          const next = { ...current };
          delete next[variables.id];
          return next;
        });
      });
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

      <div className="grid gap-4 md:grid-cols-3">
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
          <p className="text-sm text-slate-500">默認識別模式</p>
          <p className="mt-2 text-lg font-medium text-slate-900">
            {data?.summary.detection_defaults.recognition_mode ?? "--"}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            場景：{data?.summary.detection_defaults.scene ?? "--"} / 模型：{data?.summary.detection_defaults.model_profile ?? "--"}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            conf：{data?.summary.detection_defaults.confidence_threshold ?? "--"} / iou：{data?.summary.detection_defaults.iou_threshold ?? "--"}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">緩存服務</p>
          <p className="mt-2 text-lg font-medium text-slate-900">
            Redis / {data?.summary.redis.host ?? "--"}:{data?.summary.redis.port ?? "--"}
          </p>
          <p className="mt-1 text-sm text-slate-600">DB：{data?.summary.redis.db ?? "--"}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 md:col-span-3">
          <p className="text-sm text-slate-500">LLM 對話說明</p>
          <p className="mt-2 text-lg font-medium text-slate-900">
            {data?.summary.llm.provider ?? "--"} / {data?.summary.llm.model ?? "--"}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Base URL：{data?.summary.llm.base_url ?? "--"}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            temperature：{data?.summary.llm.temperature ?? "--"} / max_tokens：
            {" "}
            {data?.summary.llm.max_tokens ?? "--"} / timeout：{data?.summary.llm.timeout ?? "--"}s
          </p>
          <p className="mt-1 text-sm text-slate-600">
            API Key：{data?.summary.llm.api_key_configured ? "已配置" : "未配置"} / 來源：
            {" "}
            {data?.summary.llm.api_key_source ?? "--"}
          </p>
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
                <p className="mt-1 text-xs text-slate-400">
                  生效來源：{item.effective_source} {item.is_sensitive ? " / 敏感欄位已遮罩" : ""}
                </p>
              </div>
              <input
                className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm"
                type={item.is_sensitive ? "password" : "text"}
                value={drafts[item.id] ?? (item.is_sensitive ? "" : item.config_value)}
                placeholder={item.display_value || (item.has_effective_value ? "已配置" : "未配置")}
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
                disabled={updateMutation.isPending || drafts[item.id] === undefined}
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

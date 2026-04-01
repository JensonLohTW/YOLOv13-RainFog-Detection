import { Button } from "@/components/ui/button";

import type { PreprocessConfig } from "./detection-types";
import { PREPROCESS_ALGORITHMS, PREPROCESS_SCENES } from "./detection-types";

type Props = {
  value: PreprocessConfig;
  onChange: (next: PreprocessConfig) => void;
  onPreview: () => void;
  isPreviewing: boolean;
};

export function PreprocessConfigForm({ value, onChange, onPreview, isPreviewing }: Props) {
  function set<K extends keyof PreprocessConfig>(key: K, val: PreprocessConfig[K]) {
    onChange({ ...value, [key]: val });
  }

  function toggleAlgorithm(algo: string) {
    const current = value.preprocess_algorithms;
    const next = current.includes(algo)
      ? current.filter((a) => a !== algo)
      : [...current, algo];
    set("preprocess_algorithms", next);
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <label className="text-sm font-medium text-slate-700">預處理模式</label>
        <div className="flex gap-2">
          {(["off", "auto", "manual"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => set("preprocess_mode", mode)}
              className={`rounded-xl border px-4 py-2 text-sm font-medium transition-colors ${
                value.preprocess_mode === mode
                  ? "border-sky-600 bg-sky-600 text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:border-sky-300 hover:text-sky-700"
              }`}
            >
              {mode === "off" ? "關閉" : mode === "auto" ? "自動" : "手動"}
            </button>
          ))}
        </div>
        {value.preprocess_mode === "off" && (
          <p className="rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
            不套用任何預處理，直接進行識別。
          </p>
        )}
        {value.preprocess_mode === "auto" && (
          <p className="rounded-xl bg-sky-50 px-3 py-2 text-xs text-sky-700">
            系統根據場景自動選擇演算法鏈。可透過「場景提示」優先選擇特定場景。
          </p>
        )}
        {value.preprocess_mode === "manual" && (
          <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-700">
            手動勾選演算法。若未勾選則等同關閉。
          </p>
        )}
      </div>

      {value.preprocess_mode !== "off" && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">場景提示（Profile）</label>
          <select
            className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm"
            value={value.preprocess_profile}
            onChange={(e) => set("preprocess_profile", e.target.value)}
          >
            {PREPROCESS_SCENES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-slate-400">
            auto 模式下若檔名包含場景關鍵字則優先使用檔名偵測結果。
          </p>
        </div>
      )}

      {value.preprocess_mode === "manual" && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">選擇演算法</label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {PREPROCESS_ALGORITHMS.map((algo) => {
              const checked = value.preprocess_algorithms.includes(algo.value);
              return (
                <label
                  key={algo.value}
                  className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-xs transition-colors ${
                    checked
                      ? "border-sky-400 bg-sky-50 text-sky-800"
                      : "border-slate-200 bg-white text-slate-600 hover:border-sky-200"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleAlgorithm(algo.value)}
                    className="accent-sky-600"
                  />
                  {algo.label}
                </label>
              );
            })}
          </div>
        </div>
      )}

      {value.preprocess_mode !== "off" && (
        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={value.preprocess_enable_gamma}
              onChange={(e) => set("preprocess_enable_gamma", e.target.checked)}
              className="accent-sky-600"
            />
            追加 Gamma 校正
          </label>
        </div>
      )}

      <Button
        onClick={onPreview}
        disabled={isPreviewing || value.preprocess_mode === "off"}
        variant="outline"
        className="w-full"
      >
        {isPreviewing ? "預覽中..." : "預覽預處理結果"}
      </Button>
    </div>
  );
}

import type { TrainingEpochMetric } from "@/services/training-api";

export interface ChartSeries {
  key: keyof TrainingEpochMetric;
  label: string;
  color: string;
}

interface EpochChartProps {
  epochs: TrainingEpochMetric[];
  series: ChartSeries[];
  title?: string;
  height?: number;
}

const PAD = { top: 12, right: 16, bottom: 28, left: 48 };
const W = 500;

export function EpochChart({ epochs, series, title, height = 180 }: EpochChartProps) {
  if (epochs.length === 0) {
    return (
      <div className="flex items-center justify-center text-xs text-slate-400" style={{ height }}>
        暫無 epoch 資料
      </div>
    );
  }

  const H = height;
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const minEpoch = epochs[0].epoch;
  const maxEpoch = epochs[epochs.length - 1].epoch;
  const epochRange = Math.max(1, maxEpoch - minEpoch);

  let yMin = Infinity;
  let yMax = -Infinity;
  for (const ep of epochs) {
    for (const s of series) {
      const v = ep[s.key];
      if (typeof v === "number" && isFinite(v)) {
        if (v < yMin) yMin = v;
        if (v > yMax) yMax = v;
      }
    }
  }

  if (!isFinite(yMin) || !isFinite(yMax)) {
    return (
      <div className="flex items-center justify-center text-xs text-slate-400" style={{ height }}>
        無有效數值
      </div>
    );
  }

  const padding = (yMax - yMin) * 0.08 || 0.01;
  yMin -= padding;
  yMax += padding;
  const yRange = yMax - yMin;

  const xScale = (ep: number) => PAD.left + ((ep - minEpoch) / epochRange) * chartW;
  const yScale = (v: number) => PAD.top + chartH - ((v - yMin) / yRange) * chartH;

  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (i / 4) * yRange);
  const maxTickIdxs = Math.min(epochs.length, 7);
  const xTickIdxs = Array.from({ length: maxTickIdxs }, (_, i) =>
    Math.round((i * (epochs.length - 1)) / Math.max(1, maxTickIdxs - 1)),
  );

  return (
    <div>
      {title && <p className="mb-1 text-xs font-medium text-slate-600">{title}</p>}
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height }}>
        {/* horizontal grid */}
        {yTicks.map((v, i) => (
          <line
            key={i}
            x1={PAD.left}
            y1={yScale(v)}
            x2={W - PAD.right}
            y2={yScale(v)}
            stroke="#e2e8f0"
            strokeWidth={0.8}
          />
        ))}
        {/* y-axis labels */}
        {yTicks.map((v, i) => (
          <text
            key={i}
            x={PAD.left - 5}
            y={yScale(v) + 3.5}
            textAnchor="end"
            fontSize={9}
            fill="#94a3b8"
          >
            {Math.abs(v) < 0.01 ? v.toExponential(1) : v.toFixed(3)}
          </text>
        ))}
        {/* x-axis labels */}
        {xTickIdxs.map((idx) => {
          const ep = epochs[idx];
          return (
            <text
              key={ep.epoch}
              x={xScale(ep.epoch)}
              y={H - 4}
              textAnchor="middle"
              fontSize={9}
              fill="#94a3b8"
            >
              {ep.epoch}
            </text>
          );
        })}
        {/* polylines per series */}
        {series.map((s) => {
          const pts = epochs
            .filter((ep) => {
              const v = ep[s.key];
              return typeof v === "number" && isFinite(v);
            })
            .map((ep) => `${xScale(ep.epoch).toFixed(1)},${yScale(ep[s.key] as number).toFixed(1)}`)
            .join(" ");
          return pts ? (
            <polyline
              key={String(s.key)}
              points={pts}
              fill="none"
              stroke={s.color}
              strokeWidth={1.8}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ) : null;
        })}
        {/* dot at last epoch per series */}
        {series.map((s) => {
          const last = [...epochs].reverse().find((ep) => {
            const v = ep[s.key];
            return typeof v === "number" && isFinite(v);
          });
          if (!last) return null;
          return (
            <circle
              key={`dot-${String(s.key)}`}
              cx={xScale(last.epoch)}
              cy={yScale(last[s.key] as number)}
              r={3}
              fill={s.color}
            />
          );
        })}
      </svg>
      {/* legend */}
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 px-1">
        {series.map((s) => (
          <span key={String(s.key)} className="flex items-center gap-1 text-xs text-slate-500">
            <span
              className="inline-block h-2 w-6 rounded-full"
              style={{ background: s.color }}
            />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}

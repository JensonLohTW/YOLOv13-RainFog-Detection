export type ImageAsset = {
  id: number;
  original_name: string;
  file_url: string;
};

export type ImageAssetListResponse = {
  items: ImageAsset[];
  total: number;
};

export type PreprocessConfig = {
  preprocess_mode: "off" | "auto" | "manual";
  preprocess_profile: string;
  preprocess_algorithms: string[];
  preprocess_algorithm_params: Record<string, unknown>;
  preprocess_enable_gamma: boolean;
  scene_hint: string;
};

export type PreprocessPreviewResponse = {
  original_image_url: string;
  preview_image_url: string;
  applied: boolean;
  raw_scene: string;
  scene: string;
  scene_source: string;
  scene_debug: Record<string, unknown>;
  algorithms: string[];
};

export type DetectionTaskCreatePayload = {
  image_id: number;
  recognition_mode?: string;
  weather_scene?: string;
  confidence_threshold?: number;
  iou_threshold?: number;
} & Partial<PreprocessConfig>;

export type DetectionTaskCreateResponse = {
  task_no: string;
  status: string;
  recognition_mode: string;
};

export const PREPROCESS_ALGORITHMS = [
  { value: "dcp_dehaze", label: "DCP 去霧 (dcp_dehaze)" },
  { value: "clahe", label: "CLAHE 對比度增強 (clahe)" },
  { value: "bilateral", label: "雙邊濾波 (bilateral)" },
  { value: "white_balance", label: "白平衡 (white_balance)" },
  { value: "tone_mapping", label: "色調映射 (tone_mapping)" },
  { value: "mild_unsharp", label: "輕度銳化 (mild_unsharp)" },
  { value: "guided_filter", label: "引導濾波 (guided_filter)" },
  { value: "highlight_compression", label: "高光壓縮 (highlight_compression)" },
  { value: "gamma", label: "Gamma 校正 (gamma)" },
] as const;

export const PREPROCESS_SCENES = [
  { value: "", label: "自動偵測" },
  { value: "fog", label: "霧天 (fog)" },
  { value: "rain", label: "雨天 (rain)" },
  { value: "sandstorm", label: "沙塵暴 (sandstorm)" },
  { value: "snow", label: "雪天 (snow)" },
] as const;

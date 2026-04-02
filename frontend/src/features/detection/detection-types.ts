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

export type DetectionObject = {
  class_id: number;
  class_name: string;
  confidence: number;
  bbox: number[];
  bbox_width: number;
  bbox_height: number;
  area_ratio?: number | null;
};

export type InferenceRecord = {
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

export type DetectionTaskDetail = {
  task_no: string;
  status: string;
  recognition_mode: string;
  weather_scene: string;
  confidence_threshold: number;
  iou_threshold: number;
  runtime_options: Record<string, string | number | boolean>;
  error_message: string;
  can_retry: boolean;
  image: {
    id?: number;
    original_name: string;
    file_url: string;
  };
  latest_record: InferenceRecord | null;
  inference_records: InferenceRecord[];
  created_at: string;
  updated_at: string;
};

export type DetectionExplanationRequest = {
  task_no?: string;
  image_id?: number;
  question: string;
};

export type DetectionExplanationGrounding = {
  task_no: string;
  status: string;
  recognition_mode: string;
  weather_scene: string;
  thresholds: {
    confidence: number;
    iou: number;
  };
  image: {
    id: number;
    name: string;
    width: number | null;
    height: number | null;
  };
  inference: {
    engine_type: string;
    model_name: string;
    model_version: string;
    duration_ms: number;
    object_count: number;
    avg_confidence: number | null;
    is_mock: boolean;
  };
  object_count: number;
  class_summary: Array<{
    class_name: string;
    count: number;
    avg_confidence: number;
    max_confidence: number;
    min_confidence: number;
  }>;
  lowest_confidence_objects: Array<{
    class_name: string;
    confidence: number;
  }>;
  small_object_count: number;
  warnings: string[];
};

export type DetectionExplanationResponse = {
  task_no: string;
  image_id: number;
  question: string;
  answer: string;
  grounding: DetectionExplanationGrounding;
  llm: {
    provider: string;
    model: string;
    config_source: string;
    api_key_source: string;
  };
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

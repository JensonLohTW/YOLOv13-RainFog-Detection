import { apiGet, apiPost, apiUpload } from "@/services/api";

import type {
  DetectionTaskCreatePayload,
  DetectionTaskCreateResponse,
  ImageAsset,
  ImageAssetListResponse,
  PreprocessConfig,
  PreprocessPreviewResponse,
} from "./detection-types";

export function fetchImages(): Promise<ImageAssetListResponse> {
  return apiGet<ImageAssetListResponse>("/images");
}

export function uploadImage(file: File): Promise<ImageAsset> {
  return apiUpload<ImageAsset>("/images/upload", file);
}

export function previewPreprocess(
  imageId: number,
  config: PreprocessConfig,
): Promise<PreprocessPreviewResponse> {
  return apiPost<PreprocessPreviewResponse, Record<string, unknown>>(
    "/detection/preprocess-preview",
    {
      image_id: imageId,
      preprocess_mode: config.preprocess_mode,
      preprocess_profile: config.preprocess_profile,
      preprocess_algorithms: config.preprocess_algorithms,
      preprocess_algorithm_params: config.preprocess_algorithm_params,
      preprocess_enable_gamma: config.preprocess_enable_gamma,
      scene_hint: config.scene_hint,
    },
  );
}

export function createDetectionTask(
  payload: DetectionTaskCreatePayload,
): Promise<DetectionTaskCreateResponse> {
  return apiPost<DetectionTaskCreateResponse, DetectionTaskCreatePayload>(
    "/detection/tasks",
    payload,
  );
}

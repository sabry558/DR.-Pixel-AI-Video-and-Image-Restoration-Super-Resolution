import { ApiService } from "@/services/api";
import { API_ENDPOINTS } from "@/constants";
import type { VideoRestorationOptions } from "@/types";

export const videoService = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return ApiService.uploadFile(API_ENDPOINTS.UPLOAD_VIDEO, formData);
  },

  process: (data: { fileId: string; options: VideoRestorationOptions }) =>
    ApiService.post(API_ENDPOINTS.PROCESS_VIDEO, data),
};

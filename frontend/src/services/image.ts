import { ApiService } from "@/services/api";
import { API_ENDPOINTS } from "@/constants";
import type { ImageRestorationOptions } from "@/types";

export const imageService = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return ApiService.uploadFile(API_ENDPOINTS.UPLOAD_IMAGE, formData);
  },

  process: (data: { fileId: string; options: ImageRestorationOptions }) =>
    ApiService.post(API_ENDPOINTS.PROCESS_IMAGE, data),
};

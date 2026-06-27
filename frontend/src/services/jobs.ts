import { ApiService } from "@/services/api";
import { API_ENDPOINTS } from "@/constants";
import type { Job, JobRequest } from "@/types";

export const jobsService = {
  getAll: () => ApiService.get<Job[]>(API_ENDPOINTS.GET_JOBS),

  getById: (id: string) =>
    ApiService.get<Job>(API_ENDPOINTS.GET_JOB.replace(":id", id)),

  create: (data: JobRequest) =>
    ApiService.post<Job>(API_ENDPOINTS.CREATE_JOB, data),

  cancel: (id: string) =>
    ApiService.post(API_ENDPOINTS.CANCEL_JOB.replace(":id", id)),

  delete: (id: string) =>
    ApiService.delete(API_ENDPOINTS.DELETE_JOB.replace(":id", id)),
};

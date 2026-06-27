import { ApiService } from "@/services/api";
import { API_ENDPOINTS } from "@/constants";
import type { AuthResponse, LoginPayload, RegisterPayload, User } from "@/types";

export const authService = {
  login: (payload: LoginPayload) =>
    ApiService.post<AuthResponse>(API_ENDPOINTS.LOGIN, payload),

  register: (payload: RegisterPayload) =>
    ApiService.post<AuthResponse>(API_ENDPOINTS.REGISTER, payload),

  logout: () => ApiService.post(API_ENDPOINTS.LOGOUT),

  me: () => ApiService.get<User>(API_ENDPOINTS.ME),

  forgotPassword: (email: string) =>
    ApiService.post(API_ENDPOINTS.FORGOT_PASSWORD, { email }),
};

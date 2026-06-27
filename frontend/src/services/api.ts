import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import { API_BASE_URL, AUTH_STORAGE_KEYS } from '@/constants';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem(AUTH_STORAGE_KEYS.TOKEN);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        // Clear auth data
        localStorage.removeItem(AUTH_STORAGE_KEYS.TOKEN);
        localStorage.removeItem(AUTH_STORAGE_KEYS.USER);
        localStorage.removeItem(AUTH_STORAGE_KEYS.REFRESH_TOKEN);
        
        // Redirect to login
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// API Service class
export class ApiService {
  static get<T>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return apiClient.get<T>(url, config);
  }

  static post<T>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return apiClient.post<T>(url, data, config);
  }

  static put<T>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return apiClient.put<T>(url, data, config);
  }

  static patch<T>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return apiClient.patch<T>(url, data, config);
  }

  static delete<T>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return apiClient.delete<T>(url, config);
  }

  static uploadFile<T>(url: string, formData: FormData, config?: any): Promise<AxiosResponse<T>> {
    return apiClient.post<T>(url, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config?.headers,
      },
    });
  }
}

export default apiClient;

// Auth Types
export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface AuthResponse {
  user: User;
  token: string;
}

export interface ForgotPasswordPayload {
  email: string;
}

// Job Types
export type JobStatus = 'Queued' | 'Processing' | 'Completed' | 'Failed';
export type MediaType = 'image' | 'video';

export interface Job {
  id: string;
  name: string;
  mediaType: MediaType;
  status: JobStatus;
  progress: number;
  createdAt: string;
  updatedAt: string;
  resultUrl?: string;
  errorMessage?: string;
}

export interface JobRequest {
  name: string;
  mediaType: MediaType;
  options: Record<string, unknown>;
}

// Image Restoration
export interface ImageRestorationOptions {
  model: 'standard' | 'professional';
  scale: '2x' | '4x' | '8x';
  denoise: boolean;
  sharpen: boolean;
  faceRecovery: boolean;
}

// Video Restoration
export interface VideoRestorationOptions {
  resolution: 'original' | '720p' | '1080p' | '4k';
  frameRate: 30 | 60;
  denoise: boolean;
  stabilization: boolean;
  frameInterpolation: boolean;
}

// Pricing
export type PricingTier = 'starter' | 'pro' | 'studio';

export interface PricingPlan {
  id: PricingTier;
  name: string;
  price: number;
  jobs: string;
  exports: string;
  priority: string;
  features: string[];
}

// Showcase
export interface ShowcaseItem {
  id: string;
  title: string;
  description: string;
  category: 'vhs' | 'photo' | 'night-video' | 'historical';
  beforeImage: string;
  afterImage: string;
  improvements: string[];
}

// API Response
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  page: number;
  pageSize: number;
  total: number;
}

// Health
export interface HealthResponse {
  status: 'ok' | 'error';
  timestamp: string;
}

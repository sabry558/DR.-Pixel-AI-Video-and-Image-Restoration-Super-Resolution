export const APP_NAME = 'Dr. Pixel';
export const APP_DESCRIPTION = 'AI-powered image and video restoration platform';

// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Routes
export const ROUTES = {
  // Public routes
  HOME: '/',
  SOLUTIONS: '/solutions',
  SHOWCASE: '/showcase',
  PRICING: '/pricing',
  ABOUT: '/about',
  
  // Auth routes
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  
  // Portal routes
  PORTAL: '/portal',
  DASHBOARD: '/portal/dashboard',
  IMAGE_RESTORATION: '/portal/image-restoration',
  VIDEO_RESTORATION: '/portal/video-restoration',
  JOBS: '/portal/jobs',
  BILLING: '/portal/billing',
  SETTINGS: '/portal/settings',
  PROFILE: '/portal/settings/profile',
  SECURITY: '/portal/settings/security',
};

// Navigation
export const PUBLIC_NAV_ITEMS = [
  { label: 'Home', href: ROUTES.HOME },
  { label: 'Solutions', href: ROUTES.SOLUTIONS },
  { label: 'Showcase', href: ROUTES.SHOWCASE },
  { label: 'Pricing', href: ROUTES.PRICING },
  { label: 'About', href: ROUTES.ABOUT },
];

export const PORTAL_NAV_ITEMS = [
  { label: 'Dashboard', href: ROUTES.DASHBOARD, icon: 'LayoutDashboard' },
  { label: 'Image Restoration', href: ROUTES.IMAGE_RESTORATION, icon: 'ImagePlus' },
  { label: 'Video Restoration', href: ROUTES.VIDEO_RESTORATION, icon: 'Video' },
  { label: 'Jobs', href: ROUTES.JOBS, icon: 'Briefcase' },
  { label: 'Billing', href: ROUTES.BILLING, icon: 'CreditCard' },
  { label: 'Settings', href: ROUTES.SETTINGS, icon: 'Settings' },
];

// Features
export const FEATURES = [
  {
    id: 'super-resolution',
    title: 'Super Resolution',
    description: 'Enhance image clarity and detail with advanced AI upscaling',
  },
  {
    id: 'denoising',
    title: 'Denoising',
    description: 'Remove unwanted noise while preserving important details',
  },
  {
    id: 'deblurring',
    title: 'Deblurring',
    description: 'Sharpen blurry photos and restore lost sharpness',
  },
  {
    id: 'color-restoration',
    title: 'Color Restoration',
    description: 'Restore faded colors and improve color accuracy',
  },
  {
    id: 'artifact-removal',
    title: 'Artifact Removal',
    description: 'Eliminate compression artifacts and visual imperfections',
  },
  {
    id: 'video-enhancement',
    title: 'Video Enhancement',
    description: 'Improve video quality with intelligent frame processing',
  },
];

// Pricing Tiers
export const PRICING_TIERS = [
  {
    id: 'starter',
    name: 'Starter',
    price: 0,
    jobs: '5 jobs/month',
    exports: '720p exports',
    priority: 'Basic restoration',
    features: ['5 jobs per month', '720p export quality', 'Basic restoration models', 'Community support'],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 29,
    jobs: '100 jobs/month',
    exports: '1080p exports',
    priority: 'Priority queue',
    features: ['100 jobs per month', '1080p export quality', 'Professional models', 'Priority support', 'Advanced features'],
    popular: true,
  },
  {
    id: 'studio',
    name: 'Studio',
    price: 99,
    jobs: 'Unlimited jobs',
    exports: '4K exports',
    priority: 'Highest priority',
    features: ['Unlimited jobs', '4K export quality', 'All restoration models', '24/7 priority support', 'Custom workflows', 'Batch processing'],
  },
];

// Solutions
export const SOLUTIONS = [
  {
    id: 'image-restoration',
    title: 'Image Restoration',
    description: 'Restore damaged, old, or low-quality photographs',
    examples: ['Old photographs', 'Family albums', 'Damaged scans', 'Historical archives'],
  },
  {
    id: 'video-restoration',
    title: 'Video Restoration',
    description: 'Enhance and restore vintage or low-quality video footage',
    examples: ['VHS footage', 'Film restoration', 'Low-quality recordings', 'Social media videos'],
  },
  {
    id: 'professional-recovery',
    title: 'Professional Media Recovery',
    description: 'Advanced restoration for studios and professionals',
    examples: ['Studios', 'Archivists', 'Researchers', 'Content creators'],
  },
];

// Showcase Items
export const SHOWCASE_ITEMS = [
  {
    id: 'vhs-restoration',
    title: 'VHS Restoration',
    category: 'vhs',
    description: 'Restored vintage VHS footage with color correction and denoising',
  },
  {
    id: 'family-photo',
    title: 'Family Photo Recovery',
    category: 'photo',
    description: 'Recovered damaged family photograph with detail enhancement',
  },
  {
    id: 'night-video',
    title: 'Night Video Enhancement',
    category: 'night-video',
    description: 'Enhanced low-light video with brightness and detail restoration',
  },
  {
    id: 'historical-footage',
    title: 'Historical Footage Restoration',
    category: 'historical',
    description: 'Restored historical archive footage with color and clarity improvement',
  },
];

// Auth Storage Keys
export const AUTH_STORAGE_KEYS = {
  TOKEN: 'dr_pixel_token',
  USER: 'dr_pixel_user',
  REFRESH_TOKEN: 'dr_pixel_refresh_token',
};

// Pagination
export const PAGINATION_LIMITS = {
  DEFAULT: 20,
  JOBS_LIST: 20,
  SHOWCASE: 12,
};

// Validation
export const VALIDATION = {
  EMAIL_REGEX: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PASSWORD_MIN_LENGTH: 8,
  NAME_MIN_LENGTH: 2,
  NAME_MAX_LENGTH: 100,
};

// API Endpoints
export const API_ENDPOINTS = {
  // Auth
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
  LOGOUT: '/auth/logout',
  REFRESH: '/auth/refresh',
  FORGOT_PASSWORD: '/auth/forgot-password',
  RESET_PASSWORD: '/auth/reset-password',
  ME: '/auth/me',
  
  // Images
  UPLOAD_IMAGE: '/image/upload',
  PROCESS_IMAGE: '/image/process',
  GET_IMAGE: '/image/:id',
  
  // Videos
  UPLOAD_VIDEO: '/video/upload',
  PROCESS_VIDEO: '/video/process',
  GET_VIDEO: '/video/:id',
  
  // Jobs
  GET_JOBS: '/jobs',
  GET_JOB: '/jobs/:id',
  CREATE_JOB: '/jobs',
  CANCEL_JOB: '/jobs/:id/cancel',
  DELETE_JOB: '/jobs/:id',
  
  // Health
  HEALTH: '/health',
};

// Themes
export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  SYSTEM: 'system',
};

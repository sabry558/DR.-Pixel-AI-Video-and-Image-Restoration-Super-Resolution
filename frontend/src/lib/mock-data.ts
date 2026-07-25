import type { Job } from "@/types";

export const MOCK_JOBS: Job[] = [
  {
    id: "1",
    name: "Family Photo 1987",
    mediaType: "image",
    status: "Completed",
    progress: 100,
    createdAt: "2026-06-07T14:30:00Z",
    updatedAt: "2026-06-07T14:45:00Z",
    resultUrl: "#",
  },
  {
    id: "2",
    name: "VHS Wedding Footage",
    mediaType: "video",
    status: "Processing",
    progress: 67,
    createdAt: "2026-06-08T09:15:00Z",
    updatedAt: "2026-06-08T10:02:00Z",
  },
  {
    id: "3",
    name: "Damaged Scan Archive",
    mediaType: "image",
    status: "Queued",
    progress: 0,
    createdAt: "2026-06-08T10:30:00Z",
    updatedAt: "2026-06-08T10:30:00Z",
  },
  {
    id: "4",
    name: "Night Street Video",
    mediaType: "video",
    status: "Failed",
    progress: 34,
    createdAt: "2026-06-06T18:00:00Z",
    updatedAt: "2026-06-06T18:22:00Z",
    errorMessage: "Processing timeout",
  },
  {
    id: "5",
    name: "Historical Portrait",
    mediaType: "image",
    status: "Completed",
    progress: 100,
    createdAt: "2026-06-05T11:00:00Z",
    updatedAt: "2026-06-05T11:12:00Z",
    resultUrl: "#",
  },
];

export const MOCK_USAGE = {
  plan: "Pro",
  jobsUsed: 23,
  jobsLimit: 100,
  period: "June 2026",
};

export const MOCK_DASHBOARD_STATS = {
  total: 47,
  completed: 38,
  processing: 3,
  failed: 6,
};

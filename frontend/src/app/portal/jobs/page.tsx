"use client";

import { JobsTable } from "@/components/portal/jobs-table";
import { MOCK_JOBS } from "@/lib/mock-data";

export default function JobsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Jobs</h1>
        <p className="text-muted-foreground">Track your restoration jobs and download results.</p>
      </div>

      <JobsTable jobs={MOCK_JOBS} />
    </div>
  );
}

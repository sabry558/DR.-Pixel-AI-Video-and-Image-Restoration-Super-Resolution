"use client";

import { Briefcase, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { JobsTable } from "@/components/portal/jobs-table";
import { StatCard } from "@/components/portal/stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { MOCK_DASHBOARD_STATS, MOCK_JOBS, MOCK_USAGE } from "@/lib/mock-data";

export default function DashboardPage() {
  const recentJobs = MOCK_JOBS.slice(0, 5);
  const usagePercent = (MOCK_USAGE.jobsUsed / MOCK_USAGE.jobsLimit) * 100;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your restoration activity.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Jobs" value={MOCK_DASHBOARD_STATS.total} icon={Briefcase} />
        <StatCard title="Completed" value={MOCK_DASHBOARD_STATS.completed} icon={CheckCircle2} variant="success" />
        <StatCard title="Processing" value={MOCK_DASHBOARD_STATS.processing} icon={Loader2} variant="warning" />
        <StatCard title="Failed" value={MOCK_DASHBOARD_STATS.failed} icon={XCircle} variant="danger" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-border/50 lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <JobsTable jobs={recentJobs} />
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader>
            <CardTitle>Usage Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Current Plan</span>
                <span className="font-semibold">{MOCK_USAGE.plan}</span>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-muted-foreground">Jobs this month</span>
                <span className="font-medium">
                  {MOCK_USAGE.jobsUsed} / {MOCK_USAGE.jobsLimit}
                </span>
              </div>
              <Progress value={usagePercent} className="h-2" />
            </div>
            <p className="text-xs text-muted-foreground">
              Billing period: {MOCK_USAGE.period}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

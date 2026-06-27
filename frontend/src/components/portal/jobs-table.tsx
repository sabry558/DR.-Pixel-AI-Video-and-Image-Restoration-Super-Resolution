"use client";

import Link from "next/link";
import { Download, ImageIcon, Video } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Job, JobStatus } from "@/types";

const statusVariant: Record<JobStatus, "default" | "secondary" | "outline" | "destructive"> = {
  Queued: "secondary",
  Processing: "default",
  Completed: "outline",
  Failed: "destructive",
};

interface JobsTableProps {
  jobs: Job[];
  showDownload?: boolean;
}

export function JobsTable({ jobs, showDownload = true }: JobsTableProps) {
  return (
    <div className="rounded-xl border border-border/50">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Job Name</TableHead>
            <TableHead>Media Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Progress</TableHead>
            <TableHead>Created</TableHead>
            {showDownload && <TableHead className="text-right">Result</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => (
            <TableRow key={job.id}>
              <TableCell className="font-medium">{job.name}</TableCell>
              <TableCell>
                <span className="flex items-center gap-1.5 capitalize text-muted-foreground">
                  {job.mediaType === "image" ? (
                    <ImageIcon className="size-3.5" />
                  ) : (
                    <Video className="size-3.5" />
                  )}
                  {job.mediaType}
                </span>
              </TableCell>
              <TableCell>
                <Badge variant={statusVariant[job.status]}>{job.status}</Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Progress value={job.progress} className="h-1.5 w-20" />
                  <span className="text-xs text-muted-foreground">{job.progress}%</span>
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {new Date(job.createdAt).toLocaleDateString()}
              </TableCell>
              {showDownload && (
                <TableCell className="text-right">
                  {job.status === "Completed" && job.resultUrl ? (
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={job.resultUrl}>
                        <Download className="size-4" />
                      </Link>
                    </Button>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

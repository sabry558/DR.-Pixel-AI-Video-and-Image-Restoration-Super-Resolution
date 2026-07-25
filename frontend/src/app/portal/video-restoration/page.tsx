"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { UploadZone } from "@/components/portal/upload-zone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ROUTES } from "@/constants";

export default function VideoRestorationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState({
    resolution: "1080p",
    frameRate: "30",
    denoise: true,
    stabilization: false,
    frameInterpolation: false,
  });

  const handleStart = () => {
    setLoading(true);
    setTimeout(() => {
      router.push(ROUTES.JOBS);
    }, 1000);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Video Restoration</h1>
        <p className="text-muted-foreground">Upload a video and configure enhancement settings.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <UploadZone
            accept="video/*"
            mediaType="video"
            onFileSelect={() => {}}
          />
        </div>

        <Card className="border-border/50 lg:col-span-2">
          <CardHeader>
            <CardTitle>Options</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>Resolution</Label>
              <Select
                value={options.resolution}
                onValueChange={(v) => setOptions({ ...options, resolution: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="original">Original</SelectItem>
                  <SelectItem value="720p">720p</SelectItem>
                  <SelectItem value="1080p">1080p</SelectItem>
                  <SelectItem value="4k">4K</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Frame Rate</Label>
              <Select
                value={options.frameRate}
                onValueChange={(v) => setOptions({ ...options, frameRate: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">30 FPS</SelectItem>
                  <SelectItem value="60">60 FPS</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-4">
              <Label>Enhancements</Label>
              {[
                { key: "denoise" as const, label: "Denoise" },
                { key: "stabilization" as const, label: "Stabilization" },
                { key: "frameInterpolation" as const, label: "Frame Interpolation" },
              ].map(({ key, label }) => (
                <div key={key} className="flex items-center gap-2">
                  <Checkbox
                    id={key}
                    checked={options[key]}
                    onCheckedChange={(checked) =>
                      setOptions({ ...options, [key]: checked === true })
                    }
                  />
                  <Label htmlFor={key} className="font-normal">{label}</Label>
                </div>
              ))}
            </div>

            <Button className="w-full" onClick={handleStart} disabled={loading}>
              {loading ? "Starting..." : "Start Restoration"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

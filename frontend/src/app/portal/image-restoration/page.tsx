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

export default function ImageRestorationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState({
    model: "standard",
    scale: "2x",
    denoise: true,
    sharpen: false,
    faceRecovery: false,
  });

  const handleRestore = () => {
    setLoading(true);
    setTimeout(() => {
      router.push(ROUTES.JOBS);
    }, 1000);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Image Restoration</h1>
        <p className="text-muted-foreground">Upload an image and configure restoration settings.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <UploadZone
            accept="image/*"
            mediaType="image"
            onFileSelect={() => {}}
          />
        </div>

        <Card className="border-border/50 lg:col-span-2">
          <CardHeader>
            <CardTitle>Options</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>Model</Label>
              <Select
                value={options.model}
                onValueChange={(v) => setOptions({ ...options, model: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="professional">Professional</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Scale</Label>
              <Select
                value={options.scale}
                onValueChange={(v) => setOptions({ ...options, scale: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2x">2×</SelectItem>
                  <SelectItem value="4x">4×</SelectItem>
                  <SelectItem value="8x">8×</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-4">
              <Label>Enhancements</Label>
              {[
                { key: "denoise" as const, label: "Denoise" },
                { key: "sharpen" as const, label: "Sharpen" },
                { key: "faceRecovery" as const, label: "Face Recovery" },
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

            <Button className="w-full" onClick={handleRestore} disabled={loading}>
              {loading ? "Creating job..." : "Restore Image"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

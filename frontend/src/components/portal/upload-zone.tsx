"use client";

import { useCallback, useState } from "react";
import { Upload, X, FileImage, FileVideo } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  accept: string;
  mediaType: "image" | "video";
  onFileSelect: (file: File) => void;
}

export function UploadZone({ accept, mediaType, onFileSelect }: UploadZoneProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback(
    (f: File) => {
      setFile(f);
      onFileSelect(f);
    },
    [onFileSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) handleFile(dropped);
    },
    [handleFile]
  );

  const Icon = mediaType === "image" ? FileImage : FileVideo;

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={cn(
        "relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 transition-colors",
        isDragging ? "border-teal-500 bg-teal-500/5" : "border-border/50 hover:border-border"
      )}
    >
      {file ? (
        <div className="flex items-center gap-3">
          <Icon className="size-8 text-teal-400" />
          <div>
            <p className="font-medium">{file.name}</p>
            <p className="text-sm text-muted-foreground">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <button
            type="button"
            onClick={() => setFile(null)}
            className="ml-4 rounded-lg p-1 hover:bg-muted"
          >
            <X className="size-4" />
          </button>
        </div>
      ) : (
        <>
          <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-muted">
            <Upload className="size-6 text-muted-foreground" />
          </div>
          <p className="text-sm font-medium">Drag and drop your {mediaType} here</p>
          <p className="mt-1 text-xs text-muted-foreground">or click to browse</p>
          <input
            type="file"
            accept={accept}
            className="absolute inset-0 cursor-pointer opacity-0"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
        </>
      )}
    </div>
  );
}

"use client";

import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface BeforeAfterSliderProps {
  beforeLabel?: string;
  afterLabel?: string;
  className?: string;
}

export function BeforeAfterSlider({
  beforeLabel = "Before",
  afterLabel = "After",
  className,
}: BeforeAfterSliderProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);

  const updatePosition = useCallback((clientX: number) => {
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    setPosition((x / rect.width) * 100);
  }, []);

  const handlePointerDown = (e: React.PointerEvent) => {
    setIsDragging(true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    updatePosition(e.clientX);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging) return;
    updatePosition(e.clientX);
  };

  const handlePointerUp = () => setIsDragging(false);

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative aspect-[16/10] w-full cursor-col-resize select-none overflow-hidden rounded-2xl ring-1 ring-border",
        className
      )}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
    >
      {/* After (enhanced) — full background */}
      <div className="absolute inset-0 bg-gradient-to-br from-teal-900/80 via-slate-800 to-cyan-900/60">
        <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_70%_40%,rgba(45,212,191,0.4),transparent_60%)]" />
        <div className="absolute bottom-4 right-4 rounded-full bg-teal-500/20 px-3 py-1 text-xs font-medium text-teal-300 backdrop-blur-sm">
          {afterLabel}
        </div>
      </div>

      {/* Before (degraded) — clipped */}
      <div
        className="absolute inset-0 bg-gradient-to-br from-stone-700 via-stone-800 to-stone-900"
        style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
      >
        <div className="absolute inset-0 opacity-50 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiPgo8cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuMDUiLz4KPC9zdmc+')]" />
        <div className="absolute bottom-4 left-4 rounded-full bg-stone-500/20 px-3 py-1 text-xs font-medium text-stone-300 backdrop-blur-sm">
          {beforeLabel}
        </div>
      </div>

      {/* Divider */}
      <div
        className="absolute top-0 bottom-0 z-10 w-0.5 bg-white/80 shadow-[0_0_12px_rgba(255,255,255,0.5)]"
        style={{ left: `${position}%`, transform: "translateX(-50%)" }}
      >
        <div className="absolute top-1/2 left-1/2 flex size-10 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 border-white/80 bg-background/90 shadow-lg backdrop-blur-sm">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-foreground">
            <path d="M5 4L1 8L5 12M11 4L15 8L11 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
    </div>
  );
}

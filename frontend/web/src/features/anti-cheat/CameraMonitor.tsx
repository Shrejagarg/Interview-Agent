"use client";

import type { RefObject } from "react";
import type { CameraStatus } from "./useCameraMonitor";

interface CameraMonitorProps {
  enabled?: boolean;
  /** Refs/status come from the owning `useCameraMonitor` so the page can react. */
  videoRef: RefObject<HTMLVideoElement>;
  status: CameraStatus;
}

const STATUS_LABEL: Record<CameraStatus, string> = {
  prompting: "CONNECTING CAMERA",
  active: "CAMERA ON",
  face_lost: "FACE OUT OF VIEW",
  denied: "CAMERA BLOCKED",
  unsupported: "CAMERA UNAVAILABLE",
};

const STATUS_STYLE: Record<CameraStatus, string> = {
  prompting: "text-gray-400 border-brutal-border",
  active: "text-emerald-400 border-emerald-400",
  face_lost: "text-accent border-accent",
  denied: "text-amber-400 border-amber-400",
  unsupported: "text-gray-500 border-brutal-border",
};

/**
 * Small fixed-position camera preview + presence status shown during an
 * interview. Purely presentational — the owning `useCameraMonitor` supplies the
 * video ref and status so the page can react to a lost face.
 */
export function CameraMonitor({ enabled = true, videoRef, status }: CameraMonitorProps) {
  if (!enabled) return null;
  if (status === "unsupported" || status === "denied") {
    return (
      <div className="fixed bottom-4 right-4 z-50 border-2 bg-black px-3 py-2 text-[10px] font-heading uppercase tracking-widest text-gray-500 border-brutal-border">
        {STATUS_LABEL[status]}
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-40 border-2 border-brutal-border bg-black shadow-lg">
      <video
        ref={videoRef}
        muted
        playsInline
        aria-label="Interview camera preview"
        className="block h-28 w-full object-cover bg-brutal-dark"
      />
      <div
        className={`flex items-center justify-center gap-1.5 border-t px-2 py-1.5 text-[10px] font-heading uppercase tracking-widest ${STATUS_STYLE[status]}`}
      >
        {status === "active" && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />}
        {status === "face_lost" && <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" />}
        {STATUS_LABEL[status]}
      </div>
    </div>
  );
}

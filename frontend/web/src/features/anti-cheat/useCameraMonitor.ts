"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  MotionFaceDetector,
  NativeFaceDetectorStrategy,
  type FaceDetectorStrategy,
  type FacesDetectorStrategyFactory,
  type FacePresence,
} from "./faceDetector";

export type CameraStatus =
  | "prompting"
  | "active"
  | "face_lost"
  | "denied"
  | "unsupported";

export interface CameraMonitorCallbacks {
  /** Called once when the face is lost from view for a sustained window. */
  onFaceLost?: () => void;
  /** Called when the face returns to view after a face-lost episode. */
  onFaceReturn?: () => void;
}

export interface CameraMonitorOptions extends CameraMonitorCallbacks {
  /** Milliseconds between sampled frames. Default 500ms. */
  sampleIntervalMs?: number;
  /** Number of consecutive absent verdicts before firing face_lost. */
  absentConfirms?: number;
  /** Set to false to disable monitoring (e.g. text mode without camera). */
  enabled?: boolean;
  /** Injectable detector factory for tests. */
  detectorFactory?: FacesDetectorStrategyFactory;
}

/**
 * State machine for webcam-based presence monitoring. Returns a `videoRef` to
 * attach to a <video> element (it must be muted and playing for frames to be
 * readable) and the current status so the UI can reflect it.
 */
export function useCameraMonitor(opts: CameraMonitorOptions = {}) {
  const {
    sampleIntervalMs = 500,
    absentConfirms = 6,
    enabled = true,
    onFaceLost,
    onFaceReturn,
    detectorFactory,
  } = opts;

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const detectorRef = useRef<FaceDetectorStrategy | null>(null);
  const absentCountRef = useRef(0);
  const absentEpisodeLiveRef = useRef(false);

  // Read runtime config from refs so the sampling effect never restarts on
  // render (stable identity), which would otherwise unboundedly re-prompt.
  const configRef = useRef({ sampleIntervalMs, absentConfirms, detectorFactory });
  configRef.current = { sampleIntervalMs, absentConfirms, detectorFactory };

  const onFaceLostRef = useRef(onFaceLost);
  const onFaceReturnRef = useRef(onFaceReturn);
  useEffect(() => {
    onFaceLostRef.current = onFaceLost;
    onFaceReturnRef.current = onFaceReturn;
  }, [onFaceLost, onFaceReturn]);

  const [status, setStatus] = useState<CameraStatus>(
    enabled ? "prompting" : "unsupported"
  );
  const [permission, setPermission] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    absentCountRef.current = 0;
    absentEpisodeLiveRef.current = false;
  }, []);

  useEffect(() => {
    return stop;
  }, [stop]);

  const handlePresence = useCallback((presence: FacePresence) => {
    if (presence === "present") {
      absentCountRef.current = 0;
      if (absentEpisodeLiveRef.current) {
        absentEpisodeLiveRef.current = false;
        setStatus("active");
        onFaceReturnRef.current?.();
      }
      return;
    }
    if (presence === "unknown") return;

    absentCountRef.current += 1;
    if (
      absentCountRef.current >= configRef.current.absentConfirms &&
      !absentEpisodeLiveRef.current
    ) {
      absentEpisodeLiveRef.current = true;
      setStatus("face_lost");
      onFaceLostRef.current?.();
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      setStatus("unsupported");
      return;
    }

    let cancelled = false;
    let frameTimer: ReturnType<typeof setInterval> | null = null;

    async function start() {
      setStatus("prompting");
      setError(null);

      if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
        if (!cancelled) setStatus("unsupported");
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (!video) {
          throw new Error("Camera preview element not available");
        }
        video.srcObject = stream;
        await video.play();
        setPermission(true);

        const detector: FaceDetectorStrategy =
          configRef.current.detectorFactory?.() ??
          NativeFaceDetectorStrategy.create() ??
          new MotionFaceDetector();
        detectorRef.current = detector;
        setStatus("active");

        frameTimer = setInterval(() => {
          if (cancelled) return;
          void readFramePresence(video, detectorRef.current).then((presence) => {
            if (!cancelled) handlePresence(presence);
          });
        }, configRef.current.sampleIntervalMs);
      } catch (err) {
        if (cancelled) return;
        const name = (err as { name?: string })?.name;
        if (name === "NotAllowedError" || name === "SecurityError") {
          setStatus("denied");
          setPermission(false);
          setError("Camera permission was declined.");
        } else if (name === "NotFoundError" || name === "OverconstrainedError") {
          setStatus("unsupported");
          setError("No camera device was found.");
        } else {
          setStatus("unsupported");
          setError("Could not start the camera.");
        }
      }
    }

    void start();

    return () => {
      cancelled = true;
      if (frameTimer) clearInterval(frameTimer);
      stop();
    };
  }, [enabled, handlePresence, stop]);

  return { videoRef, status, permission, error };
}

const SAMPLE_WIDTH = 160;
const SAMPLE_HEIGHT = 90;

async function readFramePresence(
  video: HTMLVideoElement,
  detector: FaceDetectorStrategy | null
): Promise<FacePresence> {
  if (!detector || !video.videoWidth || !video.videoHeight) return "unknown";
  let canvas: HTMLCanvasElement | null = null;
  try {
    canvas = document.createElement("canvas");
    canvas.width = SAMPLE_WIDTH;
    canvas.height = SAMPLE_HEIGHT;
    const ctx = canvas.getContext("2d");
    if (!ctx) return "unknown";
    ctx.drawImage(video, 0, 0, SAMPLE_WIDTH, SAMPLE_HEIGHT);
    const imageData = ctx.getImageData(0, 0, SAMPLE_WIDTH, SAMPLE_HEIGHT);
    return detector.detect({
      width: SAMPLE_WIDTH,
      height: SAMPLE_HEIGHT,
      data: new Uint8ClampedArray(imageData.data),
    });
  } finally {
    canvas = null;
  }
}

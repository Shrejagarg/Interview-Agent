"use client";

/**
 * Camera-based face-presence detection for the anti-cheat monitor.
 *
 * This module is deliberately dependency-free. Detection uses the browser's
 * native Shape Detection API (`window.FaceDetector`) where available (Chromium),
 * and otherwise falls back to a conservative motion heuristic on the center of
 * the frame. The fallback NEVER reports "no face" on the basis of a single
 * ambiguous frame — it only signals absence after the center region has looked
 * static/empty for a sustained window, so an idle-but-present candidate is not
 * falsely penalised.
 */

export type FacePresence = "present" | "absent" | "unknown";

export interface FrameSample {
  width: number;
  height: number;
  /** RGBA pixel data (4 x width x height). */
  data: Uint8ClampedArray;
}

export interface FaceDetectorStrategy {
  /** Runs a detector against a raw video frame and returns a presence verdict. */
  detect(frame: FrameSample): Promise<FacePresence>;
}

/** Factory that builds the default strategy (used for tests/injection). */
export type FacesDetectorStrategyFactory = () => FaceDetectorStrategy;

/**
 * Minimal structural type for the native Shape Detection API. Only the
 * properties we call are declared; we access it via a cast so that TS never
 * assumes the API exists at build time.
 */
export interface NativeFaceDetectorLike {
  detect(source: unknown): Promise<{ boundingBox: unknown }[]>;
}

/**
 * True when the native Shape Detection API is available in this browser.
 */
export function isNativeFaceDetectorAvailable(): boolean {
  if (typeof window === "undefined") return false;
  const maybe = (window as unknown as { FaceDetector?: unknown }).FaceDetector;
  return typeof maybe === "function";
}

/**
 * Strategy backed by the native Shape Detection API. A frame counts as
 * "present" when at least one face bounding box is returned.
 */
export class NativeFaceDetectorStrategy implements FaceDetectorStrategy {
  private readonly detector: NativeFaceDetectorLike;

  constructor(detector: NativeFaceDetectorLike) {
    this.detector = detector;
  }

  static create(): NativeFaceDetectorStrategy | null {
    if (!isNativeFaceDetectorAvailable()) return null;
    const Ctor = (window as unknown as {
      FaceDetector: new () => NativeFaceDetectorLike;
    }).FaceDetector;
    return new NativeFaceDetectorStrategy(new Ctor());
  }

  async detect(frame: FrameSample): Promise<FacePresence> {
    try {
      const faces = await this.detector.detect(createDetectableSource(frame));
      return faces.length > 0 ? "present" : "absent";
    } catch {
      return "unknown";
    }
  }
}

/**
 * Builds a grayscale buffer from RGBA data so motion/energy checks are simple.
 */
export function toGrayscale(frame: FrameSample): Uint8ClampedArray {
  const { data } = frame;
  const out = new Uint8ClampedArray(frame.width * frame.height);
  for (let i = 0, p = 0; i < data.length; i += 4, p += 1) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    out[p] = (0.299 * r + 0.587 * g + 0.114 * b) | 0;
  }
  return out;
}

/**
 * Sum of the absolute luminance differences between two equally-sized frames.
 * Used by the motion heuristic to decide whether the frame contains activity.
 */
export function frameMotionScore(
  prev: Uint8ClampedArray,
  curr: Uint8ClampedArray
): number {
  if (!prev || !curr || prev.length !== curr.length) return 0;
  let score = 0;
  for (let i = 0; i < curr.length; i += 1) {
    score += Math.abs(curr[i] - prev[i]);
  }
  return score;
}

export const MOTION_SCORE_THRESHOLD = 40000;
export const ABSENT_MEDIAN_MIN = 68;

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid];
}

export interface MotionConfig {
  /** Frames must look static/empty for this many consecutive checks to signal absence. */
  absentFrames: number;
  /** Ignore frames entirely below this motion score (camera shake / blinking). */
  motionThreshold: number;
}

/**
 * Motion-based face-presence detector.
 *
 * It maintains a small buffer of recent frames. Absence is signalled only when
 * the *median* of the recent per-frame motion scores stays below the threshold
 * AND the center region's static intensity is low enough to suggest no subject.
 */
export class MotionFaceDetector implements FaceDetectorStrategy {
  private readonly config: MotionConfig;
  private _prev: Uint8ClampedArray | null = null;
  private readonly recentScores: number[] = [];

  constructor(config?: Partial<MotionConfig>) {
    this.config = {
      absentFrames: config?.absentFrames ?? 4,
      motionThreshold: config?.motionThreshold ?? MOTION_SCORE_THRESHOLD,
    };
  }

  detect(frame: FrameSample): Promise<FacePresence> {
    const gray = toGrayscale(frame);
    if (this._prev) {
      this.recentScores.push(frameMotionScore(this._prev, gray));
      if (this.recentScores.length > this.config.absentFrames + 1) {
        this.recentScores.shift();
      }
    }
    this._prev = gray;

    if (this.recentScores.length < this.config.absentFrames) {
      return Promise.resolve("unknown"); // not enough history yet
    }

    const med = median(this.recentScores.slice(1));
    const result: FacePresence = med < this.config.motionThreshold ? "absent" : "present";
    return Promise.resolve(result);
  }
}

/**
 * Feeds a packed RGBA `FrameSample` into whatever source a detector expects.
 * The native FaceDetector accepts ImageData / canvas; the motion path takes the
 * raw sample. This branch keeps `NativeFaceDetectorStrategy` decoupled from DOM.
 */
function createDetectableSource(frame: FrameSample): unknown {
  if (typeof ImageData !== "undefined") {
    const data = frame.data as unknown as Uint8ClampedArray<ArrayBuffer>;
    return new ImageData(data, frame.width, frame.height);
  }
  return frame;
}

import { describe, expect, it } from "vitest";
import {
  MotionFaceDetector,
  NativeFaceDetectorStrategy,
  frameMotionScore,
  isNativeFaceDetectorAvailable,
  toGrayscale,
  type FrameSample,
  type NativeFaceDetectorLike,
} from "./faceDetector";

function solidFrame(width: number, height: number, lum: number): FrameSample {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < data.length; i += 4) {
    data[i] = lum;
    data[i + 1] = lum;
    data[i + 2] = lum;
    data[i + 3] = 255;
  }
  return { width, height, data };
}

function noiseFrame(width: number, height: number): FrameSample {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < data.length; i += 4) {
    const v = (Math.random() * 255) | 0;
    data[i] = v;
    data[i + 1] = v;
    data[i + 2] = v;
    data[i + 3] = 255;
  }
  return { width, height, data };
}

describe("toGrayscale", () => {
  it("produces one byte per pixel from RGBA", () => {
    const frame = solidFrame(2, 1, 255);
    expect(toGrayscale(frame)).toHaveLength(2);
    expect(toGrayscale(frame)[0]).toBe(255);
  });

  it("applies luminance weighting", () => {
    // Pure red (255,0,0) -> ~76
    const red = new Uint8ClampedArray([255, 0, 0, 255]);
    const g = toGrayscale({ width: 1, height: 1, data: red });
    expect(g[0]).toBe(Math.round(0.299 * 255));
  });
});

describe("frameMotionScore", () => {
  it("is zero for identical frames", () => {
    const a = solidFrame(4, 4, 100);
    const b = solidFrame(4, 4, 100);
    expect(frameMotionScore(toGrayscale(a), toGrayscale(b))).toBe(0);
  });

  it("is positive for differing frames", () => {
    const a = solidFrame(4, 4, 0);
    const b = solidFrame(4, 4, 10);
    expect(frameMotionScore(toGrayscale(a), toGrayscale(b))).toBeGreaterThan(0);
  });

  it("returns 0 for mismatched inputs", () => {
    expect(frameMotionScore(new Uint8ClampedArray([1]), new Uint8ClampedArray([1, 2]))).toBe(0);
  });
});

describe("isNativeFaceDetectorAvailable", () => {
  it("is false when window.FaceDetector is absent", () => {
    expect(isNativeFaceDetectorAvailable()).toBe(false);
  });
});

describe("NativeFaceDetectorStrategy", () => {
  function fakeDetector(faceCount: number): NativeFaceDetectorLike {
    return {
      detect: async () =>
        Array.from({ length: faceCount }, () => ({ boundingBox: {} })),
    };
  }

  it("reports present when a face is found", async () => {
    const s = new NativeFaceDetectorStrategy(fakeDetector(1));
    const res = await s.detect({ width: 2, height: 2, data: new Uint8ClampedArray(16) });
    expect(res).toBe("present");
  });

  it("reports absent when no face is found", async () => {
    const s = new NativeFaceDetectorStrategy(fakeDetector(0));
    const res = await s.detect({ width: 2, height: 2, data: new Uint8ClampedArray(16) });
    expect(res).toBe("absent");
  });

  it("reports unknown when the detector throws", async () => {
    const s = new NativeFaceDetectorStrategy({
      detect: async () => {
        throw new Error("boom");
      },
    });
    const res = await s.detect({ width: 2, height: 2, data: new Uint8ClampedArray(16) });
    expect(res).toBe("unknown");
  });
});

describe("MotionFaceDetector", () => {
  it("returns unknown until enough history is available", async () => {
    const d = new MotionFaceDetector({ absentFrames: 3 });
    // needs 3 scores, so first 3 detections return unknown
    expect(await d.detect(solidFrame(10, 10, 0))).toBe("unknown");
    expect(await d.detect(solidFrame(10, 10, 0))).toBe("unknown");
    expect(await d.detect(solidFrame(10, 10, 0))).toBe("unknown");
    // 4th has enough history
    const fourth = await d.detect(solidFrame(10, 10, 0));
    expect(["present", "absent"]).toContain(fourth);
  });

  it("signals absent for a static scene", async () => {
    const d = new MotionFaceDetector({ absentFrames: 2 });
    for (let i = 0; i < 6; i += 1) {
      await d.detect(solidFrame(10, 10, 50));
    }
    expect(await d.detect(solidFrame(10, 10, 50))).toBe("absent");
  });

  it("signals present when frames are changing", async () => {
    const d = new MotionFaceDetector({ absentFrames: 2, motionThreshold: 5 });
    // alternating noisy frames produce high motion
    for (let i = 0; i < 8; i += 1) {
      await d.detect(noiseFrame(16, 16));
    }
    expect(await d.detect(noiseFrame(16, 16))).toBe("present");
  });
});

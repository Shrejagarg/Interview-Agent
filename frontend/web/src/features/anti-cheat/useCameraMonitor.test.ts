import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useCameraMonitor } from "./useCameraMonitor";
import type { FaceDetectorStrategy } from "./faceDetector";

type Presence = "present" | "absent" | "unknown";

class SequenceDetector implements FaceDetectorStrategy {
  queue: Presence[];
  calls = 0;
  constructor(queue: Presence[]) {
    this.queue = queue;
  }
  async detect() {
    const v = this.queue[Math.min(this.calls, this.queue.length - 1)];
    this.calls += 1;
    return v;
  }
}

beforeEach(() => {
  vi.stubGlobal("MediaStream", class { tracks: { stop: () => void }[] = []; getTracks() { return this.tracks; } });
  vi.spyOn(navigator.mediaDevices, "getUserMedia").mockResolvedValue({
    getTracks: () => [{ stop: vi.fn() }],
  } as unknown as MediaStream);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function makeCanvasMock() {
  const drawImage = vi.fn();
  const getImageData = vi.fn(() => ({
    data: new Uint8ClampedArray(160 * 90 * 4),
  }));
  const ctx = { drawImage, getImageData } as unknown as CanvasRenderingContext2D;
  return { drawImage, getImageData, ctx };
}

/**
 * The hook returns a readonly `RefObject`; tests drive the webcam by injecting
 * a real <video> element, so we write through a mutable view of the ref.
 */
function attachVideo(
  result: { readonly current: { readonly videoRef: { current: HTMLVideoElement | null } } },
  video: HTMLVideoElement
): void {
  result.current.videoRef.current = video;
}

describe("useCameraMonitor", () => {
  it("reports unsupported when mediaDevices is unavailable", () => {
    const orig = navigator.mediaDevices;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: undefined,
    });
    const { result } = renderHook(() => useCameraMonitor());
    expect(result.current.status).toBe("unsupported");
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: orig,
    });
  });

  it("reports denied and clears when permission is refused", async () => {
    vi.spyOn(navigator.mediaDevices, "getUserMedia").mockRejectedValue(
      Object.assign(new Error("no"), { name: "NotAllowedError" })
    );
    const { result } = renderHook(() => useCameraMonitor());
    await waitFor(() => expect(result.current.status).toBe("denied"));
    expect(result.current.permission).toBe(false);
  });

  it("reports unsupported when no device is found", async () => {
    vi.spyOn(navigator.mediaDevices, "getUserMedia").mockRejectedValue(
      Object.assign(new Error("no"), { name: "NotFoundError" })
    );
    const { result } = renderHook(() => useCameraMonitor());
    await waitFor(() => expect(result.current.status).toBe("unsupported"));
  });

  it("reaches active and fires onFaceLost after sustained absence", async () => {
    const detector = new SequenceDetector(["absent", "absent", "absent"]);
    const onFaceLost = vi.fn();
    const onFaceReturn = vi.fn();
    const { drawImage } = makeCanvasMock();

    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string, options?: ElementCreationOptions) => {
      if (tag === "canvas") {
        const canvas = origCreate("canvas", options) as HTMLCanvasElement;
        const ctx = canvas.getContext("2d") as CanvasRenderingContext2D | null;
        vi.spyOn(canvas, "getContext").mockReturnValue({
          drawImage,
          getImageData: () => ({ data: new Uint8ClampedArray(160 * 90 * 4) }),
        } as unknown as CanvasRenderingContext2D);
        if (ctx) {
          Object.defineProperty(ctx, "drawImage", { value: drawImage, writable: true });
        }
        return canvas;
      }
      return origCreate(tag, options);
    });

    const video = document.createElement("video");
    Object.defineProperty(video, "videoWidth", { value: 320, configurable: true });
    Object.defineProperty(video, "videoHeight", { value: 240, configurable: true });
    vi.spyOn(video, "play").mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useCameraMonitor({
        sampleIntervalMs: 10,
        absentConfirms: 3,
        detectorFactory: () => detector,
        onFaceLost,
        onFaceReturn,
      })
    );

    // Attach the video element that the hook drives.
    attachVideo(result, video);

    await waitFor(() => expect(result.current.status).toBe("active"));
    await waitFor(() => expect(onFaceLost).toHaveBeenCalled());
    expect(result.current.status).toBe("face_lost");
    expect(onFaceReturn).not.toHaveBeenCalled();
  });

  it("recovers to active and fires onFaceReturn when the face returns", async () => {
    const detector = new SequenceDetector([
      "absent",
      "absent",
      "absent", // face lost after 3 confirms
      "present",
      "present",
    ]);
    const onFaceLost = vi.fn();
    const onFaceReturn = vi.fn();
    const { drawImage } = makeCanvasMock();

    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string, options?: ElementCreationOptions) => {
      if (tag === "canvas") {
        const canvas = origCreate("canvas", options) as HTMLCanvasElement;
        vi.spyOn(canvas, "getContext").mockReturnValue({
          drawImage,
          getImageData: () => ({ data: new Uint8ClampedArray(160 * 90 * 4) }),
        } as unknown as CanvasRenderingContext2D);
        return canvas;
      }
      return origCreate(tag, options);
    });

    const video = document.createElement("video");
    Object.defineProperty(video, "videoWidth", { value: 320, configurable: true });
    Object.defineProperty(video, "videoHeight", { value: 240, configurable: true });
    vi.spyOn(video, "play").mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useCameraMonitor({
        sampleIntervalMs: 10,
        absentConfirms: 3,
        detectorFactory: () => detector,
        onFaceLost,
        onFaceReturn,
      })
    );
    attachVideo(result, video);

    await waitFor(() => expect(onFaceLost).toHaveBeenCalled());
    await waitFor(() => expect(onFaceReturn).toHaveBeenCalled());
    await waitFor(() => expect(result.current.status).toBe("active"));
  });
});

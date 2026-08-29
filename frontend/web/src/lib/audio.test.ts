import { describe, expect, it } from "vitest";
import {
  base64ToUint8Array,
  blobToDataUrl,
  buildWav,
  isPlayableDataUrl,
  makeSilenceDataUri,
  mimeExtension,
  toAudioDataUri,
  uint8ToBase64,
} from "./audio";

function ascii(bytes: Uint8Array, offset: number, length: number): string {
  let out = "";
  for (let i = 0; i < length; i += 1) out += String.fromCharCode(bytes[offset + i]);
  return out;
}

describe("uint8ToBase64 / base64ToUint8Array", () => {
  it("round-trips arbitrary bytes", () => {
    const input = new Uint8Array([0, 1, 2, 254, 255, 128, 77, 111, 104, 97, 110]);
    expect(base64ToUint8Array(uint8ToBase64(input))).toEqual(input);
  });

  it("round-trips empty array", () => {
    expect(uint8ToBase64(new Uint8Array(0))).toBe("");
    // Empty padding edge: base64 of [] decodes to []. Pi  (this matches spec: atob("") === "")
    expect(base64ToUint8Array("")).toHaveLength(0);
  });

  it("decodes known vector", () => {
    expect(uint8ToBase64(new Uint8Array([77, 111, 104, 97, 110]))).toBe("TW9oYW4=");
    expect(base64ToUint8Array("TW9oYW4=")).toEqual(
      new Uint8Array([77, 111, 104, 97, 110])
    );
  });

  it("strips whitespace and data-uri prefixes", () => {
    expect(base64ToUint8Array("data:audio/wav;base64,\n  TW9o YW4=  ")).toEqual(
      new Uint8Array([77, 111, 104, 97, 110])
    );
  });

  it("rejects invalid base64", () => {
    expect(() => base64ToUint8Array("TW9oYW4!")).toThrow("Invalid base64");
  });

  it("rejects base64 with wrong padding counts", () => {
    expect(() => base64ToUint8Array("TW9oYW4===")).toThrow("Invalid base64");
  });
});

describe("buildWav", () => {
  it("emits a PCM mono header with the right little-endian fields", () => {
    const wav = buildWav(new Int16Array(0), 8000, 1);
    const view = new DataView(wav.buffer);
    expect(wav.byteLength).toBe(44);
    expect(ascii(wav, 0, 4)).toBe("RIFF");
    expect(view.getUint32(4, true)).toBe(36);
    expect(ascii(wav, 8, 4)).toBe("WAVE");
    expect(ascii(wav, 12, 4)).toBe("fmt ");
    expect(view.getUint32(16, true)).toBe(16);
    expect(view.getUint16(20, true)).toBe(1);
    expect(view.getUint16(22, true)).toBe(1);
    expect(view.getUint32(24, true)).toBe(8000);
    expect(view.getUint32(28, true)).toBe(16000);
    expect(view.getUint16(32, true)).toBe(2);
    expect(view.getUint16(34, true)).toBe(16);
    expect(ascii(wav, 36, 4)).toBe("data");
    expect(view.getUint32(40, true)).toBe(0);
  });

  it("stores samples as little-endian signed 16-bit", () => {
    const positive = buildWav(new Int16Array([1000]), 8000, 1);
    expect(positive[44]).toBe(0xe8);
    expect(positive[45]).toBe(0x03);

    const negative = buildWav(new Int16Array([-1000]), 8000, 1);
    expect(negative[44]).toBe(0x18);
    expect(negative[45]).toBe(0xfc);

    expect(negative.byteLength).toBe(46);
    expect(new DataView(negative.buffer).getUint32(4, true)).toBe(38);
  });

  it("rejects non-positive sample rates", () => {
    expect(() => buildWav(new Int16Array(0), 0)).toThrow(RangeError);
    expect(() => buildWav(new Int16Array(0), -1)).toThrow(RangeError);
    expect(() => buildWav(new Int16Array(0), 7999.5)).toThrow(RangeError);
    expect(() => buildWav(new Int16Array(0), NaN)).toThrow(RangeError);
  });

  it("rejects zero channels", () => {
    expect(() => buildWav(new Int16Array(0), 8000, 0)).toThrow(RangeError);
  });

  it("honours channels in byte rate and block align", () => {
    const stereo = buildWav(new Int16Array(2), 8000, 2);
    const view = new DataView(stereo.buffer);
    expect(view.getUint16(22, true)).toBe(2);
    expect(view.getUint32(28, true)).toBe(32000);
    expect(view.getUint16(32, true)).toBe(4);
    expect(view.getUint32(40, true)).toBe(4);
    expect(stereo.byteLength).toBe(48);
  });

  it("matches the expected byte count for a long buffer", () => {
    const wav = buildWav(new Int16Array(100_000), 44_100, 1);
    expect(wav.byteLength).toBe(44 + 200_000);
  });
});

describe("makeSilenceDataUri", () => {
  it("produces a valid audio/wav data uri for 0.5s at 8k", () => {
    const uri = makeSilenceDataUri(0.5, 8000, 1);
    expect(isPlayableDataUrl(uri)).toBe(true);
    const bytes = base64ToUint8Array(uri);
    expect(bytes.byteLength).toBe(44 + 8000);
    expect(ascii(bytes, 0, 4)).toBe("RIFF");
    expect(new DataView(bytes.buffer).getUint32(24, true)).toBe(8000);
    expect(new DataView(bytes.buffer).getUint32(40, true)).toBe(8000);
  });

  it("supports zero-length audio (header-only, 44 bytes)", () => {
    const uri = makeSilenceDataUri(0, 8000, 1);
    expect(base64ToUint8Array(uri).byteLength).toBe(44);
  });

  it("encodes stereo at double byte rate", () => {
    const bytes = base64ToUint8Array(makeSilenceDataUri(0.25, 8000, 2));
    expect(bytes.byteLength).toBe(44 + 8000);
    expect(new DataView(bytes.buffer).getUint16(22, true)).toBe(2);
  });

  it("rejects negative, non-finite and non-numeric durations", () => {
    expect(() => makeSilenceDataUri(-1)).toThrow(RangeError);
    expect(() => makeSilenceDataUri(NaN)).toThrow(RangeError);
    expect(() => makeSilenceDataUri(Infinity)).toThrow(RangeError);
    expect(() => makeSilenceDataUri("0.5" as unknown as number)).toThrow(RangeError);
  });

  it("rejects durations over the sanity cap", () => {
    expect(() => makeSilenceDataUri(60.001)).toThrow(RangeError);
  });

  it("rejects out-of-range sample rates and channel counts", () => {
    expect(() => makeSilenceDataUri(0.5, 7999)).toThrow(RangeError);
    expect(() => makeSilenceDataUri(0.5, 96001)).toThrow(RangeError);
    expect(() => makeSilenceDataUri(0.5, 8000, 0)).toThrow(RangeError);
    expect(() => makeSilenceDataUri(0.5, 8000, 9)).toThrow(RangeError);
  });

  it("decodes a long clip back to the exact header bytes", () => {
    const bytes = base64ToUint8Array(makeSilenceDataUri(0.6, 8000, 1));
    expect(bytes.byteLength).toBe(44 + 9600);
    expect(bytes.slice(20, 22)).toEqual(new Uint8Array([1, 0]));
    expect(bytes.slice(40, 44)).toEqual(new Uint8Array([128, 37, 0, 0]));
  });
});

describe("toAudioDataUri", () => {
  it("prefixes raw base64 with a default audio/mp3 mime", () => {
    expect(toAudioDataUri("SGVsbG8=")).toBe("data:audio/mp3;base64,SGVsbG8=");
  });

  it("prefixes with a caller-supplied mime", () => {
    expect(toAudioDataUri("SGVsbG8=", "audio/wav")).toBe("data:audio/wav;base64,SGVsbG8=");
  });

  it("passes already-prefixed data uris through untouched", () => {
    const existing = "data:audio/mp3;base64,SGVsbG8=";
    expect(toAudioDataUri(existing)).toBe(existing);
  });

  it("rejects empty, whitespace and non-string payloads", () => {
    expect(() => toAudioDataUri("")).toThrow("Empty audio");
    expect(() => toAudioDataUri("   ")).toThrow("Empty audio");
    expect(() => toAudioDataUri(undefined as unknown as string)).toThrow("Empty audio");
    expect(() => toAudioDataUri(null as unknown as string)).toThrow("Empty audio");
  });
});

describe("isPlayableDataUrl", () => {
  const valid = "data:audio/webm;base64,U29tZUF1ZGlv";
  it("accepts well-formed audio data uris", () => {
    expect(isPlayableDataUrl(valid)).toBe(true);
    expect(isPlayableDataUrl("data:audio/mp3;base64,QUJD")).toBe(true);
  });

  it("rejects non-audio mime, missing payload and missing base64 marker", () => {
    expect(isPlayableDataUrl("data:video/webm;base64,QUJD")).toBe(false);
    expect(isPlayableDataUrl("data:audio/webm;base64,")).toBe(false);
    expect(isPlayableDataUrl("data:audio/mp3,QUJD")).toBe(false);
    expect(isPlayableDataUrl("data:audio/mp3;base64,QUJ=")).toBe(true); // valid single padding
  });

  it("rejects non-strings", () => {
    expect(isPlayableDataUrl(undefined)).toBe(false);
    expect(isPlayableDataUrl(42)).toBe(false);
    expect(isPlayableDataUrl(null)).toBe(false);
    expect(isPlayableDataUrl({})).toBe(false);
  });
});

describe("mimeExtension", () => {
  it("maps known mimes", () => {
    expect(mimeExtension("audio/webm")).toBe("webm");
    expect(mimeExtension("audio/webm;codecs=opus")).toBe("webm");
    expect(mimeExtension("audio/mp4")).toBe("m4a");
    expect(mimeExtension("audio/mpeg")).toBe("mp3");
    expect(mimeExtension("audio/wav")).toBe("wav");
  });

  it("treats missing or empty mime as unknown (bin)", () => {
    expect(mimeExtension("application/octet-stream")).toBe("bin");
    expect(mimeExtension()).toBe("bin");
    expect(mimeExtension("")).toBe("bin");
    expect(mimeExtension("   ")).toBe("bin");
  });
});

describe("blobToDataUrl", () => {
  it("reads a blob into a data uri", async () => {
    const blob = new Blob([new Uint8Array([1, 2, 3])], { type: "audio/webm" });
    const url = await blobToDataUrl(blob);
    expect(url.startsWith("data:audio/webm;base64,")).toBe(true);
    expect(base64ToUint8Array(url)).toEqual(new Uint8Array([1, 2, 3]));
  });
});
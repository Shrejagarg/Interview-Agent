import { describe, expect, it } from "vitest";
import fc from "fast-check";
import {
  base64ToUint8Array,
  buildWav,
  isPlayableDataUrl,
  makeSilenceDataUri,
  mimeExtension,
  toAudioDataUri,
  uint8ToBase64,
} from "./audio";

const MAGIC = {
  riff: [0x52, 0x49, 0x46, 0x46], // RIFF
  wave: [0x57, 0x41, 0x56, 0x45], // WAVE
  fmt: [0x66, 0x6d, 0x74, 0x20],  // "fmt "
  data: [0x64, 0x61, 0x74, 0x61], // "data"
};

describe("base64 round-trip (property)", () => {
  it("uint8ToBase64 -> base64ToUint8Array is identity", () => {
    fc.assert(
      fc.property(fc.uint8Array({ minLength: 0, maxLength: 500 }), (bytes) => {
        expect(base64ToUint8Array(uint8ToBase64(bytes))).toEqual(bytes);
      })
    );
  });

  it("large payloads survive the chunked encoder", () => {
    fc.assert(
      fc.property(fc.uint8Array({ minLength: 0x8000, maxLength: 0x800f }), (bytes) => {
        expect(base64ToUint8Array(uint8ToBase64(bytes))).toEqual(bytes);
      }),
      { numRuns: 20 }
    );
  }, 30000);

  it("output alphabet only ever contains base64 chars", () => {
    fc.assert(
      fc.property(fc.uint8Array({ minLength: 0, maxLength: 300 }), (bytes) => {
        expect(uint8ToBase64(bytes)).toMatch(/^[a-z0-9+/]*={0,2}$/i);
      })
    );
  });
});

describe("buildWav (property)", () => {
  it("emits a spec-compliant header for arbitrary inputs", () => {
    fc.assert(
      fc.property(
        fc.int16Array({ minLength: 0, maxLength: 2000 }),
        fc.integer({ min: 8000, max: 48000 }),
        fc.integer({ min: 1, max: 8 }),
        (samples, sampleRate, channels) => {
          const wav = buildWav(samples, sampleRate, channels);
          const view = new DataView(wav.buffer);
          const dataSize = samples.length * 2;

          expect(wav.byteLength).toBe(44 + dataSize);
          expect(Array.from(wav.slice(0, 4))).toEqual(MAGIC.riff);
          expect(view.getUint32(4, true)).toBe(36 + dataSize);
          expect(Array.from(wav.slice(8, 12))).toEqual(MAGIC.wave);
          expect(Array.from(wav.slice(12, 16))).toEqual(MAGIC.fmt);
          expect(view.getUint16(20, true)).toBe(1); // PCM
          expect(view.getUint16(22, true)).toBe(channels);
          expect(view.getUint32(24, true)).toBe(sampleRate);
          expect(view.getUint32(28, true)).toBe(sampleRate * channels * 2);
          expect(view.getUint16(32, true)).toBe(channels * 2);
          expect(view.getUint16(34, true)).toBe(16); // bits per sample
          expect(Array.from(wav.slice(36, 40))).toEqual(MAGIC.data);
          expect(view.getUint32(40, true)).toBe(dataSize);

          // Sample payload is a byte-identical copy of the input
          const payload = new Uint8Array(samples.buffer, samples.byteOffset, dataSize);
          expect(new Uint8Array(wav.buffer, 44, dataSize)).toEqual(payload);
        }
      )
    );
  });
});

describe("makeSilenceDataUri (property)", () => {
  it("always yields a playable, structurally-sound silence clip", () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 5, noNaN: true, noInteger: true }),
        fc.integer({ min: 8000, max: 48000 }),
        fc.integer({ min: 1, max: 8 }),
        (duration, sampleRate, channels) => {
          const uri = makeSilenceDataUri(duration, sampleRate, channels);
          expect(isPlayableDataUrl(uri)).toBe(true);

          const bytes = base64ToUint8Array(uri);
          const view = new DataView(bytes.buffer);
          const sampleCount = Math.floor(sampleRate * duration) * channels;
          expect(bytes.byteLength).toBe(44 + sampleCount * 2);
          expect(Array.from(bytes.slice(0, 4))).toEqual(MAGIC.riff);
          expect(view.getUint16(22, true)).toBe(channels);
          expect(view.getUint32(24, true)).toBe(sampleRate);
          expect(view.getUint32(40, true)).toBe(sampleCount * 2);

          // All samples are true silence (zero)
          const samples = new Uint8Array(bytes.buffer, 44, sampleCount * 2);
          expect(samples.every((b) => b === 0)).toBe(true);
        }
      )
    );
  });

  it("supports whole-second durations (tens of thousands of samples)", () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 10 }), (seconds) => {
        const bytes = base64ToUint8Array(makeSilenceDataUri(seconds, 8000, 1));
        expect(bytes.byteLength).toBe(44 + seconds * 8000 * 2);
      })
    );
  });
});

describe("toAudioDataUri (property)", () => {
  const base64Payload = fc
    .array(
      fc.constantFrom(
        ...Array.from("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
      ),
      {
        minLength: 1,
        maxLength: 120,
      }
    )
    .map((chars) => chars.join(""));

  it("is idempotent for arbitrary payloads", () => {
    fc.assert(
      fc.property(base64Payload, fc.constantFrom("audio/mp3", "audio/wav", "audio/webm"), (payload, mime) => {
        const once = toAudioDataUri(payload, mime);
        expect(toAudioDataUri(once)).toBe(once);
      })
    );
  });

  it("always emits a data uri with the requested mime", () => {
    fc.assert(
      fc.property(
        base64Payload,
        fc.constantFrom("audio/mp3", "audio/wav", "audio/webm", "audio/mpeg"),
        (payload, mime) => {
          const uri = toAudioDataUri(payload, mime);
          expect(uri.startsWith(`data:${mime};base64,`)).toBe(true);
          expect(uri.slice(`data:${mime};base64,`.length)).toBe(payload);
        }
      )
    );
  });
});

describe("mimeExtension (property)", () => {
  it("is case-insensitive and ignores parameters when mapping", () => {
    fc.assert(
      fc.property(
        fc.constantFrom("Audio/WebM", "audio/ogg", "audio/wav", "audio/mpeg", "audio/flac"),
        fc.constantFrom("", ";codecs=opus", ";rate=16000", ";channels=2"),
        (base, params) => {
          const ext = mimeExtension(`${base}${params}`);
          expect(["webm", "ogg", "wav", "mp3", "flac"]).toContain(ext);
        }
      )
    );
  });

  it("maps any unknown mime to bin", () => {
    fc.assert(
      fc.property(
        fc.stringMatching(/^[a-z]+\/[a-z0-9.+-]+$/),
        fc.constantFrom("application/octet-stream", "text/plain", "video/mp4"),
        (_, mime) => {
          const ext = mimeExtension(mime);
          expect(["bin", "webm", "m4a", "mp3", "wav", "ogg", "flac"]).toContain(ext);
        }
      )
    );
  });
});
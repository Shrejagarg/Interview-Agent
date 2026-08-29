const MIME_TO_EXT: Record<string, string> = {
  "audio/webm": "webm",
  "audio/mp4": "m4a",
  "audio/x-m4a": "m4a",
  "audio/mpeg": "mp3",
  "audio/mp3": "mp3",
  "audio/wav": "wav",
  "audio/wave": "wav",
  "audio/ogg": "ogg",
  "audio/flac": "flac",
};

const DEFAULT_MIME_VOICE = "audio/webm";

export function mimeExtension(mime?: string): string {
  if (typeof mime !== "string" || !mime.trim()) return "bin";
  const base = mime.split(";")[0]?.trim().toLowerCase() ?? "";
  return MIME_TO_EXT[base] ?? "bin";
}

export function isPlayableDataUrl(value: unknown): value is string {
  if (typeof value !== "string") return false;
  return /^data:audio\/[a-z0-9.+-]+;base64,[a-z0-9+/]+={0,2}$/i.test(value);
}

export function base64ToUint8Array(value: string): Uint8Array {
  const cleaned = value.includes(",") ? value.slice(value.indexOf(",") + 1) : value;
  const sanitized = cleaned.replace(/\s+/g, "");
  if (sanitized === "") return new Uint8Array(0);
  if (!/^[a-z0-9+/]*={0,2}$/i.test(sanitized)) {
    throw new Error("Invalid base64 payload");
  }
  const binary = atob(sanitized);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) out[i] = binary.charCodeAt(i);
  return out;
}

export function uint8ToBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...Array.from(bytes.subarray(i, i + chunk)));
  }
  return btoa(binary);
}

export function buildWav(
  samples: Int16Array,
  sampleRate: number,
  channels = 1
): Uint8Array {
  if (!Number.isInteger(sampleRate) || sampleRate <= 0) {
    throw new RangeError(`sampleRate must be a positive integer, got ${sampleRate}`);
  }
  if (!Number.isInteger(channels) || channels < 1) {
    throw new RangeError(`channels must be a positive integer, got ${channels}`);
  }
  const bytesPerSample = 2;
  const dataSize = samples.byteLength;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i += 1) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * channels * bytesPerSample, true);
  view.setUint16(32, channels * bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, dataSize, true);

  if (dataSize > 0) {
    new Uint8Array(buffer, 44).set(
      new Uint8Array(samples.buffer, samples.byteOffset, dataSize)
    );
  }
  return new Uint8Array(buffer);
}

const MAX_SILENCE_SECONDS = 60;
const MIN_SAMPLE_RATE = 8000;
const MAX_SAMPLE_RATE = 96000;

export function makeSilenceDataUri(
  durationSeconds: number,
  sampleRate = MIN_SAMPLE_RATE,
  channels = 1
): string {
  if (typeof durationSeconds !== "number" || !Number.isFinite(durationSeconds)) {
    throw new RangeError(`durationSeconds must be finite, got ${durationSeconds}`);
  }
  if (durationSeconds < 0) {
    throw new RangeError(`durationSeconds cannot be negative, got ${durationSeconds}`);
  }
  if (durationSeconds > MAX_SILENCE_SECONDS) {
    throw new RangeError(
      `durationSeconds exceeds max of ${MAX_SILENCE_SECONDS}s, got ${durationSeconds}`
    );
  }
  if (!Number.isInteger(sampleRate) || sampleRate < MIN_SAMPLE_RATE || sampleRate > MAX_SAMPLE_RATE) {
    throw new RangeError(
      `sampleRate outside [${MIN_SAMPLE_RATE}, ${MAX_SAMPLE_RATE}], got ${sampleRate}`
    );
  }
  if (!Number.isInteger(channels) || channels < 1 || channels > 8) {
    throw new RangeError(`channels outside [1, 8], got ${channels}`);
  }

  const totalSamples = Math.floor(sampleRate * durationSeconds) * channels;
  const samples = new Int16Array(totalSamples);
  const wav = buildWav(samples, sampleRate, channels);
  return `data:audio/wav;base64,${uint8ToBase64(wav)}`;
}

export function toAudioDataUri(audioBase64: string, mime = "audio/mp3"): string {
  if (typeof audioBase64 !== "string" || !audioBase64.trim()) {
    throw new Error("Empty audio payload");
  }
  const value = audioBase64.trim();
  if (value.startsWith("data:")) return value;
  return `data:${mime};base64,${value}`;
}

export function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    if (typeof FileReader === "undefined") {
      reject(new Error("FileReader is not available in this environment"));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Failed to read blob"));
    reader.readAsDataURL(blob);
  });
}

export { DEFAULT_MIME_VOICE };
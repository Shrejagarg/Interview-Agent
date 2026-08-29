import { vi } from "vitest";

export class MockUtterance {
  text: string;
  lang = "";
  pitch = 1;
  rate = 1;
  volume = 1;
  voice: unknown = null;
  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onboundary: unknown = null;
  onpause: unknown = null;
  onresume: unknown = null;
  onmark: unknown = null;

  static instances: MockUtterance[] = [];

  constructor(text = "") {
    this.text = text;
    MockUtterance.instances.push(this);
  }

  static last(): MockUtterance | undefined {
    return MockUtterance.instances[MockUtterance.instances.length - 1];
  }

  static reset() {
    MockUtterance.instances = [];
  }
}

export class MockSpeechSynthesis {
  speaking = false;
  pending = false;
  paused = false;
  onvoiceschanged: (() => void) | null = null;

  static instances: MockSpeechSynthesis[] = [];

  constructor() {
    MockSpeechSynthesis.instances.push(this);
  }

  speak = vi.fn((utterance: MockUtterance) => {
    this.pending = false;
    this.speaking = true;
    utterance.onstart?.();
  });

  cancel = vi.fn(() => {
    const wasSpeaking = this.speaking;
    this.speaking = false;
    this.pending = false;
    const last = MockUtterance.last();
    if (wasSpeaking && last && last.onerror) {
      last.onerror({ error: "canceled" });
    }
  });

  pause = vi.fn(() => {
    this.paused = true;
    this.speaking = false;
  });

  resume = vi.fn(() => {
    this.paused = false;
    this.speaking = true;
  });

  getVoices = vi.fn(() => []);

  static last(): MockSpeechSynthesis | undefined {
    return MockSpeechSynthesis.instances[MockSpeechSynthesis.instances.length - 1];
  }

  static reset() {
    MockSpeechSynthesis.instances = [];
    MockUtterance.reset();
  }
}

export interface RecognitionResultEvent {
  resultIndex?: number;
  results: Record<number, { isFinal: boolean } & Record<number, { transcript: string }>> & {
    length: number;
  };
}

export class MockSpeechRecognition {
  lang = "";
  continuous = false;
  interimResults = true;
  maxAlternatives = 1;
  onstart: (() => void) | null = null;
  onresult: ((event: RecognitionResultEvent) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;

  static supported = true;
  static instances: MockSpeechRecognition[] = [];

  private running = false;

  constructor() {
    MockSpeechRecognition.instances.push(this);
  }

  start = vi.fn(() => {
    this.running = true;
    this.onstart?.();
  });

  stop = vi.fn(() => {
    this.running = false;
  });

  abort = vi.fn(() => {
    this.running = false;
  });

  get isRunning() {
    return this.running;
  }

  private resultsAccum: Array<{ transcript: string; isFinal: boolean }> = [];

  /** Emits an incremental recognition result. Empty transcript is ignored. */
  emitResult(transcript: string, isFinal = false) {
    if (!transcript.trim()) {
      this.onresult?.({ resultIndex: this.nextResultIndex, results: { length: this.resultsAccum.length } });
      return;
    }
    const idx = this.resultsAccum.length;
    this.resultsAccum.push({ transcript, isFinal });
    const results: { length: number } & Record<number, unknown> = {
      length: idx + 1,
    };
    this.resultsAccum.forEach((entry, j) => {
      results[j] = {
        0: { transcript: entry.transcript },
        isFinal: entry.isFinal,
        length: 1,
      };
    });
    this.nextResultIndex += 1;
    this.onresult?.({
      resultIndex: idx,
      results: results as unknown as RecognitionResultEvent["results"],
    });
  }

  emitError(error: string) {
    this.onerror?.({ error });
  }

  emitEnd() {
    this.running = false;
    this.onend?.();
  }

  private nextResultIndex = 0;

  static last(): MockSpeechRecognition | undefined {
    return MockSpeechRecognition.instances[MockSpeechRecognition.instances.length - 1];
  }

  static reset() {
    MockSpeechRecognition.instances = [];
    MockSpeechRecognition.supported = true;
  }
}

export function installFakeSpeech() {
  resetFakeSpeech();
  const synth = new MockSpeechSynthesis();
  Object.defineProperty(window, "SpeechRecognition", {
    configurable: true,
    writable: true,
    value: MockSpeechRecognition,
  });
  Object.defineProperty(window, "webkitSpeechRecognition", {
    configurable: true,
    writable: true,
    value: MockSpeechRecognition,
  });
  Object.defineProperty(window, "SpeechSynthesisUtterance", {
    configurable: true,
    writable: true,
    value: MockUtterance,
  });
  Object.defineProperty(window, "speechSynthesis", {
    configurable: true,
    writable: true,
    value: synth,
  });
  return { synth };
}

export function uninstallFakeSpeech() {
  Object.defineProperty(window, "SpeechRecognition", {
    configurable: true,
    writable: true,
    value: undefined,
  });
  Object.defineProperty(window, "webkitSpeechRecognition", {
    configurable: true,
    writable: true,
    value: undefined,
  });
  Object.defineProperty(window, "SpeechSynthesisUtterance", {
    configurable: true,
    writable: true,
    value: undefined,
  });
  Object.defineProperty(window, "speechSynthesis", {
    configurable: true,
    writable: true,
    value: undefined,
  });
}

export function resetFakeSpeech() {
  MockSpeechRecognition.reset();
  MockSpeechSynthesis.reset();
}
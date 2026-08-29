import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { base64ToUint8Array, isPlayableDataUrl } from "./audio";
import * as api from "./api";

describe("Voice API (simulated mode)", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_SIMULATED_VOICE = "1";
  });

  afterAll(() => {
    delete process.env.NEXT_PUBLIC_SIMULATED_VOICE;
  });

  it("audio-start returns a deterministic first question with playable audio", async () => {
    const turn = await api.audioInterviewStart("sess_1");
    expect(turn.question).toBeTruthy();
    expect(turn.question_index).toBe(1);
    expect(turn.question_total).toBe(3);
    expect(isPlayableDataUrl(turn.audio_base64)).toBe(true);
    // 0.6s of 8kHz mono 16-bit -> 44 + 9600 bytes
    expect(base64ToUint8Array(turn.audio_base64).byteLength).toBe(9644);
  });

  it("resets the question cursor on every start", async () => {
    const first = await api.audioInterviewStart("sess_1");
    await api.submitAudioAnswer("sess_1", new Blob(["x"], { type: "audio/webm" }));
    const again = await api.audioInterviewStart("sess_1");
    expect(first.question).toBe(again.question);
  });

  it("audio-answer walks the question bank and yields deterministic scores", async () => {
    await api.audioInterviewStart("sess_1");
    const audio = new Blob(["fake-audio"], { type: "audio/webm" });
    const answers = await Promise.all([
      api.submitAudioAnswer("sess_1", audio),
      api.submitAudioAnswer("sess_1", audio),
      api.submitAudioAnswer("sess_1", audio),
    ]);
    expect(answers[0].evaluation.overall_score).toBe(5.8);
    expect(answers[1].evaluation.overall_score).toBe(6.4);
    expect(answers[2].evaluation.overall_score).toBe(7.1);
    expect(answers.map((a) => a.next_question)).toEqual([
      expect.any(String),
      expect.any(String),
      null,
    ]);
    expect(answers[0].evaluation.strengths.length).toBeGreaterThan(0);
    expect(answers[2].evaluation.weaknesses.length).toBeGreaterThan(0);
    expect(isPlayableDataUrl(answers[0].audio_base64)).toBe(true);
  });

  it("accepts the recorded blob without inspecting its contents", async () => {
    await api.audioInterviewStart("sess_1");
    const empty = new Blob([], { type: "audio/webm" });
    const res = await api.submitAudioAnswer("sess_1", empty);
    expect(res.next_question).toBeTruthy();
  });
});

describe("Voice API (real fetch path)", () => {
  const captured = {
    startBody: "",
    authHeader: null as string | null,
    rawBody: "" as string,
  };

  const server = setupServer(
    http.post("http://localhost:8000/api/interviews/:id/audio-start", async ({ request }) => {
      captured.authHeader = request.headers.get("authorization");
      return HttpResponse.json({
        question: "Are you comfortable with live debugging?",
        audio_base64: "U01MPS0=",
        question_index: 1,
        question_total: 1,
      });
    }),
    http.post(
      "http://localhost:8000/api/interviews/:id/audio-answer",
      async ({ request }) => {
        captured.authHeader = request.headers.get("authorization");
        captured.rawBody = new TextDecoder().decode(await request.arrayBuffer());
        return HttpResponse.json({
          evaluation: { overall_score: 9.0, strengths: [], weaknesses: [] },
          next_question: null,
          audio_base64: "U01MPS0=",
        });
      }
    )
  );

  beforeAll(() => {
    process.env.NEXT_PUBLIC_SIMULATED_VOICE = "0";
    server.listen();
  });

  afterAll(() => {
    delete process.env.NEXT_PUBLIC_SIMULATED_VOICE;
    server.close();
  });

  beforeEach(() => {
    captured.startBody = "";
    captured.authHeader = null;
    captured.rawBody = "";
    localStorage.setItem("auth_token", "tok_abc");
    vi.clearAllMocks();
  });

  it("POSTs to audio-start with the bearer token", async () => {
    const res = await api.audioInterviewStart("sess_2");
    expect(res.question).toBe("Are you comfortable with live debugging?");
    expect(captured.authHeader).toBe("Bearer tok_abc");
  });

  it("builds the multipart form with the intended filename and mime", () => {
    const { formData, filename } = api.buildAudioAnswerForm(
      new Blob([new Uint8Array([1, 2, 3])], { type: "audio/webm;codecs=opus" })
    );
    expect(filename).toBe("answer.webm");
    const file = formData.get("audio") as File;
    expect(file.name).toBe("answer.webm");
    expect(file.type).toBe("audio/webm;codecs=opus");
    expect(file.size).toBe(3);
  });

  it("falls back to the .bin extension for unknown mime types in the form", () => {
    const { filename } = api.buildAudioAnswerForm(
      new Blob([new Uint8Array([1])], { type: "application/x-foo" })
    );
    expect(filename).toBe("answer.bin");
  });

  it("uploads the audio in a multipart body under part `audio`", async () => {
    const recorded = new Blob([new Uint8Array([9, 8, 7])], { type: "audio/webm" });
    const res = await api.submitAudioAnswer("sess_2", recorded);

    expect(captured.authHeader).toBe("Bearer tok_abc");
    expect(captured.rawBody).toMatch(/name="audio"/);
    expect(captured.rawBody).toMatch(/Content-Type: audio\/webm/i);
    expect(captured.rawBody.length).toBeGreaterThan(128);
    expect(res.evaluation.overall_score).toBe(9.0);
    expect(res.next_question).toBeNull();
  });

  it("surfaces backend `detail` errors", async () => {
    server.use(
      http.post(
        "http://localhost:8000/api/interviews/:id/audio-answer",
        () => HttpResponse.json({ detail: "No audio received" }, { status: 422 })
      )
    );
    await expect(
      api.submitAudioAnswer("sess_2", new Blob([], { type: "audio/webm" }))
    ).rejects.toThrow("No audio received");
  });

  it("throws on network failure instead of silently succeeding", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("boom"));
    await expect(
      api.submitAudioAnswer("sess_2", new Blob(["x"], { type: "audio/webm" }))
    ).rejects.toThrow("boom");
  });
});
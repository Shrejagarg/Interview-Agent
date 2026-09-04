import { test, expect, Page } from "@playwright/test";

async function speakAnswer(page: Page) {
  const idleMic = page.getByRole("button", {
    name: "Hold to record your answer",
  });
  const recordingMic = page.getByRole("button", {
    name: "Stop recording and send your answer",
  });
  await expect(idleMic).toBeVisible();
  await idleMic.hover();
  await page.mouse.down();
  // MediaRecorder captures a real (browser fake-mic) stream. Keep the button
  // held long enough to yield a non-empty audio blob before releasing.
  await expect(recordingMic).toBeVisible();
  await page.waitForTimeout(500);
  await page.mouse.up();
  await expect(idleMic).toBeVisible();
}

test("candidate registers and completes a full voice interview", async ({
  page,
}) => {
  const email = `e2e-${Date.now()}@test.io`;

  await page.goto("/register");
  await page.getByPlaceholder("Jane Doe").fill("E2E Voice Candidate");
  await page.getByPlaceholder("you@example.com").fill(email);
  await page.getByPlaceholder("Min 6 characters").fill("Passw0rd123!");
  await page.getByRole("button", { name: "Create Account" }).click();

  // / redirects candidates to /interview once the session is set.
  await page.waitForURL("**/interview");
  await page.selectOption("#interview-domain", "software_engineering");
  await page.getByLabel("Questions").fill("2");
  await page.getByRole("button", { name: "Start Mock Interview" }).click();

  await page.waitForURL(/\/interview\/[^/]+\/[^/]+/);

  // VoiceInterview loads the first question via getQuestion.
  const questionSection = page.locator(
    'section[aria-label="Current question"]'
  );
  await expect(questionSection.getByText("Interviewer")).toBeVisible();

  // Answer each question (and follow-up) with the (fake) mic; the audio
  // answer is transcribed server-side and advances the session. Keep
  // recording until the interview reports complete.
  for (let i = 0; i < 8; i++) {
    await speakAnswer(page);
    // A score is shown per-turn in the status card ("7.1") and, on the final
    // answer, in the "done" summary ("7.1/10", which drops the status card).
    // Wait for either, then stop once the interview reports complete.
    await expect(page.getByText(/\d+\.\d/).first()).toBeVisible({
      timeout: 15_000,
    });
    if (await page.getByText("Interview complete").isVisible().catch(() => false)) {
      break;
    }
  }

  await expect(page.getByText("Interview complete")).toBeVisible({
    timeout: 15_000,
  });

  await page.getByRole("link", { name: "View your report" }).click();
  await expect(
    page.getByRole("heading", { name: "Interview Report" })
  ).toBeVisible();
  await expect(
    page.getByText(/questions answered/).first()
  ).toBeVisible();
});

test("demo company can sign in and see the dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("you@example.com").fill("company@test.io");
  await page.getByPlaceholder("••••••••").fill("Passw0rd123!");
  await page.getByRole("button", { name: "Sign In" }).click();

  await page.waitForURL("**/dashboard");
  await expect(page.getByRole("heading", { name: /Dashboard/i })).toBeVisible();
});
import { defineConfig } from "@playwright/test";
import path from "path";

const webDir = __dirname;
const repoRoot = path.resolve(webDir, "..", "..");
const venvPython =
  process.platform === "win32"
    ? path.join(repoRoot, "venv", "Scripts", "python.exe")
    : path.join(repoRoot, "venv", "bin", "python");
const e2eServer = path.join(repoRoot, "backend", "scripts", "e2e_server.py");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        // Fake device feeds getUserMedia/MediaRecorder with synthetic audio
        // and auto-grants permission, so the record path needs no real mic.
        launchOptions: {
          args: [
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
          ],
        },
      },
    },
  ],
  webServer: [
    {
      command: `"${venvPython}" "${e2eServer}"`,
      cwd: repoRoot,
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run start",
      cwd: webDir,
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
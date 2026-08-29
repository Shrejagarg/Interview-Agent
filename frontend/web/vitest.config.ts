/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    css: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      // Phase 5 scope: the voice-interview feature and its pure audio helpers.
      // `api.ts` and `auth.tsx` are pre-existing shared modules; the voice API
      // surface is covered by MSW integration tests in src/lib/api.test.ts.
      include: [
        "src/features/voice-interview/**/*.{ts,tsx}",
        "src/lib/audio.ts",
      ],
      exclude: [
        "src/**/*.{test,spec}.{ts,tsx}",
        "src/test/**",
        "src/**/*.d.ts",
        "src/features/**/index.ts",
      ],
      thresholds: { branches: 80, functions: 80, lines: 80, statements: 80 },
    },
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
});
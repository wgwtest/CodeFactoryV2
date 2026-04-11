import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: {
    include: ["src/test/**/*.test.ts?(x)"],
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts"
  }
});

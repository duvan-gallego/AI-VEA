import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiUrl = env.VITE_API_URL ?? "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": apiUrl,
      },
    },
  };
});

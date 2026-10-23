import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development, anything under /api goes to the Python server on port 8000
const proxy = { "/api": "http://localhost:8000" };

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
});

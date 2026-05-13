import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        // Ensure SSE streams are not buffered
        configure: (proxy) => {
          proxy.on("proxyReq", (proxyReq, req) => {
            if (req.url?.includes("/chat/stream") || req.url?.includes("/regenerate")) {
              // Disable proxy request buffering
              proxyReq.setHeader("Accept", "text/event-stream");
            }
          });
        },
      },
    },
  },
});

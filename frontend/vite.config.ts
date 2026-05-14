import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

type ProxyEventEmitter = {
  on: (
    event: "proxyReq",
    listener: (
      proxyReq: { setHeader: (name: string, value: string) => void },
      req: { url?: string },
    ) => void,
  ) => void;
};

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
          (proxy as unknown as ProxyEventEmitter).on("proxyReq", (proxyReq, req) => {
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

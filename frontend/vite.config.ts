import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// @ts-ignore
import fs from "node:fs";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    https: {
      key:  fs.readFileSync("certs/localhost-key.pem"),
      cert: fs.readFileSync("certs/localhost-cert.pem"),
    },
    host: "localhost",
    port: 5173,
    strictPort: true,
  },
})

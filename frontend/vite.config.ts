import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

const backend = "http://localhost:8000"
// Full-page Django surfaces (auth, MFA, OAuth, admin, downloads) plus the API.
const proxiedPrefixes = [
  "/api",
  "/accounts",
  "/mfa",
  "/admin",
  "/static",
  "/health",
  "/exports",
  "/integrations",
]

export default defineConfig(({ command }) => ({
  // Production assets are served by Django/WhiteNoise under /static/.
  base: command === "build" ? "/static/" : "/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    proxy: Object.fromEntries(proxiedPrefixes.map((prefix) => [prefix, backend])),
  },
}))

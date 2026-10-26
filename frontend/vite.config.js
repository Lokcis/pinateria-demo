import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      injectRegister: "auto",
      // Solo se precachea el "app shell" (JS/CSS/fuentes/iconos): asi la aplicacion
      // abre aunque no haya internet. Las llamadas a la API nunca se sirven desde
      // cache a proposito (stock y precios son datos en vivo). El modo sin conexion
      // (Fase 9) no usa el Service Worker para los datos: el catalogo y la cola de
      // ventas pendientes viven en IndexedDB (src/offline/), ver docs/11.
      workbox: {
        globPatterns: ["**/*.{js,css,html,woff2,png,svg}"],
        navigateFallbackDenylist: [/^\/api\//],
      },
      manifest: {
        name: "Piñatería Demo",
        short_name: "Piñatería Demo",
        description: "Punto de venta e inventario de Piñatería Demo.",
        lang: "es",
        theme_color: "#d6245f",
        background_color: "#fbf6ee",
        display: "standalone",
        start_url: "/",
        scope: "/",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          {
            src: "maskable-icon-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/setup-tests.js",
    globals: false,
    css: false,
  },
});

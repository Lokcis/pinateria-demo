import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/figtree";
import { App } from "./app";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/schibsted-grotesk";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-mono/600.css";
import "./styles/base.css";
import { APP_NAME } from "./config";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <p className="p-4 text-display-md text-ink">{APP_NAME}</p>
  </StrictMode>,
);

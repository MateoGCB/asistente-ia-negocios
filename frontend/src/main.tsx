import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { APP_NAME } from "./config";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <p>{APP_NAME}</p>
  </StrictMode>,
);

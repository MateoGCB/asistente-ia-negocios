// Provisional product name: change it here and it changes everywhere.
export const APP_NAME = "Comanda";

// Backend base URL. Set VITE_API_URL in frontend/.env (never put secrets there: it ends up in the bundle).
export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

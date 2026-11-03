import { useEffect, useState, type ReactNode } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { clearSession, getToken } from "../api/session";
import { useSessionToken } from "./session";

export const HOME_PATH = "/pedidos";

// Owner panel: without a token, go to /login (and come back here after logging in).
// It reacts to session changes: a 401 anywhere in the panel lands here and redirects.
export function RequireAuth({ children }: { children: ReactNode }) {
  const token = useSessionToken();
  const location = useLocation();
  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return children;
}

// /login and /registro: if a session was ALREADY open when arriving, go straight to the panel.
// It looks only at arrival on purpose: when the user logs in here, the page itself decides where
// to go next (back to "from", or to /negocios after registering) instead of racing with this redirect.
export function GuestOnly({ children }: { children: ReactNode }) {
  const [hadSessionOnArrival] = useState(() => getToken() !== null);
  if (hadSessionOnArrival) return <Navigate to={HOME_PATH} replace />;
  return children;
}

// /salir: an explicit logout. It lives OUTSIDE the panel, so RequireAuth is no longer mounted when
// the session is cleared and does not remember the page (the next login may be someone else).
export function Logout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  useEffect(() => {
    clearSession();
    queryClient.clear(); // nothing of this owner stays in memory
    navigate("/login", { replace: true });
  }, [queryClient, navigate]);
  return null;
}

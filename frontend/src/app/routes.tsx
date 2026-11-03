import { Navigate, Outlet, type RouteObject } from "react-router";
import { AppShell } from "./AppShell";
import { GuestOnly, HOME_PATH, Logout, RequireAuth } from "./guards";
import { NotFoundPage } from "./NotFoundPage";
import { RouteLoading } from "./RouteLoading";

// Each screen is downloaded only when it is visited (code splitting): a customer opening the
// public page from a phone does not download the owner panel.
const page = (load: () => Promise<{ default: React.ComponentType }>) => async () => ({ Component: (await load()).default });

// Also used by the tests with createMemoryRouter
export const routes: RouteObject[] = [
  {
    hydrateFallbackElement: <RouteLoading />,
    element: <GuestOnly><Outlet /></GuestOnly>,
    children: [
      { path: "/login", lazy: page(() => import("../features/auth/LoginPage").then((m) => ({ default: m.LoginPage }))) },
      { path: "/registro", lazy: page(() => import("../features/auth/RegisterPage").then((m) => ({ default: m.RegisterPage }))) },
    ],
  },
  {
    // Owner panel: every screen needs a session and uses AppShell
    hydrateFallbackElement: <RouteLoading />,
    element: <RequireAuth><AppShell /></RequireAuth>,
    children: [
      { index: true, element: <Navigate to={HOME_PATH} replace /> },
    ],
  },
  { path: "/salir", element: <Logout /> },
  { path: "*", element: <NotFoundPage /> },
];

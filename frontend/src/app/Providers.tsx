import { useEffect, useState, type ReactNode } from "react";
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { subscribeSession, getToken } from "../api/session";
import { ToastProvider } from "../components/Toast";
import { createQueryClient } from "./queryClient";

// Everything the screens need around them. MotionConfig reducedMotion="user" turns every
// Motion animation off when the system asks for reduced motion.
export function Providers({ children, queryClient }: { children: ReactNode; queryClient?: QueryClient }) {
  const [client] = useState(() => queryClient ?? createQueryClient());

  // When the session ends (logout or expired token), no data of that owner stays cached
  useEffect(() => subscribeSession(() => {
    if (!getToken()) client.clear();
  }), [client]);

  return (
    <QueryClientProvider client={client}>
      <MotionConfig reducedMotion="user">
        <ToastProvider>{children}</ToastProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}

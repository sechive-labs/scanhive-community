import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";

import { AuthProvider } from "../auth/AuthContext";
import { ScanHiveThemeProvider } from "../theme/ScanHiveThemeProvider";

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

export function TestProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <ScanHiveThemeProvider>
          <AuthProvider>{children}</AuthProvider>
        </ScanHiveThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

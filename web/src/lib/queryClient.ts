import { QueryClient } from "@tanstack/react-query";

// Sim state is immutable until the next mutation (sim-week, fork, etc.),
// so we can cache aggressively and invalidate explicitly after actions.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

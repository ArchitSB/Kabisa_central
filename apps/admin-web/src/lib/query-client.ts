import { MutationCache, QueryClient } from "@tanstack/react-query";
import axios from "axios";
import { isTransientReadError } from "@/lib/http-policy";

export const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onSuccess: () => {
      // Successful edits should update the overview without waiting for its poll.
      void queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Transport owns the single transient GET retry. Do not multiply attempts.
      retry: (count, error) =>
        !isTransientReadError(error) &&
        !(axios.isAxiosError(error) && [401, 403].includes(error.response?.status ?? 0)) &&
        count < 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});

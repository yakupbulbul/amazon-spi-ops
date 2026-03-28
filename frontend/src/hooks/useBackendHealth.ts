import { useEffect, useState } from "react";

import { getHealth } from "../lib/api";

type BackendHealthState = {
  status: "loading" | "healthy" | "error";
  message: string;
};

export function useBackendHealth(): BackendHealthState {
  const [state, setState] = useState<BackendHealthState>({
    status: "loading",
    message: "Checking backend",
  });

  useEffect(() => {
    const abortController = new AbortController();

    async function loadHealth() {
      try {
        const response = await getHealth(abortController.signal);
        setState({
          status: "healthy",
          message: response.status === "ok" ? "Backend healthy" : "Backend reported issues",
        });
      } catch (error) {
        if (abortController.signal.aborted) {
          return;
        }

        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Unable to reach backend",
        });
      }
    }

    void loadHealth();

    return () => {
      abortController.abort();
    };
  }, []);

  return state;
}


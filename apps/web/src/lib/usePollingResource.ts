import { useCallback, useEffect, useRef, useState } from "react";

type PollingResourceOptions<T> = {
  intervalMs: number;
  load: () => Promise<T>;
  onData: (data: T) => void;
  onError?: (error: unknown) => void;
};

export function usePollingResource<T>({ intervalMs, load, onData, onError }: PollingResourceOptions<T>) {
  const [loading, setLoading] = useState(true);
  const inFlightRef = useRef(false);
  const cancelledRef = useRef(false);

  const refresh = useCallback(
    async (options: { initial?: boolean } = {}) => {
      if (inFlightRef.current) {
        return;
      }
      inFlightRef.current = true;
      if (options.initial) {
        setLoading(true);
      }
      try {
        const data = await load();
        if (!cancelledRef.current) {
          onData(data);
        }
      } catch (error) {
        if (!cancelledRef.current) {
          onError?.(error);
        }
      } finally {
        inFlightRef.current = false;
        if (!cancelledRef.current) {
          setLoading(false);
        }
      }
    },
    [load, onData, onError],
  );

  useEffect(() => {
    cancelledRef.current = false;
    void refresh({ initial: true });

    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void refresh();
      }
    }, intervalMs);

    const refreshOnVisible = () => {
      if (document.visibilityState === "visible") {
        void refresh();
      }
    };

    document.addEventListener("visibilitychange", refreshOnVisible);
    window.addEventListener("focus", refreshOnVisible);

    return () => {
      cancelledRef.current = true;
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", refreshOnVisible);
      window.removeEventListener("focus", refreshOnVisible);
    };
  }, [intervalMs, refresh]);

  return { loading, refresh };
}

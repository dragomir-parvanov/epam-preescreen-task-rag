import { useCallback, useEffect, useRef, useState } from "react";
import { debounceLlm, fetchReadiness, isAllOk, type Readiness } from "./readiness";

/** How often `/ready` is polled while any check fails. */
export const POLL_INTERVAL_MS = 5_000;

export type ReadinessControls = {
  /** The latest readiness, with a fresh `llm` `unavailable` held back; `null` before the first. */
  readiness: Readiness | null;
  /** Check again now, e.g. after a Turn failed for an operational reason. */
  recheck: () => void;
};

/**
 * Polls `GET /api/ready`: on load, then every 5 s while any check fails, stopping once all pass,
 * so a healthy page makes no background requests. Paused while the tab is hidden, with a check
 * as soon as it's visible again.
 */
export function useReadiness(): ReadinessControls {
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const checkNow = useRef<() => void>(() => undefined);

  useEffect(() => {
    let previous: Readiness | null = null;
    let inFlight: AbortController | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const cancel = () => {
      clearTimeout(timer);
      inFlight?.abort();
      inFlight = null;
    };

    // Each check supersedes any pending one, so there's never more than one in flight.
    async function check() {
      cancel();
      const controller = new AbortController();
      inFlight = controller;
      let next: Readiness;
      try {
        next = await fetchReadiness(controller.signal);
      } catch {
        return; // Superseded, or the page went away.
      }
      if (controller.signal.aborted) return;
      inFlight = null;
      setReadiness(debounceLlm(next, previous));
      previous = next;
      if (!isAllOk(next) && !document.hidden) {
        timer = setTimeout(() => void check(), POLL_INTERVAL_MS);
      }
    }

    const onVisibilityChange = () => {
      if (document.hidden) cancel();
      else void check();
    };

    checkNow.current = () => void check();
    void check();
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      checkNow.current = () => undefined;
      cancel();
    };
  }, []);

  const recheck = useCallback(() => checkNow.current(), []);
  return { readiness, recheck };
}

import { useId, useState } from "react";
import type { BannerView, Tone } from "./readiness";

const TONE_CLASSES: Record<Tone, string> = {
  info: "border-blue-200 bg-blue-50 text-blue-950",
  warning: "border-amber-300 bg-amber-50 text-amber-950",
  error: "border-red-200 bg-red-50 text-red-950",
};

/**
 * The stack's current state, for the CSM: a headline and a subline saying whether to wait or get
 * help, then, collapsed, every failing check for whoever runs the assistant. Red is an alert;
 * blue and amber are a status.
 */
export function ReadinessBanner({ view }: { view: BannerView }) {
  const headlineId = useId();
  return (
    <div
      role={view.tone === "error" ? "alert" : "status"}
      aria-labelledby={headlineId}
      className={`border-b text-sm ${TONE_CLASSES[view.tone]}`}
    >
      <div className="mx-auto max-w-3xl space-y-0.5 px-4 py-2 sm:px-6">
        <p id={headlineId} className="font-semibold">
          {view.headline}
        </p>
        <p>{view.subline}</p>
        <details className="pt-1 text-xs">
          <summary className="cursor-pointer opacity-80 hover:opacity-100">
            Details for whoever runs this
          </summary>
          <ul className="mt-1 space-y-1">
            {view.problems.map((problem) => (
              <li key={problem.subject} className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
                <span>
                  <code className="font-mono">{problem.subject}</code> {problem.text}
                </span>
                {problem.command && <CopyableCommand command={problem.command} />}
              </li>
            ))}
          </ul>
        </details>
      </div>
    </div>
  );
}

function CopyableCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
    } catch {
      // No clipboard outside a secure context; the command stays selectable.
    }
  };
  return (
    <>
      {" "}
      Run: <code className="rounded bg-white/70 px-1 font-mono select-all">{command}</code>
      <button
        type="button"
        onClick={() => void copy()}
        className="rounded border border-current/30 px-1.5 py-0.5 hover:bg-white/60"
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </>
  );
}

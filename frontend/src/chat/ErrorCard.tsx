import type { components } from "../api/schema";

type ErrorBody = components["schemas"]["ErrorBody"];
type ErrorCode = components["schemas"]["ErrorCode"];

const COULDNT_FINISH = "The assistant couldn't finish this answer";
const NOT_SET_UP = "The assistant isn't set up correctly";
const GENERIC = "Something went wrong";

/** A short, CSM-facing title per error code. Typed over the generated union, so new codes must be added. */
const TITLES: Record<ErrorCode, string> = {
  llm_unavailable: COULDNT_FINISH,
  llm_timeout: COULDNT_FINISH,
  rewrite_failed: "This follow-up couldn't be understood",
  llm_auth_failed: NOT_SET_UP,
  llm_not_configured: NOT_SET_UP,
  index_not_ready: "The Knowledge Base is still loading",
  retrieval_unavailable: "The Knowledge Base can't be reached right now",
  validation_error: "This question couldn't be sent",
  not_found: GENERIC,
  method_not_allowed: GENERIC,
  internal_error: GENERIC,
};

/**
 * A failed Turn: what went wrong, the server's message, its code and request id (small and
 * selectable, for bug reports), and a way to ask again.
 */
export function ErrorCard({
  error,
  onAskAgain,
  disabled,
}: {
  error: ErrorBody;
  onAskAgain: () => void;
  disabled: boolean;
}) {
  return (
    <div
      role="alert"
      className="space-y-1 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900"
    >
      <p className="font-semibold">{TITLES[error.code]}</p>
      <p>{error.message}</p>
      {error.details && error.details.length > 0 && (
        <ul className="list-disc pl-5">
          {error.details.map((detail) => {
            const field = detail.loc.filter((part) => part !== "body").join(".");
            return (
              <li key={`${field}:${detail.msg}`}>
                {field ? `${field}: ` : ""}
                {detail.msg}
              </li>
            );
          })}
        </ul>
      )}
      <div className="flex items-center justify-between gap-2 pt-1">
        <p className="flex flex-wrap gap-x-3 font-mono text-xs text-red-500">
          <code className="select-all">{error.code}</code>
          {error.request_id && (
            <span>
              request id <code className="select-all">{error.request_id}</code>
            </span>
          )}
        </p>
        <button
          type="button"
          onClick={onAskAgain}
          disabled={disabled}
          className="rounded bg-red-700 px-3 py-1 text-xs font-medium text-white hover:bg-red-800 disabled:opacity-50"
        >
          Ask again
        </button>
      </div>
    </div>
  );
}

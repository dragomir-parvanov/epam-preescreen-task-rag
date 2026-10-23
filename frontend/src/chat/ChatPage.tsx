import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { bannerFor, blocksSending, isOperational } from "../readiness/readiness";
import { ReadinessBanner } from "../readiness/ReadinessBanner";
import { useReadiness } from "../readiness/useReadiness";
import type { OpenSection } from "./passages";
import { TurnView } from "./TurnView";
import { useConversation } from "./useConversation";

/** Golden Questions a reviewer can click through as a demo script. */
const SUGGESTED_QUESTIONS = [
  "What is the API rate limit for a Business client?",
  "Can a Business-tier client set up SCIM provisioning with Okta?",
  "Which header carries the webhook signature and what algorithm is used?",
  "A client still on v2 asks which SAML attribute carries the user's email.",
  "How much does the Enterprise tier cost per seat?",
];

const QUESTION_MAX_CHARS = 2_000;

/**
 * The chat page: a header with New conversation, one reading column of Turns, and the composer
 * pinned to the bottom, with the readiness banner under the header while the stack isn't ready.
 * `onOpenSection` is where Citation click-through opens an Article; while one is open, `covered`
 * makes everything but the banner inert.
 */
export function ChatPage({
  onOpenSection,
  covered = false,
}: {
  onOpenSection: OpenSection;
  covered?: boolean;
}) {
  const { readiness, recheck } = useReadiness();
  const banner = readiness && bannerFor(readiness);
  // A question would fail while the database or index is down; the CSM can still type one.
  const paused = blocksSending(readiness);
  const pausedReasonId = useId();
  const { turns, busy, ask, stop, reset } = useConversation({
    // The banner may have gone quiet since the stack last failed: see how it is now.
    onTurnError: (error) => {
      if (isOperational(error.code)) recheck();
    },
  });
  const [draft, setDraft] = useState("");
  const latestTurn = useRef<HTMLDivElement>(null);

  // Bring each new Turn into view as it starts.
  const turnCount = turns.length;
  useEffect(() => {
    if (turnCount > 0) latestTurn.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [turnCount]);

  const send = (question: string) => {
    if (busy || paused || !question.trim()) return;
    ask(question.trim());
    setDraft("");
  };
  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    send(draft);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends; Shift+Enter starts a new line.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      send(draft);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-stone-50 text-slate-900">
      <div className="sticky top-0 z-10">
        <header inert={covered} className="border-b border-stone-200 bg-stone-50/90 backdrop-blur">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
            <h1 className="font-semibold">OmniCorp Knowledge Base Assistant</h1>
            <button
              type="button"
              onClick={() => {
                reset();
                setDraft("");
              }}
              className="shrink-0 rounded px-2 py-1 text-sm whitespace-nowrap text-slate-600 hover:bg-stone-200 hover:text-slate-900"
            >
              New conversation
            </button>
          </div>
        </header>
        {/* Never inert: the stack's state stays reachable while an Article is open. */}
        {banner && <ReadinessBanner view={banner} />}
      </div>

      <main
        inert={covered}
        className="mx-auto w-full max-w-3xl flex-1 space-y-10 px-4 pt-8 pb-12 sm:px-6"
      >
        {turns.length === 0 ? (
          <section className="space-y-3 text-slate-600">
            <p>
              Ask about OmniCorp Nimbus. Answers come only from the internal Knowledge Base, with
              Citations you can check.
            </p>
            <p className="text-sm font-medium text-slate-500">Try one of these:</p>
            <ul className="space-y-1 text-sm">
              {SUGGESTED_QUESTIONS.map((question) => (
                <li key={question}>
                  <button
                    type="button"
                    onClick={() => send(question)}
                    disabled={paused}
                    className="text-left text-blue-700 hover:underline disabled:text-slate-400 disabled:no-underline"
                  >
                    {question}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ) : (
          turns.map((turn, i) => (
            <div
              key={turn.id}
              ref={i === turns.length - 1 ? latestTurn : undefined}
              className="scroll-mt-20"
            >
              <TurnView
                turn={turn}
                canAskAgain={!busy && !paused}
                onAskAgain={send}
                onOpenSection={onOpenSection}
              />
            </div>
          ))
        )}
      </main>

      <footer
        inert={covered}
        className="sticky bottom-0 border-t border-stone-200 bg-stone-50/95 backdrop-blur"
      >
        <form onSubmit={onSubmit} className="mx-auto max-w-3xl space-y-1 px-4 py-3 sm:px-6">
          <div className="flex items-end gap-2">
            <textarea
              aria-label="Your question"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={onKeyDown}
              maxLength={QUESTION_MAX_CHARS}
              rows={1}
              placeholder="Ask a question about OmniCorp Nimbus…"
              className="max-h-40 min-h-10 flex-1 resize-none rounded-md border border-stone-300 bg-white px-3 py-2 shadow-sm field-sizing-content focus:outline-2 focus:outline-blue-600"
            />
            {busy ? (
              <button
                type="button"
                onClick={stop}
                className="rounded-md bg-slate-200 px-4 py-2 font-medium text-slate-800 hover:bg-slate-300"
              >
                Stop
              </button>
            ) : (
              <button
                type="submit"
                disabled={paused || !draft.trim()}
                aria-describedby={paused ? pausedReasonId : undefined}
                className="rounded-md bg-slate-900 px-4 py-2 font-medium text-white hover:bg-slate-700 disabled:opacity-40"
              >
                Send
              </button>
            )}
          </div>
          {paused && (
            <p id={pausedReasonId} className="text-right text-xs text-slate-500">
              Questions can be sent once the Knowledge Base is ready.
            </p>
          )}
        </form>
      </footer>
    </div>
  );
}

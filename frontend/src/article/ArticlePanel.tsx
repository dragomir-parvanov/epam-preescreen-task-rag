import { useEffect, useId, useRef, useState, type KeyboardEvent, type RefObject } from "react";
import { api } from "../api/client";
import type { components } from "../api/schema";
import { Markdown } from "../chat/Markdown";
import { VersionBadges } from "../chat/PassageRow";
import { isV2Only } from "../chat/passages";

type Passage = components["schemas"]["Passage"];
type ArticleDetail = components["schemas"]["ArticleDetail"];
type ErrorBody = components["schemas"]["ErrorBody"];

/** The last day of support for Nimbus v2, as the v2 Legacy Reference states it. */
const V2_END_OF_SUPPORT = "2027-03-31";

const UNREACHABLE: ErrorBody = {
  code: "internal_error",
  message: "Couldn't load this Article. Check that the backend is running, then try again.",
};

/**
 * Citation click-through: the Passage's whole Article in a slide-over panel, scrolled to the
 * Passage's Section, which is highlighted. The conversation stays in place behind it.
 *
 * Focus moves into the panel when it opens and back to whatever had it (the "Open Section"
 * button) when it closes, with ×, Escape or a click on the backdrop.
 */
export function ArticlePanel({ passage, onClose }: { passage: Passage; onClose: () => void }) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);
  const highlighted = useRef<HTMLElement>(null);
  const article = api.useQuery(
    "get",
    "/articles/{article_id}",
    { params: { path: { article_id: passage.article.id } } },
    // The Knowledge Base is loaded once at startup. A failure is shown at once, with Try again.
    { staleTime: Infinity, retry: false },
  );

  // Whatever had focus as the panel opened: the Open Section button. Read once, before the
  // panel takes focus, so StrictMode's second effect run can't mistake the panel for it.
  const [opener] = useState(() => document.activeElement);
  useEffect(() => {
    panel.current?.focus();
    return () => {
      if (opener instanceof HTMLElement) opener.focus();
    };
  }, [opener]);

  const loaded = article.data;
  // openapi-fetch hands back the error envelope, or the text of a reply that isn't one (a
  // proxy's error page, say); `fetch` throws a TypeError when nothing answers at all.
  const { error } = article;
  const failure =
    typeof error === "object" && error !== null && "error" in error ? error.error : UNREACHABLE;
  useEffect(() => {
    if (loaded) highlighted.current?.scrollIntoView({ block: "start" });
  }, [loaded]);

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-30 flex justify-end">
      <div
        data-testid="article-panel-backdrop"
        aria-hidden
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/40"
      />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onKeyDown={onKeyDown}
        className="relative flex h-full w-full flex-col bg-white shadow-2xl outline-none sm:max-w-2xl"
      >
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3 sm:px-6">
          <div className="min-w-0 space-y-1">
            <p className="font-mono text-xs break-all text-slate-500">
              knowledge-base/{passage.article.id}.md
            </p>
            <h2 id={titleId} className="text-lg leading-snug font-semibold">
              {loaded?.title ?? passage.article.title}
            </h2>
            {loaded && (
              <p className="flex items-center gap-1">
                <VersionBadges of={loaded} />
              </p>
            )}
          </div>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="-mr-2 shrink-0 rounded px-2 text-2xl leading-none text-slate-500 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-blue-600"
          >
            ×
          </button>
        </header>
        {/* Outside the scrolling body, so it stays in view whichever Section was opened. */}
        {loaded?.status === "deprecated" && (
          <p className="border-b border-orange-200 bg-orange-50 px-4 py-2 text-sm text-orange-900 sm:px-6">
            {isV2Only(loaded)
              ? `This Article describes Nimbus v2, which is deprecated: end of support ${V2_END_OF_SUPPORT}.`
              : "This Article is deprecated."}
          </p>
        )}

        <div className="flex-1 overflow-y-auto overscroll-contain px-4 py-4 sm:px-6">
          {article.isPending && <p className="text-sm text-slate-500">Loading the Article…</p>}
          {article.isError && (
            <ArticleError
              error={failure}
              retrying={article.isFetching}
              onTryAgain={() => void article.refetch()}
            />
          )}
          {loaded && (
            <ArticleBody
              article={loaded}
              sectionId={passage.section.id}
              highlighted={highlighted}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function ArticleError({
  error,
  retrying,
  onTryAgain,
}: {
  error: ErrorBody;
  retrying: boolean;
  onTryAgain: () => void;
}) {
  return (
    <div
      role="alert"
      className="space-y-1 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900"
    >
      <p className="font-semibold">This Article couldn't be opened</p>
      <p>{error.message}</p>
      <div className="flex items-center justify-between gap-2 pt-1">
        <code className="font-mono text-xs text-red-500 select-all">{error.code}</code>
        <button
          type="button"
          onClick={onTryAgain}
          disabled={retrying}
          className="rounded bg-red-700 px-3 py-1 text-xs font-medium text-white hover:bg-red-800 disabled:opacity-50"
        >
          Try again
        </button>
      </div>
    </div>
  );
}

function ArticleBody({
  article,
  sectionId,
  highlighted,
}: {
  article: ArticleDetail;
  sectionId: string;
  highlighted: RefObject<HTMLElement | null>;
}) {
  return (
    <div className="space-y-4 text-sm text-slate-800">
      {article.sections.map((section) => {
        const current = section.id === sectionId;
        return (
          <section
            key={section.id}
            ref={current ? highlighted : undefined}
            // The path starts with the Article title; the intro has nothing after it.
            aria-label={section.path.slice(1).join(" › ") || "Introduction"}
            aria-current={current ? "location" : undefined}
            className={
              current
                ? "-mx-3 scroll-mt-4 rounded-md bg-amber-50 px-3 py-2 ring-1 ring-amber-300"
                : undefined
            }
          >
            <Markdown text={section.markdown} headingOffset={1} />
          </section>
        );
      })}
    </div>
  );
}

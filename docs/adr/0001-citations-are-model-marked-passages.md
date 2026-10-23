# Citations are the Passages the model marked; uncited answers are flagged, not backfilled

An Answer's Citations are exactly the retrieved Passages the model referenced with a valid inline `[n]` marker. Markers pointing at Passages that don't exist are removed, and the remaining ones are renumbered `[1]..[k]` in order of first appearance. When a non-Refusal answer contains no valid markers, it is returned as an **Uncited Answer** with a visible warning. Its retrieved Passages are returned separately as "retrieved, not cited" and are never promoted to Citations. We chose this so that "cited" always means "the model claimed to use it". In a local benchmark, the small keyless models cited poorly: `llama3.2:3b` emitted no markers in plain text, and in JSON mode both small models listed every chunk as a source. A design that hides this would mislead a CSM checking a client-facing answer.

Retrieved Passages are always returned next to Citations (never mixed in), so the evaluation can tell a retrieval failure from a citation failure.

## Considered Options

- **Show every retrieved Passage as a Citation.** Rejected because it breaks "cited = used" and reproduces the "lists every chunk" failure.
- **Turn uncited answers into Refusals.** Rejected because it is strict but would refuse most answers from keyless local models, hiding the model's behaviour instead of exposing it.
- **Verify each claim with an LLM judge or lexical overlap.** Rejected because it adds latency and cost per request, and the judge has its own failure modes. Citation quality is measured offline against the golden questions' expected sources instead.

## Consequences

- "Used" is the model's claim and is not verified per request. Citation precision and recall in the evaluation are the check.
- With a weak model, Uncited Answers will be common. The UI and README present that as an honest signal, not a bug.

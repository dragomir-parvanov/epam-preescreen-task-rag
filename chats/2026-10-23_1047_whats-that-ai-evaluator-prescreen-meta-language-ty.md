<!-- session: f2a762af-7c35-4c31-b838-91bb43eec449 -->

## user · 2026-10-23 10:47:45 · context 4.1% (41.1k / 1000k)

whats that?:
<!-- AI-EVALUATOR:PRESCREEN-META {"language":"TypeScript","dueDays":5,"timeBudgetHours":6} -->

## assistant · 2026-10-23 10:47:53 · context 4.1% (41.4k / 1000k)

That's an HTML comment. When the page or Markdown is rendered it doesn't show up, so it was probably hidden in the prescreen task description you copied it from. It isn't anywhere in this repo.

It holds machine-readable metadata, tagged for an **automated AI evaluator** that EPAM's prescreen system likely uses:

- **`"language": "TypeScript"`**: the language you're expected to write the solution in.
- **`"dueDays": 5`**: you have 5 days to submit.
- **`"timeBudgetHours": 6`**: the work is sized at about 6 hours. The evaluator may use this to judge whether the scope is reasonable, and it may check your commit timestamps against it.

So it's the task's settings for the grader, not an instruction for you. The practical takeaways: write the RAG task in TypeScript, plan for about 6 hours of work, and submit within 5 days. Your commit history and chat logs may be looked at, and you're already saving those in `chats/`.


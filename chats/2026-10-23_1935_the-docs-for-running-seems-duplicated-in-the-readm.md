<!-- session: 2f53dd9c-e6d6-4b75-b6ad-9f73759be5b6 -->

## user · 2026-10-23 19:35:40 · context 4.3% (42.8k / 1000k)

the docs for running seems duplicated in the README

## assistant · 2026-10-23 19:36:14 · context 5.2% (52.2k / 1000k)

I removed the duplicated run instructions from `README.md`. The new "Quick start for reviewers" section is now the only place that covers the first run, and "How to run" keeps just the details the Quick start doesn't have.

What I took out of "How to run":
- **Prerequisites paragraph:** it repeated the Quick start. Its one extra detail, why Docker Engine 25 is needed (the healthcheck's `start_interval`), now sits in the Quick start's prerequisites line.
- **The `cp .env` / `pixi run up` / `pixi run down` block:** the Quick start already has these commands.
- **The keyless Ollama setup:** the steps to uncomment the two `.env` lines and the "about 8 GB" warning were in both places. The Quick start's "No key?" note keeps them. The Ollama bullet in "How to run" now has only the extras: the download breakdown (5.0 GB image + 2.7 GB model), how to follow the download in the logs, the 30-minute wait, and the native Ollama option on a Mac.

"How to run" now opens with a line pointing back to the Quick start, followed by the API docs URL. The rest of it is unchanged: picking an LLM, first boot, stopping and re-indexing, and the task table. The section's name and link stay the same, and nothing outside the README linked to it. I haven't committed anything.


# epam-preescreen-task-rag

## Chat recording

Every Claude Code session in this repo is saved automatically to `chats/<start-time>_<first-prompt>.md`, for example `chats/2026-10-23_1012_testing-if-this-gets-recorded.md`. Nothing is committed automatically. Committing the chat files is up to you.

The name is built from the session's start time and a slug of its first real prompt (slash commands are skipped), cut to 50 characters. Both are fixed once the session starts, so the file keeps its name as the chat goes on. The first line of each file is `<!-- session: <session-id> -->`, which links the file back to its Claude Code session.

### How it works

- `.claude/settings.json` registers a `Stop` hook. It runs each time Claude finishes a reply.
- The hook (`.claude/hooks/record-session.sh`) reads the session transcript (JSONL) that Claude Code passes to it.
- The `Stop` hook fires before the final reply is written to the transcript. To catch that reply, the script hands off to a detached background process and returns at once. That process waits until the transcript file stops changing (at most about 10 seconds).
- It then renders the whole transcript again into the session's chat file, overwriting the previous version. If the session was saved earlier under a different name, such as an old `<session-id>.md`, that file is removed. Each message gets a `## user · YYYY-MM-DD HH:MM:SS` or `## assistant · ...` header, in local time.
- Only the text of user and assistant messages is kept. Tool calls, tool results and injected `<system-reminder>` blocks are dropped.

### Notes

- Slash commands such as `/model`, and their output, are recorded as user messages.
- Requirements: `bash` and `jq`. The hook only runs inside a git work tree and writes to `chats/` at the repo root.
- To turn recording off, remove the `Stop` entry from `.claude/settings.json`.

# epam-preescreen-task-rag

## Chat recording

The task requires the AI assistant conversation logs to be committed, so a Claude Code `Stop` hook (`.claude/hooks/record-session.sh`) saves every session in this repo to `chats/<start-time>_<first-prompt>.md`.

- Only user and assistant text is kept, so the logs read as a conversation rather than a dump of tool output.
- Each message shows its time and how full the context window was, for example `context 5.7% (57.4k / 1000k)`.
- Showing context % to prevent getting into the dumb zone

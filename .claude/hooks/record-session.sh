#!/usr/bin/env bash
# Stop hook: renders the current chat transcript to chats/<start-time>_<first-prompt-slug>.md
# (committing is left to the user).
set -euo pipefail

input=$(cat)
transcript=$(jq -r .transcript_path <<<"$input")
session=$(jq -r .session_id <<<"$input")
cd "$(jq -r .cwd <<<"$input")"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
cd "$(git rev-parse --show-toplevel)"

# The Stop hook fires before the final assistant message is flushed to the transcript,
# so finish in a detached background process once the file has stopped changing (max ~10s)
if [[ -z "${RECORD_SESSION_BG:-}" ]]; then
  RECORD_SESSION_BG=1 setsid "$0" <<<"$input" >/dev/null 2>&1 &
  exit 0
fi
sleep 1
for _ in $(seq 1 18); do
  before=$(stat -c %Y.%s "$transcript")
  sleep 0.5
  [[ "$(stat -c %Y.%s "$transcript")" == "$before" ]] && break
done

mkdir -p chats

# Name the file after when the session started and its first real prompt (slash commands
# skipped); both are fixed once the session exists, so the name stays stable across turns
start=$(jq -rs 'map(.timestamp // empty) | first // "" | sub("\\.[0-9]+Z$"; "Z")
  | try (fromdate | strflocaltime("%Y-%m-%d_%H%M")) catch "unknown"' "$transcript")
slug=$(jq -rs '
  map(select(.type == "user" and (.isMeta | not))
      | .message.content | if type == "string" then . else map(select(.type == "text").text) | join(" ") end
      | gsub("<system-reminder>[\\s\\S]*?</system-reminder>"; ""))
  | map(select(test("^\\s*<(command|local-command)") | not) | select(test("\\S")))
  | first // ""' "$transcript" \
  | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | cut -c1-50 | sed 's/^-*//; s/-*$//')
out="chats/${start}_${slug:-session}.md"
marker="<!-- session: $session -->"
# Parallel sessions started in the same minute with the same prompt would share that name,
# and the later render would overwrite the other session, so the second one gets an id suffix
if [[ -e "$out" ]] && [[ "$(head -1 "$out")" != "$marker" ]]; then
  out="chats/${start}_${slug:-session}_${session:0:8}.md"
fi

# Drop earlier renders of this session saved under another name (e.g. the old <uuid>.md)
rm -f "chats/$session.md"
grep -lxF -- "$marker" chats/*.md 2>/dev/null | grep -vxF -- "$out" | xargs -r rm -f -- || true

# User/assistant text only; drops tool calls, tool results and injected system reminders.
# Context usage is the prompt token count of the API call that produced a reply, as a share
# of the model's window (1M, or 200k for Haiku 4.5 and older); a user message gets the count
# of the next call, which is the first one to include it
{
echo "$marker"
echo
jq -rs '
  def ctx: (if .message.model // "" | test("haiku-4|claude-3") then 200000 else 1000000 end) as $window
    | .message.usage // {}
    | (.input_tokens // 0) + (.cache_creation_input_tokens // 0) + (.cache_read_input_tokens // 0)
    | select(. > 0)
    | " · context \(. * 1000 / $window | round / 10)% (\(. / 100 | round / 10)k / \($window / 1000)k)";
  . as $all
  | to_entries[] | .key as $i | .value
  | select((.type == "user" or .type == "assistant") and (.isMeta | not))
  | (.message.content
      | if type == "string" then . else map(select(.type == "text").text) | join("\n") end
      | gsub("<system-reminder>[\\s\\S]*?</system-reminder>"; "")
      | gsub("^\\s+|\\s+$"; "")) as $text
  | select($text != "")
  | (.timestamp // "" | sub("\\.[0-9]+Z$"; "Z") | try (fromdate | strflocaltime(" · %Y-%m-%d %H:%M:%S")) catch "") as $time
  | ((if .type == "assistant" then ctx else first($all[$i + 1:][] | select(.type == "assistant") | ctx) end) // "") as $ctx
  | "## \(.type)\($time)\($ctx)\n\n\($text)\n"
' "$transcript"
} > "$out"

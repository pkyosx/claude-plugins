# Orchestration — drive / spawn another terminal or agent

Control a second terminal or agent ("slave" Claude) from your session: spawn it, hand it a task, watch
liveness, collect its output. Distilled from a production Bash driver, plus the
newer **events/Feed** channel (cmux ≥ 0.6x) that replaces fragile screen-scraping.

## First principle: pick the cheapest pattern that works

1. **One-pass job (best, no driving):** the slave runs once and writes a file → bake the task into the launch
   command, then read the file from disk. Zero send/read choreography, none of the targeting gotchas.
2. **Interactive driving:** you must send follow-ups and react → spawn, then `send` / `send-key` / `read-screen`,
   pairing `--workspace` + `--surface` on every call.
3. **Fleet / unattended supervision:** subscribe to `cmux events` (or Feed) and answer prompts programmatically
   instead of polling the screen.

## Pattern 1 — one-pass (most robust)
```bash
cmux new-workspace --name worker --cwd /path --focus false \
  --command "claude --dangerously-skip-permissions --plugin-dir <your-plugin-dir> \"Read /path/task.md and follow it; write result to /path/out.md then stop.\""
# ...later: read /path/out.md from disk.
```
⚠️ `--command` is implemented as **send-text+Enter after creation** (not a real initial-command API), so it can
race with shell init. For anything load-sensitive, prefer **bare spawn + explicit `send`** (Pattern 2) so you
control timing. Track the returned `workspace:N` / UUID so you can `close-workspace` it later.

## Pattern 2 — interactive driving

### Spawn (split in a known workspace, or a fresh workspace)
```bash
WS_UUID="$CMUX_WORKSPACE_ID"                       # or a target workspace ref/UUID
SPLIT="$(cmux new-split right --workspace "$WS_UUID" 2>&1)"
SLAVE_SURFACE="$(printf '%s' "$SPLIT" | awk '{for(i=1;i<=NF;i++) if($i ~ /^surface:/) print $i}' | head -1)"
[ -n "$SLAVE_SURFACE" ] || { echo "FATAL: could not parse slave surface"; exit 3; }
cmux rename-tab --workspace "$WS_UUID" --surface "$SLAVE_SURFACE" "slave" 2>/dev/null || true
sleep 4                                            # CRITICAL: let the pty fully attach before sending
```

### Send text, THEN Enter — two separate steps
```bash
cmux send     --workspace "$WS_UUID" --surface "$SLAVE_SURFACE" "claude --dangerously-skip-permissions --plugin-dir <your-plugin-dir> \"do the thing\""
cmux send-key --workspace "$WS_UUID" --surface "$SLAVE_SURFACE" enter
```
- `send` types; `send-key enter` submits. Keep them separate (combining is unreliable).
- `send` escape sequences: `\n`/`\r` = Enter, `\t` = Tab. `send-key` takes key names: `enter`, `tab`,
  `backspace`, `ctrl+c`, etc. (case-insensitive). **`ctrl+u` does NOT clear Claude's input box — use `backspace`.**
- **Retry sends** — a single `send` can no-op while the pty settles. Wrap in ~3× with a short sleep.

### Read the slave's screen (the ONLY reliable cross-pane read)
```bash
cmux read-screen --workspace "$WS_UUID" --surface "$SLAVE_SURFACE" --scrollback 2>&1 | tail -40
cmux read-screen --workspace "$WS_UUID" --surface "$SLAVE_SURFACE" --lines 60   # last 60 lines (implies scrollback)
```
Use it for **liveness only**: spinner = busy, stable bare `❯` prompt = idle/done. Never `cmux rpc surface.read_text`
(reads your own surface). Beware **ghost text**: `❯ wait for it to finish` shown greyed is an autocomplete
*suggestion*, not real input — just `send` your actual text.

> **Targeting is verified, not folklore:** a marker `echo`'d into a spawned workspace with `--workspace WS`
> appears in *that* workspace's `read-screen` and is **absent from the caller's own surface** — pairing the flags
> addresses the right pane every time; dropping `--workspace` falls back to your own.

### Discover & clean up
```bash
cmux tree --json                                  # structured topology: find a slave's workspace/pane/surface refs
cmux list-pane-surfaces --workspace "$WS_UUID"    # surfaces within a pane
cmux close-surface   --surface "$SLAVE_SURFACE" --workspace "$WS_UUID"   # a SPLIT-spawned slave is a surface
cmux close-workspace --workspace "$WS_UUID"                              # a workspace-spawned slave is a workspace
```
Prefer `cmux tree --json` over `awk`-parsing spawn output when you need to re-find a slave you lost track of.

## Pattern 3 — supervise without polling (events / Feed)
Instead of looping `read-screen`, subscribe to the event stream and act on real signals. See
`references/feed-and-events.md` for the full stream + Feed-answering details. Quick form:
```bash
# Tail agent + notification activity; wire the stdout lines into the Monitor tool.
cmux events --category agent --category notification --cursor-file ~/.cache/cmux/drive.seq --reconnect
```
Cadence for a known long build/install: nudge at ~10-min intervals, don't react to every "waiting" notification
(a `Completed in <ws>` notification is an end-of-turn status, NOT a question — read the screen before replying).
If you also armed a `ScheduleWakeup` fallback, cancel it once the event Monitor is live (both firing is harmless
but wasteful).

## The three-actor model (why isolation matters)
For verification/eval-style work, keep three roles separate:
- **Orchestrator** (deterministic Bash) — spawns, sends, collects. Holds the success criteria.
- **Slave** (the agent under test) — sees only its task + where to write output. Can't game criteria it can't see.
- **Driver/observer** — watches from outside (events/files), answers structured prompts via hooks.

Give the slave a **self-contained brief** (task + output path) in its own cwd; don't leak harness internals.
For long sweeps, run **one worker + one heavy resource (VM) at a time** — serial by design keeps RAM/contention sane.

## Checklist (the things that actually bite)
1. **Pair `--workspace` + `--surface` on every cross-pane command.** #1 failure cause.
2. **`sleep 4` after spawn** before the first send (pty attach race).
3. **send + send-key enter as two steps, with retry.**
4. **Result channel = files / events / hooks; screen = liveness only.**
5. **Spawn serially** (5–10s apart, ≤3 concurrent). A failed spawn is usually transient — see
   `references/troubleshooting.md`, do NOT tight-loop or ask for a relaunch.
6. **Only close what you created**; track refs. Split slave → `close-surface --surface surface:N --workspace workspace:N`;
   workspace slave → `close-workspace --workspace workspace:N` (colon form, not bare `N`).

## Source
Distilled from a production Bash driver that implements the three-actor model and a
hook-based AskUserQuestion capture (spawn → send → read liveness → collect file output).

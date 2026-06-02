---
name: cmux
description: >
  Control cmux — the terminal/browser workspace manager — from a Claude session via its `cmux` CLI.
  Use this skill for ANY cmux task: driving or spawning another terminal/agent session ("slave"
  Claude) and reading its output; browser automation in cmux panes (open URL, click, fill, snapshot,
  read page, check console errors, log in, save session); managing windows/workspaces/panes/surfaces;
  answering agent permission/question prompts via Feed; subscribing to the cmux events stream; sending
  notifications; or diagnosing cmux daemon problems (phantom panes, broken-pipe / socket wedges,
  workspaces that won't spawn). Triggers on "cmux", "drive a cmux pane", "spawn a slave session",
  "control another terminal", "read a cmux pane", browser tasks (URL / web page / frontend / "open
  this page" / "check console errors" / "fill the form" / "screenshot"), "cmux feed", "cmux events",
  "cmux notify", or any cmux daemon / workspace / surface error. Even if the user doesn't say "cmux"
  explicitly — if the task involves driving another terminal session, or a browser/URL/web page on
  this Mac, use this skill.
---

# cmux — drive terminals, browsers, and agents from the CLI

`cmux` controls the cmux app over a Unix socket. One binary (`/Applications/cmux.app/Contents/Resources/bin/cmux`)
exposes four task domains. **Read the matching reference file before doing real work** — each holds the
battle-tested recipes and the gotchas that have actually bitten us.

| You want to… | Read | Core commands |
|---|---|---|
| **Drive / spawn another terminal or agent** (slave Claude, A/B runs, CI workers) | `references/orchestration.md` | `new-workspace`, `new-split`, `send`, `send-key`, `read-screen` |
| **Automate a browser** (open URL, click, fill, snapshot, read, debug, log in) | `references/browser.md` | `browser open/snapshot/click/fill/wait/get/eval/state` |
| **Observe agents & answer their prompts** (Feed, events stream, notifications) | `references/feed-and-events.md` | `events`, `hooks setup`, `feed`, `notify` |
| **Fix a cmux daemon problem** (phantom pane, broken-pipe, won't spawn) | `references/troubleshooting.md` | `ping`, `tree`, `surface-health`, `close-workspace` |

Run `cmux --help`, `cmux <command> --help`, or `cmux capabilities` (JSON method list) to see the full surface.
Verified against **cmux 0.64.11**.

## Mental model — internalize these three things first

### 1. The targeting rule (the #1 cause of "it hit the wrong pane")
`cmux` reads `CMUX_WORKSPACE_ID` and `CMUX_SURFACE_ID` from **your own** session's env and uses them as
the default target. Short refs (`workspace:2`, `surface:7`) are **context-relative**, not global.

- **Always pass `--workspace <WS> --surface <S>` TOGETHER** when addressing another pane. `--workspace`
  supplies the resolution context that makes the surface ref point at the right pane. `--surface` alone
  silently falls back to *your* surface.
- **Never use `cmux rpc surface.read_text` to read another pane** — it ignores the surface param and reads
  your own. Use `cmux read-screen --workspace <WS> --surface <S>` for cross-pane reads.
- Prefer **UUIDs** (from `cmux <cmd> --id-format uuids` or `--json`) when you persist a handle across calls;
  refs/indexes can shift.

### 2. Daemon health is a real, finite resource — don't hammer it
The cmux daemon **degrades under burst load** and there is no amount of retrying that fixes a wedged
daemon faster than *waiting*. This has cost us hours. Hard rules:

- **`cmux ping` → `PONG`** is your liveness probe. Use it before/after risky bursts.
- **Spawn workspaces serially**, 5–10s apart. Max ~3 concurrent on this Mac; rest 60–120s between batches.
- A failed spawn ("Terminal N" phantom, or `Failed to write to socket (Broken pipe, errno 32)`) is usually
  **transient contention, NOT a broken install.** Do **not** tight-probe-loop (it makes it worse) and do
  **NOT** ask the user to relaunch cmux. Close the bad workspace, wait 30–60s, retry once. See
  `references/troubleshooting.md` for the full playbook.

### 3. Result channel = files/events; screen = liveness only
When driving a slave, **don't parse the TUI for results.** Have the slave write output to a file, or
subscribe to `cmux events` / Feed. Use `read-screen` only to tell busy (spinner) from idle (bare `❯`).

## Environment & conventions
- `CMUX_WORKSPACE_ID` / `CMUX_SURFACE_ID` — auto-set inside cmux terminals; default target for every command.
- `CMUX_SOCKET_PATH` — override the socket (default `~/Library/Application Support/cmux/cmux.sock`; docs also
  reference `~/.config/cmux/cmux.sock`). Auto-discovers tagged/debug sockets.
- `CMUX_QUIET=1` — silence the "X is now an alias for Y" migration notices (e.g. `list-workspaces` →
  `workspace list`). Set it in scripts so parsing isn't polluted.
- `--json` / `--id-format uuids|both` — structured output; use when capturing a ref/UUID for later commands.

## Spawning a Claude slave — the canonical flags
When launching a fresh Claude in a cmux workspace/tab for autonomous work, **always** use:
```bash
claude --dangerously-skip-permissions --plugin-dir <your-plugin-dir>
```
Bare `claude` starts interactive without your plugins and still prompts for every tool — defeating the
purpose of an unattended side-tab. (cmux's own wrapper launches Claude with `--allow-dangerously-skip-permissions`
so Feed can later flip it into bypass mode; the explicit flags above are for when *you* spawn it.)

## Safety rails (do not skip)
- **Process isolation:** never `pkill -f 'claude'` / broad patterns — you will kill the user's interactive
  sessions. Scope kills to the run path (`pkill -f 'your-ci-runner/runs/'`, `pkill -f 'orchestrate.sh.*<ticket>-'`);
  `pgrep -f <pattern>` first to inspect matches.
- **Only `close-workspace` workspaces YOU spawned** — track their refs/UUIDs; never wildcard-close.
- **Never commit browser `state save` files** — they hold auth tokens.
- `cmux close-workspace` needs the **ref form** `--workspace workspace:N` (with the colon), not bare `N`.

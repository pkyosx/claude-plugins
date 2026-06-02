# Feed, events stream & notifications

The modern way to **observe** agents and **answer** their prompts without scraping a TUI. Use these instead of
`read-screen` polling whenever you supervise one or more agent sessions.

## Events stream — `cmux events`
A reconnectable stream of workspace / pane / surface / notification / browser / **Feed** / **agent-hook** activity.
Also appended to `~/.cmuxterm/events.jsonl` (newline-delimited JSON) for audit/catch-up.

```bash
cmux events --cursor-file ~/.cache/cmux/events.seq --reconnect          # durable, resumes after restart
cmux events --category feed --category agent --no-heartbeat             # only agent decisions
cmux events --category notification
cmux events --after <seq> --limit 50 --no-heartbeat                     # bounded one-shot read
```
Frames are JSON objects, one per line: the first is always `ack` (with `boot_id`, `resume{…}`), then replay,
then live events + heartbeats (every ~15s; suppress with `--no-heartbeat`). Each event has a process-local
`seq` (monotonic), a stable `id` (use for dedupe), `name`, `category`, `source`, `occurred_at`, and a
`payload`. **Persist the latest `seq`** (or use `--cursor-file`) and resume with `--after`. If cmux restarts,
`boot_id` changes and `resume.gap=true` → process the replayed tail, then refresh state via snapshot commands
(`workspace list`, `list-notifications`, `tree`).

Useful event names: `feed.item.received` (a hook needs a decision), `feed.item.completed` (decision delivered),
`agent.hook.<HookEventName>` (Claude/Codex/etc. native hook events), `notification.created`.

**Driving use:** tail `--category agent --category notification`, feed the stdout lines into the **Monitor**
tool, and react to real signals instead of blind `read-screen` loops. The request line takes over the socket —
don't send other commands on that connection.

## Feed — answer permission / plan / question prompts from outside the TUI
Feed is cmux's inline surface for agent decisions (right sidebar, `Ctrl-4`, or `cmux feed tui`). It surfaces
three actionable types and **parks the agent's hook on a semaphore until you answer (≤120s, then it falls
through to the agent's own TUI prompt — Feed is advisory, never a hard block):**
- **Permission requests** — Once / Always / All tools / Bypass / Deny
- **ExitPlanMode** — Ultraplan / Manual / Auto / Deny
- **AskUserQuestion** — pick one or several, Submit

### Install the bridge (once per agent)
```bash
cmux hooks setup                  # installs Feed + notification hooks for every supported agent on PATH
cmux hooks setup --agent codex    # or a single agent (see list below)
cmux hooks codex install          # equivalent per-agent form;  cmux hooks <agent> uninstall to remove
cmux hooks uninstall [--agent X]
```
Supported agents (0.64.11): `codex, grok, opencode, pi, amp, cursor, gemini, kiro, antigravity (agy),
rovodev (rovo), hermes-agent, copilot, codebuddy, factory, qoder`. Agents without a binary on `PATH` are
skipped. **Claude Code needs no `hooks install`** — its hooks are injected automatically by the cmux Claude
wrapper. For Claude Code the hook is wrapper-injected; cmux launches Claude with `--allow-dangerously-skip-permissions`
so a later PermissionRequest reply can switch the session into `bypassPermissions`. (Without that flag Claude
ignores `setMode: bypassPermissions`.) AskUserQuestion is answered by allowing the PermissionRequest with the
selected answers patched into the tool input.

### Inspect / answer / jump
The `cmux feed` **CLI** has only two subcommands; everything else is a **socket verb** called via `cmux rpc`:
```bash
cmux feed tui                     # interactive Feed (OpenTUI via Bun); --legacy for the built-in TUI
cmux feed clear [--yes]           # reset history (~/.cmuxterm/workstream.jsonl audit log)

cmux rpc feed.list                # → { items:[{id, kind, source, cwd, created_at, …}] }  (read the workstream)
cmux rpc feed.permission.reply '{"request_id":"…","decision":"allow"}'   # answer programmatically
cmux rpc feed.question.reply   '{"request_id":"…", …}'                   # AskUserQuestion
cmux rpc feed.exit_plan.reply  '{"request_id":"…", …}'                   # ExitPlanMode
cmux rpc feed.jump '{"id":"…"}'                                          # focus the agent's workspace+surface
```
`cmux rpc feed.list` takes no params (or `{}`). Reply verbs are keyed by the event's `request_id` (get it from
the `feed.item.received` event or `feed.list`). The full method set is in `cmux capabilities` → `feed.*`.
Decisions can also be clicked in the sidebar or in the native notification's inline buttons; double-clicking a
Feed row does the same as `feed.jump`.

**This is the structured "answer the slave's questions" channel** that `references/orchestration.md` Pattern 3
refers to — far more robust than reading the menu off the screen. Audit log: `~/.cmuxterm/workstream.jsonl`;
session→workspace map: `~/.cmuxterm/<agent>-hook-sessions.json`.

### Feed troubleshooting
- **Feed shows nothing:** the hook isn't installed — check `~/.codex/hooks.json` (etc.) for a
  `cmux hooks feed --source <agent>` entry; re-run `cmux hooks setup`.
- **Agent hangs >120s on a permission:** the hook didn't reach the socket — verify `$CMUX_SOCKET_PATH` matches
  the running app (default `~/.config/cmux/cmux.sock`).
- **No inline notification buttons:** macOS notification authorization was denied on first use — rows still
  appear in the sidebar.
- **Codex plan-mode questions stay in the terminal:** Codex `request_user_input`/`update_plan` aren't hook
  events in the stock TUI; Feed only sees Codex *permission* hooks today.

## Notifications — `cmux notify`
```bash
cmux notify --title "Build complete"
cmux notify --title "Claude Code" --subtitle "Permission" --body "Approval needed"
cmux notify --title "Done" --workspace workspace:3            # target a workspace/surface
# Detect-and-fallback in scripts:
command -v cmux >/dev/null && cmux notify --title "Done" --body "ok" || osascript -e 'display notification "ok" with title "Done"'
```
`cmux notify` is the CLI to **create** one; to read/manage them, use the `cmux rpc notification.*` socket verbs:
```bash
cmux rpc notification.list          # → { notifications:[ … ] }   (verified read-only)
cmux rpc notification.dismiss '{"notification_id":"…"}'
cmux rpc notification.mark_read '{"notification_id":"…"}'
cmux rpc notification.jump_to_unread
```
Navigate the panel in-app with `Cmd+Shift+U` (latest unread). A `Completed in <workspace>` notification is an
**end-of-turn status, not a question** — read the screen / events before replying so you don't waste a turn.
`cmux.json` `notifications.hooks` can filter banners/sounds/history (off by default).

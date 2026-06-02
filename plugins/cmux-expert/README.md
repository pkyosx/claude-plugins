# cmux-expert

A Claude Code plugin that turns Claude into an expert at driving [**cmux**](https://cmux.com) from
the command line — the terminal/browser workspace manager. It packages one comprehensive `cmux` skill
with a hub + four task references, distilled from real-world usage and the failure modes that actually
bite in practice.

Verified against **cmux 0.64.x**.

## What it covers

| Domain | What you can do | Reference |
|---|---|---|
| **Orchestration** | Spawn and drive a "slave" Claude/terminal session, send keystrokes, read its screen, collect output, run A/B agent sessions | `skills/cmux/references/orchestration.md` |
| **Browser automation** | Open URLs, snapshot the DOM, click/fill via element refs, wait, read content, run JS, debug console errors, save/restore login sessions | `skills/cmux/references/browser.md` |
| **Feed & events** | Answer agent Permission / AskUserQuestion / ExitPlanMode prompts from outside the TUI; subscribe to the reconnectable `cmux events` stream; send notifications | `skills/cmux/references/feed-and-events.md` |
| **Troubleshooting** | Recover from daemon contention — phantom panes, broken-pipe / socket wedges, workspaces that won't spawn — with a tested playbook and decision tree | `skills/cmux/references/troubleshooting.md` |

## The three things the skill drills first

1. **The targeting rule** — `cmux` defaults to *your own* pane via `CMUX_WORKSPACE_ID` / `CMUX_SURFACE_ID`,
   and short refs are context-relative. Always pass `--workspace <WS> --surface <S>` **together** to address
   another pane. Never `cmux rpc surface.read_text` for cross-pane reads — use `cmux read-screen`.
2. **Daemon health is a finite resource** — spawn workspaces serially, don't tight-loop on failures (it makes
   contention worse), and `cmux ping → PONG` is your liveness probe.
3. **Result channel = files / events; screen = liveness only** — when driving a slave, don't parse the TUI for
   results; have it write a file or subscribe to `cmux events` / Feed.

## Install

```bash
# In Claude Code:
/plugin marketplace add pkyosx/cmux-expert
/plugin install cmux-expert
```

Then ask Claude to do anything with cmux — "spawn a slave Claude and have it run X", "open this URL and check
for console errors", "why won't cmux spawn a new workspace" — and the `cmux` skill activates automatically.

## Layout

```
cmux-expert/
├── .claude-plugin/
│   ├── plugin.json          # plugin manifest
│   └── marketplace.json     # self-marketplace (install this repo directly)
└── skills/
    └── cmux/
        ├── SKILL.md         # hub: mental model, capability map, safety rails
        ├── references/      # orchestration · browser · feed-and-events · troubleshooting
        └── evals/           # browser-automation eval cases
```

## License

MIT

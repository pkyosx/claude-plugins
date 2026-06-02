# pkyosx-plugins

Monorepo for pkyosx's Claude Code plugins. One marketplace, many plugins.

## Plugins

| Plugin | What it does |
|---|---|
| [`agent-retro`](plugins/agent-retro) | Retrospective + experience recall loop so agents learn across sessions. |
| [`dont-touch-secrets`](plugins/dont-touch-secrets) | Keep credential values out of the conversation transcript. |
| [`cmux-expert`](plugins/cmux-expert) | Drive [cmux](https://cmux.com) from the CLI: orchestrate slave agent sessions, automate the built-in browser, observe agents via Feed + events, and recover from daemon contention. |

## Install

```
/plugin marketplace add pkyosx/claude-plugins
/plugin install agent-retro@pkyosx-plugins
/plugin install dont-touch-secrets@pkyosx-plugins
/plugin install cmux-expert@pkyosx-plugins
```

Run these in the Claude Code prompt. The first line registers the marketplace; each
`/plugin install` adds one plugin. **Open a new session afterwards** — plugins load at
session start, so a freshly installed plugin only activates in the next session. Verify with
`/plugin` (the installed list) or check that the skill name appears in a new session
(e.g. `cmux` for `cmux-expert`).

## Repo layout

```
.
├── .claude-plugin/marketplace.json   # lists every plugin
└── plugins/
    ├── agent-retro/
    │   ├── .claude-plugin/plugin.json
    │   └── skills/…
    ├── dont-touch-secrets/
    │   ├── .claude-plugin/plugin.json
    │   └── skills/…
    └── cmux-expert/
        ├── .claude-plugin/plugin.json
        └── skills/cmux/…
```

Each plugin lives under `plugins/<name>/` with its own `plugin.json` and skills. The root `marketplace.json` references them via local paths (`"./plugins/<name>"`).

## Adding a plugin

1. Create `plugins/<name>/.claude-plugin/plugin.json` and `plugins/<name>/skills/<name>/SKILL.md`.
2. Add an entry to `.claude-plugin/marketplace.json`.
3. Commit, push, done.

## History

`agent-retro` and `dont-touch-secrets` were originally separate repos; their full commit history was preserved here via `git subtree add`.

## License

MIT

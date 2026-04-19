# pkyosx-plugins

Marketplace manifest for pkyosx's Claude Code plugins. Each plugin lives in its own repo; this repo just lists them so one `/plugin marketplace add` pulls everything.

## Plugins

| Plugin | Repo | What it does |
|---|---|---|
| [`agent-retro`](https://github.com/pkyosx/claude-plugin-retro) | `pkyosx/claude-plugin-retro` | Retrospective + experience recall loop so agents learn across sessions. |
| [`dont-touch-secrets`](https://github.com/pkyosx/claude-plugin-dont-touch-secrets) | `pkyosx/claude-plugin-dont-touch-secrets` | Keep credential values out of the conversation transcript. |

## Install

```
/plugin marketplace add pkyosx/claude-plugins
/plugin install agent-retro@pkyosx-plugins
/plugin install dont-touch-secrets@pkyosx-plugins
```

## License

MIT

# agent-retro

A Claude Code plugin that gives AI agents a persistent learning loop. After completing tasks, run a retrospective to capture hard-won lessons. Before starting new tasks, the agent automatically recalls relevant past experiences to avoid repeating mistakes.

## How it works

**Three modes:**

1. **Retro mode** (`/retro`) — Run after a task to reflect on what was inefficient, what failed, and what workarounds were discovered. Stores structured learnings in `~/.claude/memory/experiences/`.

2. **Recall mode** (automatic) — Before starting complex tasks, the agent checks the experience index for relevant past lessons and applies them proactively.

3. **Try Harder mode** (`/try-harder`) — Spawns a subagent to do a deep, thorough search of the entire experience store. Keeps your main context window clean while getting better recall accuracy than a quick index scan. Use when you're stuck or about to tackle something tricky.

**Architecture:**

```
~/.claude/memory/experiences/
├── index.md          # Quick-scan index (one-liner per experience, tagged)
├── git-workflow.md   # Domain-specific experience files
├── testing.md
├── debugging.md
└── ...
```

The two-tier design (lightweight index → detailed domain files) keeps token usage low. The agent reads the index (~50-100 lines) to find matches, then loads only the relevant detail files.

## Install

1. Add the marketplace:
   ```
   /plugin marketplace add pkyosx/claude-plugin-retro
   ```

2. Install the plugin:
   ```
   /plugin install agent-retro
   ```

   Or browse available plugins via `/plugin` → **Discover** tab.

### Auto-configuration

Add to your project's `.claude/settings.json` so the plugin is automatically available:

```json
{
  "extraKnownMarketplaces": {
    "pkyosx-plugins": {
      "source": {
        "source": "github",
        "repo": "pkyosx/claude-plugin-retro"
      }
    }
  }
}
```

### Local development

```bash
claude --plugin-dir /path/to/claude-plugin-retro
```

## Usage

### After a painful debugging session:

```
/retro
```

Or just describe what happened:

> "I just spent 30 minutes figuring out that cmux browser console list returns empty. Save this lesson."

The agent will:
1. Extract the lesson into a structured entry (Context, Problem, Root Cause, Solution, Rule)
2. Store it in the appropriate domain file
3. Update the index for future recall
4. Show you what it's saving for confirmation

### When you're stuck or want deeper recall:

```
/try-harder
```

The agent spawns a background subagent that:
1. Reads the full experience index
2. Scans all domain files (not just index matches)
3. Checks cross-project memories
4. Returns only the relevant lessons back to the main agent

This costs ~2-5K tokens for the search but can save 10-50K tokens of wasted retries. The main context window stays clean.

### Before starting a new task:

The agent automatically checks the experience index when you describe a task that matches past challenges. No action needed — it just works.

> "Check for JavaScript errors on our staging site using cmux browser."

The agent will find the relevant experience and use JS hooks from the start, instead of wasting time on the `console list` dead end.

## Experience entry format

```markdown
## [2024-01-15] Brief descriptive title

**Tags:** tool1, tool2, concept1
**Context:** What was being attempted
**Problem:** What went wrong (be specific)
**Root Cause:** Why it happened
**Solution:** What actually worked
**Rule:** One-line actionable guideline for next time
```

## License

MIT

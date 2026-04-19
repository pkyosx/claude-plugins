---
name: agent-retro
description: >
  Agent learning loop — retrospective, experience recall, and auto-nudge. This skill has three modes:

  **Retro mode (`/retro`):** Run after completing a task to reflect on what was inefficient, what failed,
  what workarounds were discovered, and store structured learnings for future sessions. Use this whenever
  the user says "retro", "retrospective", "what did we learn", "save this lesson", or after a session
  with notable struggles, retries, or dead ends.

  **Recall mode (proactive):** Before starting implementation work on a complex task, ALWAYS consult the
  experience index at ~/.claude/memory/experiences/index.md to check if past sessions encountered similar
  challenges. This is especially important when the task involves tools, patterns, or domains where past
  sessions hit problems. If the user describes a requirement and you recognize it might match a past
  hard-won lesson, check experiences BEFORE diving in. Even if the user doesn't ask — if you're about to
  do something that has a relevant experience entry, read it first. Think of this as "checking your notes
  before the exam."

  **Auto-nudge mode (silent, continuous):** While working, continuously monitor for learning opportunities.
  PROACTIVELY save experiences WITHOUT being asked when you detect: (1) a retry — you tried an approach
  that failed and had to switch to a different one, (2) a non-obvious discovery — something worked but
  only after investigation that a newcomer wouldn't know, (3) a tool gotcha — a tool behaved differently
  than expected. Don't ask the user for permission on auto-nudge saves — just save and briefly mention
  "Saved experience: {one-liner}" so they know. This is the closed learning loop.
---

# Agent Retro — Learning Loop

This skill gives you a persistent memory of hard-won lessons. It has three modes:
- **Retro**: reflect on what happened, extract learnings, store them
- **Recall**: before starting work, check if past experiences are relevant
- **Auto-nudge**: silently detect and save learnings during work — the closed learning loop

The experience store lives at `~/.claude/memory/experiences/` and persists across all projects and sessions.

## First-Time Setup

If `~/.claude/memory/experiences/` does not exist, create it along with an empty index:

```bash
mkdir -p ~/.claude/memory/experiences
```

Then create `~/.claude/memory/experiences/index.md` with:

```markdown
# Experience Index

One-liner per experience for quick scanning. Format:
`- [file.md#section-anchor] tags: tag1, tag2 — Summary`

## Entries
```

## Retro Mode

### When to run

- **Manual**: User invokes `/retro` after a task
- **Auto-suggest**: If you notice during a session that you hit significant struggles (3+ retries on
  the same approach, workarounds for tool limitations, non-obvious solutions that took multiple attempts),
  suggest running a retro at the end: "That was a tricky one — want me to run `/retro` to capture what
  we learned?"

Note: For lightweight, in-the-moment saves, use **Auto-nudge mode** (see below) instead of a full retro.

### How to run a retrospective

1. **Review the session.** Look back through the conversation for:
   - Commands or approaches that failed and had to be retried
   - Workarounds for tool limitations or unexpected behavior
   - Non-obvious solutions that took multiple attempts to discover
   - Patterns that worked well and should be repeated
   - Time sinks where a different approach would have been faster

2. **Draft experience entries.** For each significant learning, write a structured entry:

   ```markdown
   ## [YYYY-MM-DD] Brief descriptive title

   **Tags:** tool1, tool2, concept1, concept2
   **Context:** What was being attempted (1-2 sentences)
   **Problem:** What went wrong or was inefficient (be specific)
   **Root Cause:** Why it happened (the underlying reason, not just symptoms)
   **Solution:** What actually worked (exact commands, code, or approach)
   **Pattern:** The generalizable principle — what does this teach beyond this specific situation? (舉一反三)
   **Rule:** One-line actionable guideline for next time
   ```

3. **Categorize and store.** Each entry goes into a domain file under `~/.claude/memory/experiences/`.

   Organize by **tool or domain**, not by date or project. This makes retrieval efficient — when you're
   about to use a tool, you check that tool's experience file. Examples:

   - `git-workflow.md` — git, PR, branching lessons
   - `testing.md` — testing patterns and pitfalls
   - `debugging.md` — debugging techniques and gotchas
   - `api-integration.md` — external API patterns
   - `general.md` — cross-cutting workflow lessons

   Create new domain files as needed. If an experience spans multiple domains, put it in the most
   relevant one and add cross-reference tags.

4. **Update the index.** After adding entries, update `~/.claude/memory/experiences/index.md` with a
   one-liner per entry. The index is the scout's quick-scan file — it should be fast to read and
   pattern-match against.

   Format:
   ```markdown
   - [filename.md#section-anchor] tags: tag1, tag2, tag3 — One-line summary of the lesson
   ```

5. **Present to user.** Show the user what you're about to save. Let them confirm, edit, or skip entries
   before writing to disk.

### What makes a good experience entry

**Good entries are specific and actionable.** They capture the non-obvious — things that someone seeing
the task for the first time wouldn't know.

Good:
> **Rule:** When checking console errors via cmux browser, `console list` and `errors list` may return
> empty. Always install JS hooks via `eval` to monkey-patch console.error/warn and capture window.onerror.

Bad:
> **Rule:** Check for console errors carefully.

Good:
> **Rule:** mock.ANY and StrEnum show false diffs in pytest assertion output — only trust the
> "Differing items" section, ignore "Full diff" for those types.

Bad:
> **Rule:** Be careful with test assertions.

**Skip trivial lessons.** Don't store things that are obvious or well-documented. Focus on things that
cost real time to figure out.

### Generalize to behavior patterns (舉一反三)

**Every experience should be generalized beyond its specific situation.** The specific fix is useful once;
the underlying pattern is useful forever.

When writing an experience entry, always ask: "What general principle does this teach that applies to
situations I haven't seen yet?"

Replace the specific **Rule** with a **Pattern** that explains the underlying principle, then keep the
**Rule** as a concrete application of that pattern.

Bad (too specific — only helps if you hit this exact situation):
> **Rule:** Use `contextvars.ContextVar` not `threading.local` when passing state from ASGI middleware
> to FastMCP tool handlers.

Good (generalizable — helps in any async/sync boundary situation):
> **Pattern:** When passing state across async/sync boundaries, the correct mechanism depends on HOW the
> framework bridges them. Don't guess — read the framework's dispatch code. `anyio.to_thread.run_sync()`
> propagates contextvars but not thread-locals.
> **Rule:** Before choosing a state-passing mechanism, verify: "In what thread/context does the consumer
> run, and what gets propagated there?"

Bad (too specific):
> **Rule:** When MCP proxy returns 500, check Django error logs first.

Good (generalizable — helps in any proxy/upstream debugging):
> **Pattern:** Error 500 from a proxy almost always originates in the upstream service. Confirmation bias
> makes you look at the code you just changed, not the logs of the service that actually failed. After
> finding root cause, audit all changes made under the wrong assumption — they may introduce new bugs.
> **Rule:** Debug sequence: READ logs → VERIFY assumption → CHANGE code. Never skip step 2.

The **Pattern** field should make someone think "oh, I can apply this to X, Y, Z" — not just the
original situation.

## Auto-Nudge Mode

The closed learning loop. Unlike retro (manual, end-of-session) and recall (proactive, start-of-task),
auto-nudge runs **continuously during work** and saves learnings as they happen.

### How it works

While working on any task, watch for these signals:

| Signal | Example | What to save |
|--------|---------|-------------|
| **Retry** | Tried approach A, it failed, switched to B | Why A failed, why B works |
| **Non-obvious discovery** | Solution required reading source code or docs to figure out | The non-obvious fact |
| **Tool gotcha** | CLI flag, API behavior, or config that surprised you | The correct usage |
| **Workaround** | Had to work around a limitation | The limitation and the workaround |
| **User correction** | User said "no, do it this way instead" | What the user prefers and why |

### When a signal fires

1. **Save immediately** — don't wait for end-of-session. Write the experience entry to the
   appropriate domain file and update the index.

2. **Keep it lightweight** — auto-nudge entries can be shorter than full retro entries.
   Minimum: Tags, one-line Context, one-line Rule. Skip Problem/Root Cause if obvious.

   ```markdown
   ## [YYYY-MM-DD] Brief title

   **Tags:** tool1, tool2
   **Context:** What was being attempted
   **Rule:** The one-line takeaway
   ```

3. **Notify briefly** — after saving, mention it in one line so the user knows:
   ```
   💡 Saved experience: "Cerbos SDK v0.7.x uses `action` kwarg, not `actions`"
   ```
   Then continue with the task. Don't interrupt the flow.

4. **Don't over-save** — only save things that are non-obvious and would cost time if
   encountered again. If the lesson is "I had a typo", don't save it.

### What NOT to auto-save

- Typos and simple mistakes
- Things already documented in README/CLAUDE.md
- Trivial one-off issues that won't recur
- Information the user explicitly said to ignore

### Deduplication

Before saving, quickly scan the experience index to check if a similar entry already exists.
If it does, skip or update the existing entry rather than creating a duplicate.

## Recall Mode

### When to recall

- **Before complex tasks**: When the user describes a requirement that could involve past challenges,
  check the experience index before starting.
- **When you recognize a pattern**: If a task involves a tool/domain where you know experiences exist
  (because you can see the index), load the relevant file proactively.
- **On struggle detection**: If you're in the middle of a task and hitting walls, check if there's a
  relevant experience you missed.

### How to recall

1. **Read the index** at `~/.claude/memory/experiences/index.md`. This is lightweight — just one-liners
   with tags. Scan it for entries that match the current task's tools, concepts, or error patterns.

2. **Load relevant files.** If the index has matches, read only the specific experience files (not all
   of them). Use the section anchors from the index to jump to the right entry if the file is large.

3. **Apply the lessons.** Use the **Rule** and **Solution** fields to inform your approach. Don't just
   blindly follow them — they're guidelines from past context that may not perfectly fit the current
   situation. But they should save you from repeating known mistakes.

4. **Cite the experience.** When a past experience influences your approach, briefly mention it:
   "Based on a past experience with X, I'll use Y approach instead of Z."

### Token efficiency

The two-tier design (index → detail files) is intentional:
- The index is small enough to always read (~50-100 lines for dozens of experiences)
- Detail files are loaded only when relevant
- This avoids loading thousands of tokens of experiences that don't apply

If the experience store grows very large (100+ entries), consider having a subagent do the recall
scan in the background while you start on the obvious parts of the task.

## Experience Store Structure

```
~/.claude/memory/experiences/
├── index.md              # One-liner per experience, tagged for quick scanning
├── git-workflow.md       # Git workflow lessons
├── testing.md            # Testing patterns and pitfalls
├── debugging.md          # Debugging techniques
├── general.md            # Cross-cutting lessons
└── ...                   # New domain files as needed
```

## Bootstrapping

If the experience store doesn't exist yet or is empty, that's fine — there's nothing to recall. After
the first `/retro`, entries will start accumulating. The value compounds over time as the store grows.

If the user has existing notes in CLAUDE.md or memory files that represent hard-won lessons, suggest
migrating the relevant ones into the experience store format during the first retro.

---
name: try-harder
description: >
  Offload experience recall to a subagent for deeper, more thorough memory search without bloating the
  main context window. Use `/try-harder` when you're stuck on a problem, about to attempt something that
  feels like it could go wrong, or want a second opinion from past sessions. Also use this PROACTIVELY
  when you hit 2+ retries on the same approach — your past self probably left a note about this.
---

# Try Harder — Subagent Memory Recall

When invoked, spawn a background subagent that thoroughly searches the experience store and returns
only the relevant lessons. This keeps the main context window lean while getting better recall accuracy
than a quick index scan.

## How to use

When the user runs `/try-harder`, or when you decide to use this proactively:

1. **Gather context.** Identify the current task, tools involved, error messages, and what you've
   already tried. This becomes the search brief for the subagent.

2. **Spawn the subagent.** Use the Agent tool with this prompt structure:

   ```
   You are a memory recall agent. Your job is to search the experience store and return relevant
   lessons for the task described below.

   ## Current Task Context
   {Describe what the user is trying to do}

   ## Tools/Technologies Involved
   {List tools, frameworks, APIs being used}

   ## What's Been Tried (if applicable)
   {What approaches have failed or are being considered}

   ## Instructions

   1. Read the experience index at ~/.claude/memory/experiences/index.md
   2. For EVERY entry in the index, evaluate whether it could be relevant to the task context above.
      Be generous — include anything that might help, even tangentially.
   3. For each matching entry, read the full detail from the referenced domain file.
   4. Return a structured report with ONLY the relevant experiences, formatted as:

   ## Relevant Experiences Found

   ### [Title from domain file]
   **Source:** [filename.md#anchor]
   **Relevance:** Why this applies to the current task
   **Key Rule:** The one-line rule from the experience
   **Solution Summary:** Brief summary of what worked

   If nothing is relevant, say so clearly: "No relevant experiences found."

   Also scan for:
   - ~/.claude/memory/experiences/*.md (all domain files, not just index matches)
   - Any MEMORY.md files in the current project that might contain relevant notes
   - ~/.claude/projects/*/memory/*.md for cross-project memories

   Be thorough. Read every domain file if the index alone doesn't surface enough matches.
   The whole point is to be MORE thorough than a quick index scan.
   ```

3. **Apply the results.** When the subagent returns:
   - If relevant experiences were found, incorporate the **Rules** and **Solutions** into your approach
   - Cite what you're applying: "Past experience suggests X, so I'll do Y instead of Z"
   - If nothing was found, proceed normally — at least you checked

## When to use proactively (without /try-harder)

- You've retried the same approach 2+ times without success
- You're about to use a tool or pattern where past sessions often hit problems
- The user mentions something that sounds like a previously solved challenge
- You're debugging an error that feels like it could be a known gotcha

## Token efficiency

The subagent approach costs ~2-5K tokens for the search but saves potentially 10-50K tokens
of wasted retries. The main agent's context window stays clean — it only receives the condensed
relevant results, not the full experience store.

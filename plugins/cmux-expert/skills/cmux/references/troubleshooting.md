# Troubleshooting — cmux daemon contention & gotchas

The cmux daemon is a **finite, contention-prone resource.** Most "cmux is broken" moments are *transient load*,
and the only real fix is **patience + serial pacing**, not retrying harder. When in doubt: `cmux ping` → `PONG`
means the daemon is alive; act calm.

> **Provenance:** the health probes, the targeting/close-ref facts, and the upstream bug list are *verified against
> cmux 0.64.11*. The three contention failure modes below are *field-observed from real incidents* (they can't be
> safely re-manufactured on demand) — treat their thresholds as battle-tested heuristics, not lab constants.

## Health probes (use these before concluding anything is broken) — verified 0.64.11
```bash
cmux ping                                   # → PONG. Liveness. Cheap.
cmux tree                                   # full window→workspace→pane→surface map (real state); --json for parsing
cmux surface-health                         # per-surface: "surface:N type=terminal in_window=true/false"
cmux top --processes                        # per-process CPU%/MEMORY tree, grouped by workspace (find the RAM hog)
cmux memory                                 # app footprint + child RSS; names the heaviest child group
cmux debug-terminals                        # low-level per-surface state: mapped/tree/pty/tty/cwd/frame (deep debug)
CMUX_QUIET=1 cmux workspace list            # workspaces (legacy alias: list-workspaces)
```
`top --processes` is the fastest way to spot a runaway pane; `surface-health`/`debug-terminals` distinguish a
real pty from a phantom (`in_window=false` / `mapped=0 tree=0` = not a live terminal).

## Failure mode 1 — phantom pane ("Terminal N", no real pty)
**Symptom:** `new-workspace`/`new-split` returns OK, but the surface is a placeholder "Terminal N";
`read-screen` → "Terminal surface not found" / "Surface not ready". Upstream bugs #2555 (frame deferred until
tab switch under main-thread load) and #1472 (background workspaces have dead PTYs).

**It is transient daemon contention, NOT a broken install.** What makes it WORSE: tight probe-loops and
spawning more workspaces (proven 2026-05-11 — 14 successive spawns turned a 1-min wedge into a 10-min freeze).

**Recovery (do exactly this, do NOT improvise a faster loop):**
1. Close the phantom: `cmux close-workspace --workspace workspace:N` (colon ref form, not bare `N`).
2. **Wait 30–60s** (idle, not faster probes).
3. Retry **once**, single-shot.
4. Still phantom? **Wait 5+ minutes** before the next attempt. The daemon recovers on its own given idle time.
5. After 2–3 patient retries over ~10 min, drop batch size (1 instead of 3 parallel).
6. **NEVER ask the user to relaunch cmux**, and never tight-loop.

## Failure mode 2 — broken-pipe / spawn wedge after the first op
**Symptom:** the **first** `new-workspace` of a session succeeds; every subsequent one fails with
`Error: Failed to write to socket (Broken pipe, errno 32)` for all retries (2026-05-19). The daemon can spawn
**one** workspace, then wedges for the rest of the session.

**What does NOT recover it:** 90s waits, 360s deep settles, spawning a probe workspace (it consumes the one
good slot), closing stale workspaces. **Only a daemon/process restart clears this wedge.**

**How to live with it:**
- For multi-spawn work (e.g. a multi-case CI runner with N>1 cases): treat **one spawn per session as the reliable
  budget.** Chunk N runs into N separate sessions, each preceded by a cmux restart.
- Don't burn the one good slot on a probe.

## Failure mode 3 — socket-pool starvation by an active Claude's hooks
**Symptom:** a `nohup`'d background path (e.g. `ci.sh`) consistently hits broken-pipe, while the **same command
run directly from the Bash tool works first try** (2026-05-14). Cause: an active Claude session's
`UserPromptSubmit`/`PreToolUse` hooks fire `cmux hooks` calls that starve the socket pool.

**Workaround:** invoke the work **directly from the Bash tool**, not via a `nohup`'d wrapper that races the
hooks. (Retry patches in the harness help but don't fully fix it — root cause is daemon socket-pool sizing.)

## Wrapper-pane pattern — run cmux ops from inside a healthy workspace
Claude's Bash tool has **no tty**, which aggravates contention for chained cmux ops. Instead of running a chain
of cmux commands directly from no-tty Bash, **send the work INTO a healthy workspace** and let it run there:
```bash
WS_OUT="$(cmux new-workspace 2>&1)"
WS="$(printf '%s' "$WS_OUT" | awk '{for(i=1;i<=NF;i++) if($i ~ /^workspace:[0-9]+$/) print $i}' | head -1)"
sleep 15                                           # generous settle before first send
cmux send --workspace "$WS" "echo probe-$$"; cmux send-key --workspace "$WS" enter
sleep 5
cmux read-screen --workspace "$WS" | tail          # confirm the probe echoed back = pty is live
cmux send --workspace "$WS" "bash /path/to/work.sh ARG..."; cmux send-key --workspace "$WS" enter
```

## Concurrency budget (this Mac)
- **≤3 concurrent** workspace spawns; **5–10s gaps** between sequential spawns.
- After a 3-parallel batch, let the daemon **rest 60–120s** before the next batch.
- Long sweeps: **one worker + one heavy resource (VM) at a time.** Serial by design.

## The targeting gotcha (also a "why did it hit my own pane" bug) — verified
`cmux` defaults `--workspace`/`--surface` to **your** session's `CMUX_WORKSPACE_ID`/`CMUX_SURFACE_ID`; short
refs are context-relative. **Always pass `--workspace <WS> --surface <S>` together** for another pane.
- **Verified:** `cmux rpc surface.read_text {"surface":"surface:N"}` targeting another pane returned **0** of that
  pane's content, while `cmux read-screen --workspace <WS> --surface <S>` returned it. Never use `rpc` for
  cross-pane reads — always `read-screen`.
- **Verified:** `close-workspace --workspace 14` (bare number) → `Error: Workspace index not found` (a bare
  number is read as a workspace *index*, not a ref). Use the **colon ref**: `close-workspace --workspace workspace:14`.

## Process isolation — don't kill the user's interactive sessions
A broad `pkill` once killed an unrelated interactive session as collateral. Hard rules:
- **NEVER** `pkill -f 'claude'`, `pkill -f 'claude --session-id'`, or `pkill -f 'tail.*'` — they match
  interactive sessions.
- Scope to the run path: `pkill -f 'your-ci-runner/runs/'`, `pkill -f 'orchestrate.sh.*<ticket>-'`, or a unique
  launch-flag combo. **`pgrep -f <pattern>` FIRST** to inspect matches; abort if anything non-CI appears.
- **Only `close-workspace` workspaces YOU spawned** (track their refs/UUIDs); never wildcard-close.

## Known upstream bugs (manaflow-ai/cmux)
- **#1900** — `new-workspace --command` uses send-text+Enter (not a real initial-command API); races with shell
  init. Prefer bare spawn + explicit `cmux send` for load-sensitive launches.
- **#2555** — new workspace's terminal doesn't render until tab switch (first Metal frame deferred under
  main-thread load) → the "Terminal N" phantom symptom.
- **#1472** — background workspaces can have dead PTYs; `read-screen`/`send-key` fail with "Surface not ready".

## Quick decision tree
1. Something failed → `cmux ping`. No `PONG`? daemon is down/restarting — wait, don't spam.
2. `PONG` but spawn gave a phantom → close it, wait 30–60s, retry **once**. Don't loop.
3. Broken-pipe on the 2nd+ spawn of the session → it's wedged; **restart cmux** or chunk into new sessions.
4. Background path fails but direct Bash works → socket-pool starvation; **run direct, not nohup'd.**
5. Targeted the wrong pane → you dropped `--workspace`; pair `--workspace`+`--surface`.

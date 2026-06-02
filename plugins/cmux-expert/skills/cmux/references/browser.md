# Browser automation — `cmux browser`

A full browser toolkit in cmux panes: navigate, interact via element refs, read content, debug errors,
persist sessions — all from the CLI. The engine is **WKWebView (Safari), not Chrome** — see Limits.

## The stable agent loop
Every interaction should follow this pattern — it's the most reliable way to automate:
```
navigate → verify URL → wait for load → snapshot → act → re-snapshot
```
```bash
cmux --json browser open https://example.com        # returns a surface ref, e.g. surface:7
cmux browser surface:7 get url                       # verify navigation (empty/about:blank → re-navigate)
cmux browser surface:7 wait --load-state complete --timeout-ms 15000
cmux browser surface:7 snapshot --interactive        # get element refs (e1, e2, …)
cmux browser surface:7 fill e1 "hello"               # act using refs
cmux --json browser surface:7 click e2 --snapshot-after   # act + re-snapshot in one call
```

## Opening
```bash
cmux --json browser open https://example.com                      # caller's workspace (uses CMUX_WORKSPACE_ID)
cmux --json browser open https://example.com --workspace workspace:2
cmux browser open-split https://example.com
```
Use `--json` to capture the surface ref. To reuse an existing browser surface, find it with
`cmux identify --json` or `cmux list-pane-surfaces`. Keep one `surface:N` per task unless you intentionally switch.

## Snapshots — your eyes on the page
Returns a text DOM tree with short refs (e1, e2, …) for interactive elements. **Prefer refs over CSS selectors.**
```bash
cmux browser surface:7 snapshot --interactive
cmux browser surface:7 snapshot --interactive --compact --max-depth 3     # large pages
cmux browser surface:7 snapshot --selector "form#checkout" --interactive  # scope, reduce noise
```
**Ref lifecycle:** refs are invalidated by any DOM change (navigation, modal open/close, AJAX). **Re-snapshot
after every mutating action.** A stale ref → `not_found`; the fix is always a fresh snapshot.

## Interacting (use bare ref IDs)
```bash
cmux browser surface:7 click e6           # ✅ bare ref. NOT click '[ref=e6]' / 'ref=e6' (both fail)
cmux browser surface:7 dblclick e8
cmux browser surface:7 hover e3
cmux browser surface:7 fill e10 "user@example.com"   # clears first
cmux browser surface:7 fill e11 ""                    # clear an input
cmux browser surface:7 type e10 "appended text"       # appends, fires key events
cmux browser surface:7 press "Enter"                  # or "Tab"
cmux browser surface:7 select e15 "option-value"
cmux browser surface:7 check e20      # / uncheck e20
cmux browser surface:7 scroll --dy 500
cmux browser surface:7 scroll --selector ".list" --dy 300
```
Add `--snapshot-after` to any mutating action to fold the re-snapshot into the same call.

## Navigation, waiting, reading
```bash
cmux browser surface:7 goto https://example.com/page2     # back | forward | reload
cmux browser surface:7 get url        # | title

cmux browser surface:7 wait --load-state complete --timeout-ms 15000
cmux browser surface:7 wait --selector "#results" --timeout-ms 10000
cmux browser surface:7 wait --text "Success" --timeout-ms 10000
cmux browser surface:7 wait --url-contains "/dashboard" --timeout-ms 15000

cmux browser surface:7 get text "#main-content"   # html | value | attr | count | box | styles
cmux browser surface:7 get attr "a.logo" "href"
cmux browser surface:7 get count ".search-result"
```
Typical timeouts: 15000ms general, 45000ms OAuth/redirect, 120000ms manual 2FA.

## JavaScript
```bash
cmux browser surface:7 eval "document.title"
cmux browser surface:7 eval "window.localStorage.getItem('token')"
```

## Debugging — console errors & warnings
`console list` / `errors list` capture only what fires *while the surface is active* — they routinely **miss
load-time errors and `window.onerror`.** Don't rely on them alone; install JS hooks, then trigger.
```bash
cmux browser surface:7 console list
cmux browser surface:7 errors list
```
**Thorough capture (recommended):** monkey-patch console + onerror, navigate/reload, then collect.
```bash
cmux browser surface:7 eval "(() => { window.__ce = []; window.__cw = []; const oe = console.error; const ow = console.warn; console.error = function() { window.__ce.push([...arguments].map(String).join(' ')); oe.apply(console, arguments); }; console.warn = function() { window.__cw.push([...arguments].map(String).join(' ')); ow.apply(console, arguments); }; window.onerror = function(msg, src, line, col) { window.__ce.push('Uncaught: ' + msg + ' at ' + src + ':' + line + ':' + col); }; window.onunhandledrejection = function(e) { window.__ce.push('Unhandled rejection: ' + String(e.reason)); }; return 'hooks installed'; })()"
cmux browser surface:7 goto http://localhost:8000
cmux browser surface:7 wait --load-state complete --timeout-ms 15000
cmux browser surface:7 eval "JSON.stringify({errors: window.__ce, warnings: window.__cw, errorCount: window.__ce.length, warningCount: window.__cw.length})"
```
**Interact to trigger latent errors:** an idle page may show 0 errors; click/navigate/trigger AJAX, *then*
re-collect — many warnings (APM, AG Grid sizing) only fire on use.

**Failed network requests:**
```bash
cmux browser surface:7 eval "JSON.stringify(performance.getEntriesByType('resource').filter(r => r.responseStatus >= 400).map(r => ({url: r.name, status: r.responseStatus})))"
```

## Authentication & session persistence
```bash
# Login → save state (cookies + localStorage + sessionStorage)
cmux --json browser open https://app.example.com/login
cmux browser surface:7 wait --load-state complete --timeout-ms 15000
cmux browser surface:7 snapshot --interactive
cmux browser surface:7 fill e1 "user@example.com"
cmux browser surface:7 fill e2 "$APP_PASSWORD"
cmux browser surface:7 click e3 --snapshot-after
cmux browser surface:7 wait --url-contains "/dashboard" --timeout-ms 20000
cmux browser surface:7 state save ./auth-state.json

# Restore later
cmux --json browser open https://app.example.com
cmux browser surface:8 state load ./auth-state.json
cmux browser surface:8 goto https://app.example.com/dashboard

# Cookie shortcut
cmux browser surface:7 cookies set "session_token=abc123xyz"
```
**Never commit state files — they contain auth tokens.** For 2FA, let the user complete it in the pane, then
`wait --url-contains "/dashboard" --timeout-ms 120000` and `state save`.

## Cookies, storage, tabs, dialogs, frames
```bash
cmux browser surface:7 cookies get | set "name=value; domain=example.com" | clear
cmux browser surface:7 storage local get "key" | set "key" "value"   # / storage session …
cmux browser surface:7 tab list | new "https://example.com" | switch 2 | close 1
cmux browser surface:7 dialog accept | accept "input" | dismiss
cmux browser surface:7 frame "#my-iframe" | frame main
```

## AG Grid — read via the internal API, never scrape the DOM
Virtual rendering leaves offscreen cells empty. Use the grid API through `eval`; `forEachNode()` first, fall
back to a `getModel().getRow(i)` loop if `forEachNode` yields 0 while `getRowCount() > 0`:
```javascript
var el = document.querySelector('.ag-root-wrapper');
var api = el.__agComponent.gridOptionsService.api;
var rows = [];
api.forEachNode(function(n){ if (n.data) rows.push(n.data); });
if (rows.length === 0) { for (var i=0;i<api.getModel().getRowCount();i++){ var n=api.getModel().getRow(i); if(n&&n.data) rows.push(n.data);} }
JSON.stringify(rows);
```

## Troubleshooting
- **`js_error` on snapshot/eval:** some pages reject the snapshot JS. Fall back to `get url` → `get text body`
  / `get html body`.
- **Stale refs / `not_found`:** re-snapshot.
- **Element not visible:** `wait --selector "#target"` → `scroll --dy 400` → re-snapshot.
- **Snapshot too noisy/truncated on big pages:** `--selector` to scope, or fall back to `get text/html body`.
- **AngularJS custom components** (e.g. a custom wrapper component with internal validators) have validators that programmatic
  `angular.element(el).scope()` changes don't satisfy. Simple text fields via scope work; for complex
  components, create data via Django shell instead of browser automation.

## WKWebView limits (return `not_supported` — need Chrome/CDP)
`viewport` (device emulation), `geolocation`, `offline`, `trace`/`screencast`, `network route/unroute`,
`input mouse/keyboard/touch` (raw injection). Use the high-level commands (`click`, `fill`, `press`, `scroll`,
`wait`, `snapshot`) instead.

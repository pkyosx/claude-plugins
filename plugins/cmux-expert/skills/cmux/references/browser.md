# Browser automation — `cmux browser`

A full browser toolkit in cmux panes: navigate, locate elements by ref **or** semantic locator, interact,
read, debug, and persist sessions — all from the CLI. The engine is **WKWebView (Safari), not Chrome** —
see Limits. Every command below is **verified against cmux 0.64.11**.

`cmux browser <surface> <subcommand> [args]` — the surface can be the first positional token
(`cmux browser surface:7 click e2`) or `--surface surface:7`. `open`/`open-split`/`new`/`identify` need no surface.
Add `--json` to get structured output (required to read back values — see below).

## The stable agent loop
```
navigate → verify URL → wait for load → snapshot → act → re-snapshot
```
```bash
cmux --json browser open https://example.com        # returns a surface ref, e.g. surface:7
cmux browser surface:7 get url                       # verify (empty/about:blank → re-navigate)
cmux browser surface:7 wait --load-state complete --timeout-ms 15000
cmux browser surface:7 snapshot --interactive        # element refs e1, e2, …
cmux browser surface:7 fill e1 "hello"
cmux --json browser surface:7 click e2 --snapshot-after   # act + re-snapshot in one call
```

## Surfaces = isolated sessions
Each browser surface is an **independent context**: its own cookies, localStorage/sessionStorage, tab list,
and navigation history. Open several for parallel isolated sessions; clean up with
`cmux close-surface --surface surface:7`. Keep **one task per surface** to avoid ref churn.
```bash
cmux --json browser open https://example.com                       # caller's workspace (CMUX_WORKSPACE_ID)
cmux --json browser open https://example.com --workspace workspace:2 --window window:1
cmux browser open-split https://example.com                        # open beside current pane
```
Reuse an existing surface found via `cmux identify --json` or `cmux list-pane-surfaces`.

## Snapshots — two modes
```bash
cmux browser surface:7 snapshot                       # FULL accessibility tree, every node gets a ref
cmux browser surface:7 snapshot --interactive         # ONLY actionable elements (links/inputs/buttons)
cmux browser surface:7 snapshot --interactive --compact --max-depth 3   # trim noise on big pages
cmux browser surface:7 snapshot --selector "form#checkout" --interactive # scope to a section
cmux browser surface:7 snapshot --interactive --cursor                  # include cursor/focus info
```
Output is a tree of `role "name" [ref=eN]`. **Prefer refs over CSS selectors.**
**Ref lifecycle:** refs are invalidated by any DOM change (navigation, modal, AJAX). **Re-snapshot after every
mutating action.** A stale ref → `not_found`; the fix is always a fresh snapshot.

## `find` — locate by semantic locator without a snapshot
`find` resolves a locator to a concrete `@eN` ref **plus** its CSS selector, tag, and text — no snapshot needed.
The returned `@eN` ref is a usable handle in `click`/`fill`/`get`/`is`.
```bash
cmux --json browser surface:7 find role link                 # by ARIA role
cmux --json browser surface:7 find role button --name "Save" --exact
cmux browser surface:7 find text "Sign in"                   # by visible text (add --exact for exact match)
cmux browser surface:7 find label "Email"                    # label | placeholder | alt | title | testid
cmux browser surface:7 find testid "submit-btn"
cmux browser surface:7 find first "a"                        # first|last <selector>
cmux browser surface:7 find nth 2 "li.item"                  # nth <index> <selector>
```
`--json` returns `{ ref:"@e8", element_ref, selector:"…css path…", tag, text, role, name, exact }`. Use the
`@eN` directly: `cmux browser surface:7 click @e8`. Great for stable targeting when you know a role/label/testid.

## Interacting
```bash
cmux browser surface:7 click e6           # bare ref (snapshot eN or find @eN). NOT '[ref=e6]'
cmux browser surface:7 dblclick e8
cmux browser surface:7 hover e3
cmux browser surface:7 focus e4
cmux browser surface:7 fill e10 "user@example.com"   # clears first;  fill e10 ""  to clear
cmux browser surface:7 type e10 "appended text"      # appends, fires key events
cmux browser surface:7 press Enter                    # press|key|keydown|keyup <key>   (Tab, Escape, ArrowDown…)
cmux browser surface:7 select e15 "option-value"
cmux browser surface:7 check e20      # / uncheck e20
cmux browser surface:7 scroll-into-view e22
cmux browser surface:7 scroll --dy 500               # --dx/--dy; --selector to scroll a container
```
Add `--snapshot-after` to any mutating action to fold the re-snapshot into the same call. Refs and CSS selectors
are interchangeable everywhere (`--selector` or bare positional).

## Navigate, wait, read
```bash
cmux browser surface:7 goto https://example.com/p2    # goto|navigate; back | forward | reload  (all take --snapshot-after)
cmux browser surface:7 get url        # | title    (get title is occasionally empty — fall back to eval "document.title")

cmux browser surface:7 wait --load-state complete --timeout-ms 15000   # interactive|complete
cmux browser surface:7 wait --selector "#results" --timeout-ms 10000
cmux browser surface:7 wait --text "Success" --timeout-ms 10000
cmux browser surface:7 wait --url-contains "/dashboard" --timeout-ms 15000   # or --url
cmux browser surface:7 wait --function "document.readyState === 'complete'" --timeout-ms 10000

cmux browser surface:7 get text "#main"            # text|html|value|count|box|styles
cmux browser surface:7 get attr "a.logo" --attr href
cmux browser surface:7 get styles "#submit" --property color
cmux --json browser surface:7 get box "#submit"    # {x,y,width,height,top,right,bottom,left}
cmux browser surface:7 is visible "#submit"        # is visible|enabled|checked  → 1 / 0
```
Typical timeouts: 15000ms general, 45000ms OAuth/redirect, 120000ms manual 2FA.

## JavaScript
```bash
cmux browser surface:7 eval "document.title"
cmux browser surface:7 eval "window.localStorage.getItem('token')"
cmux browser surface:7 addinitscript --script "<js>"   # runs on every new document, before page scripts
cmux browser surface:7 addscript --script "<js>"       # inject a script into the current page
cmux browser surface:7 addstyle  --css "body{outline:1px solid red}"
cmux browser surface:7 highlight "#target"             # visually flash an element
```
`eval` runs in the page; strict-CSP pages (e.g. GitHub) can reject it with `js_error` — fall back to `get text/html`.

## Debugging — console & errors (these DO capture runtime events in 0.64.11)
```bash
cmux browser surface:7 console list   # [error]/[warn]/[log] entries fired while the surface was active
cmux browser surface:7 errors list    # uncaught/thrown errors, e.g. "[error] Error: …"
cmux browser surface:7 console clear  # / errors clear
```
Verified: `console list` captures `console.error`/`console.warn`, and `errors list` captures thrown errors that
occur **while the surface is attached**. What they can still miss: errors fired during the very first page load
*before* the surface attached. For that, install capture hooks via `addinitscript` (runs before page scripts):
```bash
cmux browser surface:7 addinitscript --script "(() => { window.__ce=[]; const oe=console.error; console.error=function(){window.__ce.push([...arguments].map(String).join(' '));oe.apply(console,arguments)}; window.onerror=(m,s,l,c)=>window.__ce.push('Uncaught: '+m+' @'+s+':'+l); window.onunhandledrejection=e=>window.__ce.push('Rejection: '+String(e.reason)); })()"
cmux browser surface:7 reload
cmux browser surface:7 eval "JSON.stringify(window.__ce)"
```
Also interact (click/navigate) before re-checking — many warnings only fire on use, not at idle.
Failed requests (network.* is unsupported — see Limits) can be read from the page instead:
```bash
cmux browser surface:7 eval "JSON.stringify(performance.getEntriesByType('resource').filter(r=>r.responseStatus>=400).map(r=>({url:r.name,status:r.responseStatus})))"
```

## Reading values back → use `--json`
Several read commands print just `OK` without `--json`; add it to get the data:
```bash
cmux --json browser surface:7 cookies get                     # { cookies:[{name,value,domain,path,expires,secure,…}] }
cmux --json browser surface:7 storage local get --name token  # { key, value, type, … }
cmux --json browser surface:7 find role button --name Save     # { ref, selector, tag, text, … }
```
`cookies get` returns **all cookies in the surface's profile** unless scoped — pass `--url`/`--domain` to filter
(and be mindful it can surface tokens from other sites in the same profile).

## Authentication & session state
```bash
# Login, then persist (cookies + localStorage + sessionStorage + tab metadata)
cmux browser surface:7 snapshot --interactive
cmux browser surface:7 fill e1 "user@example.com"
cmux browser surface:7 fill e2 "$APP_PASSWORD"
cmux browser surface:7 click e3 --snapshot-after
cmux browser surface:7 wait --url-contains "/dashboard" --timeout-ms 20000
cmux browser surface:7 state save ./auth-state.json

# Restore on a fresh surface
cmux --json browser open https://app.example.com
cmux browser surface:8 state load ./auth-state.json
cmux browser surface:8 goto https://app.example.com/dashboard

# Cookie shortcut
cmux browser surface:7 cookies set --name session_token --value abc123 --url https://app.example.com
```
**Never commit state files — they contain auth tokens.** For 2FA, let the user complete it in the pane, then
`wait --url-contains "/dashboard" --timeout-ms 120000` and `state save`. Clear after sensitive work:
`cookies clear` + `rm` the state file.

### Profiles & import (persistent auth, or reuse a real browser's login)
```bash
cmux browser surface:7 profiles list                          # name + uuid; "default" is current
cmux browser profiles add work                                # add|rename|clear|delete
cmux browser import --from chrome --to-profile work --domain example.com   # import cookies/profile from Chrome/Safari
```
Profiles give a surface a durable cookie/storage context across runs (no re-login). `import` can pull an existing
browser's session — run with care (it copies real credentials).

## Cookies, storage, tabs, dialogs, frames, downloads, screenshots
```bash
cmux browser surface:7 cookies get|set|clear [--name --value --url --domain --path --expires --secure --all]
cmux browser surface:7 storage local|session get|set|clear [--name --value]
cmux browser surface:7 tab new <url> | list | switch <i> | close <i>     # (use --json to read the tab list)
cmux browser surface:7 dialog accept ["text"] | dismiss
cmux browser surface:7 frame main | frame --selector "#my-iframe"
cmux browser surface:7 download wait --path ./dl --timeout-ms 10000
cmux browser surface:7 screenshot --out /tmp/page.png        # writes PNG, prints "OK <path>"
```

## AG Grid — read via the internal API, never scrape the DOM
Virtual rendering leaves offscreen cells empty. Use the grid API through `eval`; `forEachNode()` first, fall
back to a `getModel().getRow(i)` loop if it yields 0 while `getRowCount() > 0`:
```javascript
var el = document.querySelector('.ag-root-wrapper');
var api = el.__agComponent.gridOptionsService.api;
var rows = [];
api.forEachNode(function(n){ if (n.data) rows.push(n.data); });
if (rows.length === 0) { for (var i=0;i<api.getModel().getRowCount();i++){ var n=api.getModel().getRow(i); if(n&&n.data) rows.push(n.data);} }
JSON.stringify(rows);
```

## Troubleshooting
- **`js_error` on snapshot/eval:** strict-CSP pages reject the injected JS. Fall back to `get url` → `get text body`
  / `get html body`; or navigate to a simpler intermediate page and retry.
- **Stale ref / `not_found`:** re-snapshot (or re-`find`).
- **Element not visible:** `wait --selector "#target"` → `scroll-into-view` (or `scroll --dy`) → re-snapshot.
- **Snapshot too noisy/truncated:** `--selector` to scope, `--compact --max-depth N`, or fall back to `get text/html body`.
- **A read command printed only `OK`:** add `--json` to get the value.
- **`get title` empty:** fall back to `eval "document.title"` or the snapshot's `document "…"` label.
- **AngularJS custom components** (custom wrapper components with internal validators) often ignore programmatic
  `angular.element(el).scope()` changes. Simple text fields via scope work; for complex components, create the data
  server-side instead of via browser automation.

## Limits — `not_supported` on WKWebView (verified 0.64.11)
These commands exist but return `not_supported: browser.<x> is not supported on WKWebView` (they need Chrome/CDP):
`viewport <w> <h>`, `geolocation <lat> <lon>`, `offline <bool>`, `trace start|stop`,
`network route|unroute|requests`, `screencast start|stop`, `input mouse|keyboard|touch`.
Use the high-level commands (`click`, `fill`, `press`, `scroll`, `wait`, `snapshot`, `find`) instead; for failed
requests read `performance.getEntriesByType('resource')` via `eval` (see Debugging).

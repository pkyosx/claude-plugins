#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""gen.py：缺口泳道圖（Gap Swimlane）產圖工具，只用 Python 標準庫。

用法（技能從使用者的專案資料夾執行，所以腳本一律用安裝路徑）：
  uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/gap-swimlane/scripts/gen.py" spec.json -o out.html
  uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/gap-swimlane/scripts/gen.py" spec.json --check
  uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/gap-swimlane/scripts/gen.py" spec.json -o shot.html --standalone dark

out.html 不含 doctype／html／head／body，直接當 Artifact 發佈；--standalone 另包一層，給 Chrome headless 截圖用。
spec 欄位見 references/spec-format.md。
"""
import argparse, html, json, sys, unicodedata
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
DATA_SLOT = "/*__GAP_SWIMLANE_DATA__*/null"

LABEL_W = 172
COL_X0 = 275
COL_W = 205
BOX_W, BOX_H = 172, 56
LANE_PAD = 18
DEFAULT_ROW_H = 84
RIGHT_PAD = 44

KINDS = {"normal", "fail", "risknode"}
ROUTES = {"auto", "straight", "vertical", "hv", "vh", "bus", "vhv"}
DEFAULT_LEDES = {
    "gaps": "每一項依序寫：改動前缺什麼、這次 PR 補了什麼、由哪支 PR 補、對應哪些 AC、依據。依據「確認」代表讀程式或留言原文確認，「推論」代表依程式或說明判斷、未經驗證。",
    "risks": "PR 合併後仍存在的狀況。圖上以紅色字母徽章或紅色虛線框標示。",
    "ext": "不是這次 PR 造成或遺留的問題，合併 PR 不會引入。圖上以灰色字母徽章標示，與紅色的剩餘風險區分。",
}


class SpecError(Exception):
    pass


def text_w(s, fs):
    w = 0.0
    for c in s:
        if unicodedata.east_asian_width(c) in "WF":
            w += fs
        elif c == " ":
            w += 0.3 * fs
        elif c in "il.,:;|!'()[]/-":
            w += 0.33 * fs
        elif c.isupper() or c.isdigit():
            w += 0.64 * fs
        else:
            w += 0.55 * fs
    return w


def col_x(i):
    return COL_X0 + i * COL_W


def ac_ref(a):
    """The id other entries use to point at an AC: 'AC-01', or 'SHOP-1 AC-01' when the AC names its ticket."""
    return f"{a['ticket']} {a['id']}" if a.get("ticket") else a["id"]


# ---------- 驗證 ----------
def validate(spec):
    errs = []

    def need(obj, key, where):
        if key not in obj or obj[key] in (None, ""):
            errs.append(f"{where}: 缺少必填欄位 '{key}'")
            return False
        return True

    for k in ("title", "summary", "note", "prs", "lanes", "nodes", "edges", "gaps"):
        need(spec, k, "spec")
    if errs:
        raise SpecError("\n".join(errs))

    ids = {}

    def claim(i, where):
        if i in ids:
            errs.append(f"{where}: id '{i}' 重複（已用於 {ids[i]}）")
        else:
            ids[i] = where

    tickets = []
    for j, t in enumerate(spec.get("tickets", [])):
        w = f"tickets[{j}]"
        for k in ("key", "title", "url"):
            need(t, k, w)
        if t.get("key") in tickets:
            errs.append(f"{w}: 票號 '{t.get('key')}' 重複")
        tickets.append(t.get("key"))
    multi = len(tickets) > 1

    pr_keys = set()
    for j, p in enumerate(spec["prs"]):
        w = f"prs[{j}]"
        for k in ("key", "name", "url", "base", "head"):
            need(p, k, w)
        if p.get("ticket") and p["ticket"] not in tickets:
            errs.append(f"{w}: ticket '{p['ticket']}' 不在 tickets 清單")
        if p.get("key") in pr_keys:
            errs.append(f"{w}: PR key '{p['key']}' 重複")
        pr_keys.add(p.get("key"))

    lanes = {}
    for j, L in enumerate(spec["lanes"]):
        w = f"lanes[{j}]"
        if need(L, "id", w):
            claim(L["id"], w)
            lanes[L["id"]] = L
        need(L, "name", w)
        r = L.get("rows", 1)
        if not isinstance(r, int) or r < 1:
            errs.append(f"{w}: rows 必須是 >= 1 的整數")

    ac_ids = []
    for j, a in enumerate(spec.get("acs", [])):
        w = f"acs[{j}]"
        if need(a, "id", w) and need(a, "text", w):
            if multi and not a.get("ticket"):
                errs.append(f"{w}: 多張票的 spec 裡，每條 AC 都要寫 ticket")
            if a.get("ticket") and a["ticket"] not in tickets:
                errs.append(f"{w}: ticket '{a['ticket']}' 不在 tickets 清單")
            ref = ac_ref(a)
            if ref in ac_ids:
                errs.append(f"{w}: AC '{ref}' 重複")
            ac_ids.append(ref)

    gap_ns = set()
    for j, g in enumerate(spec["gaps"]):
        w = f"gaps[{j}]"
        for k in ("n", "title", "before", "after", "prs"):
            need(g, k, w)
        n = g.get("n")
        if not isinstance(n, int):
            errs.append(f"{w}: n 必須是整數")
        elif n in gap_ns:
            errs.append(f"{w}: 缺口編號 {n} 重複")
        gap_ns.add(n)
        for p in g.get("prs", []):
            if p not in pr_keys:
                errs.append(f"{w}: prs 裡的 '{p}' 不在 prs 清單")
        for a in g.get("acs", []):
            if a not in ac_ids:
                errs.append(f"{w}: acs 裡的 '{a}' 不在頂層 acs 清單（多張票時寫成「票號 AC 編號」，例如 'SHOP-1 AC-01'）")
        for t in g.get("tickets", []):
            if t not in tickets:
                errs.append(f"{w}: tickets 裡的 '{t}' 不在頂層 tickets 清單")

    risk_keys = set()
    for sect in ("risks", "out_of_scope"):
        for j, r in enumerate(spec.get(sect, [])):
            w = f"{sect}[{j}]"
            for k in ("key", "title", "text", "basis"):
                need(r, k, w)
            if r.get("key") in risk_keys:
                errs.append(f"{w}: 風險字母 '{r.get('key')}' 重複（risks 與 out_of_scope 共用一組字母）")
            risk_keys.add(r.get("key"))
            inf = r.get("inf", False)
            if inf not in (True, False, "part"):
                errs.append(f"{w}: inf 只能是 true、false 或 \"part\"")

    pos = {}
    for j, n in enumerate(spec["nodes"]):
        w = f"nodes[{j}]"
        if need(n, "id", w):
            claim(n["id"], w)
            w = f"node '{n['id']}'"
        need(n, "title", w)
        if need(n, "lane", w) and n["lane"] not in lanes:
            errs.append(f"{w}: lane '{n['lane']}' 不存在（可用：{', '.join(lanes)}）")
        if "x" not in n and not isinstance(n.get("col"), int):
            errs.append(f"{w}: 需要整數 col（或手動指定 x）")
        row = n.get("row", 0)
        L = lanes.get(n.get("lane"))
        if "y" not in n and L and (not isinstance(row, int) or row < 0 or row >= L.get("rows", 1)):
            errs.append(f"{w}: row {row} 超出 lane '{L['id']}' 的 rows（{L.get('rows', 1)}）")
        if n.get("kind", "normal") not in KINDS:
            errs.append(f"{w}: kind '{n.get('kind')}' 不認得（可用：{', '.join(sorted(KINDS))}）")
        for g in n.get("gaps", []):
            if g not in gap_ns:
                errs.append(f"{w}: 缺口 {g} 沒有對應的 gaps 卡片")
        for r in n.get("risks", []):
            if r not in risk_keys:
                errs.append(f"{w}: 風險 '{r}' 沒有對應的 risks／out_of_scope 卡片")
        for a in n.get("acs", []):
            if a not in ac_ids:
                errs.append(f"{w}: acs 裡的 '{a}' 不在頂層 acs 清單（多張票時寫成「票號 AC 編號」，例如 'SHOP-1 AC-01'）")
        if n.get("inf", False) not in (True, False, "part"):
            errs.append(f"{w}: inf 只能是 true、false 或 \"part\"")
        key = (n.get("lane"), n.get("col"), n.get("row", 0), n.get("x"), n.get("y"))
        if key in pos:
            errs.append(f"{w}: 與 node '{pos[key]}' 位置相同")
        pos[key] = n.get("id")

    node_ids = {n.get("id") for n in spec["nodes"]}
    for j, e in enumerate(spec["edges"]):
        w = f"edges[{j}]"
        for end in ("from", "to"):
            if need(e, end, w) and e[end] not in node_ids:
                errs.append(f"{w}: {end} '{e[end]}' 不是任何 node 的 id")
        if e.get("route", "auto") not in ROUTES:
            errs.append(f"{w}: route '{e.get('route')}' 不認得（可用：{', '.join(sorted(ROUTES))}）")
        if e.get("label_anchor", "start") not in ("start", "middle", "end"):
            errs.append(f"{w}: label_anchor 只能是 start、middle 或 end")

    if errs:
        raise SpecError("\n".join(errs))


# ---------- 排版 ----------
def layout(spec):
    lanes, y = [], 0
    lane_idx = {}
    for i, L in enumerate(spec["lanes"]):
        rows = L.get("rows", 1)
        rh = L.get("row_height", DEFAULT_ROW_H)
        h = max(120, rows * rh + 2 * LANE_PAD)
        lanes.append({"id": L["id"], "name": L["name"], "sub": L.get("sub", []), "y": y, "h": h, "rows": rows, "rh": rh, "idx": i})
        lane_idx[L["id"]] = lanes[-1]
        y += h
    total_h = y

    nodes = []
    for n in spec["nodes"]:
        L = lane_idx[n["lane"]]
        x = n["x"] if "x" in n else col_x(n["col"])
        if "y" in n:
            ny = n["y"]
        else:
            inner = L["h"] - 2 * LANE_PAD
            used = L["rows"] * L["rh"]
            ny = L["y"] + LANE_PAD + (inner - used) / 2 + n.get("row", 0) * L["rh"] + L["rh"] / 2
        nodes.append({**n, "x": x, "y": ny})
    return lanes, lane_idx, nodes, total_h


def R(n): return [n["x"] + BOX_W / 2, n["y"]]
def Lf(n): return [n["x"] - BOX_W / 2, n["y"]]
def T(n): return [n["x"], n["y"] - BOX_H / 2]
def B(n): return [n["x"], n["y"] + BOX_H / 2]


def route_edge(e, a, b, lane_idx):
    r = e.get("route", "auto")
    if r == "auto":
        if abs(a["y"] - b["y"]) < 1:
            r = "straight"
        elif abs(a["x"] - b["x"]) < 1:
            r = "vertical"
        elif a["lane"] == b["lane"]:
            r = "bus"
        else:
            r = "hv"
    down = b["y"] > a["y"]
    right = b["x"] > a["x"]
    if r == "straight":
        if abs(a["y"] - b["y"]) >= 1:
            raise SpecError(f"edge {a['id']}→{b['id']}: route straight 只能用在同一列的兩個 node")
        pts = [R(a), Lf(b)] if right else [Lf(a), R(b)]
    elif r == "vertical":
        if abs(a["x"] - b["x"]) >= 1:
            raise SpecError(f"edge {a['id']}→{b['id']}: route vertical 只能用在同一欄的兩個 node")
        pts = [B(a), T(b)] if down else [T(a), B(b)]
    elif r == "hv":
        pts = [R(a) if right else Lf(a), [b["x"], a["y"]], T(b) if down else B(b)]
    elif r == "vh":
        pts = [B(a) if down else T(a), [a["x"], b["y"]], Lf(b) if right else R(b)]
    elif r == "bus":
        gap = COL_W - BOX_W
        bx = e.get("bus_x", b["x"] - BOX_W / 2 - gap / 2 if right else b["x"] + BOX_W / 2 + gap / 2)
        pts = [R(a) if right else Lf(a), [bx, a["y"]], [bx, b["y"]], Lf(b) if right else R(b)]
    else:  # vhv
        if "mid" in e:
            mid = e["mid"]
        else:
            L = lane_idx[b["lane"]]
            mid = L["y"] + 22 if down else L["y"] + L["h"] - 22
        pts = [B(a) if mid > a["y"] else T(a), [a["x"], mid], [b["x"], mid], T(b) if b["y"] > mid else B(b)]
    if "points" in e:
        pts = e["points"]
    return [[round(p[0], 1), round(p[1], 1)] for p in pts], r


def label_pos(e, pts, r):
    if "label_at" in e:
        return e["label_at"], e.get("label_anchor", "start")
    segs = list(zip(pts, pts[1:]))
    vert = [s for s in segs if abs(s[0][0] - s[1][0]) < 1 and abs(s[0][1] - s[1][1]) > 20]
    if r in ("vertical", "hv", "vh", "vhv") and vert:
        s = vert[-1] if r == "hv" else vert[0]
        return [s[0][0] + 8, round((s[0][1] + s[1][1]) / 2 + 4, 1)], "start"
    if r == "bus" and len(pts) == 4:
        # The column gap is narrower than any label, so a bus label sits beside its vertical
        # segment, just above the arrow into the target, on the side the edge comes from.
        bx, ty = pts[2]
        return [round(bx - 4, 1), round(ty - 6, 1)], "end" if pts[3][0] > bx else "start"
    s = segs[0]
    return [round((s[0][0] + s[1][0]) / 2, 1), round(s[0][1] - 7, 1)], "middle"


def lane_at(lanes, y):
    for L in lanes:
        if L["y"] <= y < L["y"] + L["h"]:
            return L
    return lanes[-1]


# ---------- 檢查 ----------
def box_of(n, pad=0):
    return (n["x"] - BOX_W / 2 - pad, n["y"] - BOX_H / 2 - pad, n["x"] + BOX_W / 2 + pad, n["y"] + BOX_H / 2 + pad)


def seg_hits_box(p, q, bx):
    x1, y1, x2, y2 = bx
    if abs(p[0] - q[0]) < 1:
        x = p[0]
        lo, hi = sorted((p[1], q[1]))
        return x1 < x < x2 and lo < y2 and hi > y1
    if abs(p[1] - q[1]) < 1:
        y = p[1]
        lo, hi = sorted((p[0], q[0]))
        return y1 < y < y2 and lo < x2 and hi > x1
    return False


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def check(nodes, edges):
    issues = []
    for n in nodes:
        if text_w(n["title"], 14.5) > BOX_W - 10:
            issues.append(f"node '{n['id']}': 標題「{n['title']}」太長，框內放不下，請縮短")
        if n.get("sub") and text_w(n["sub"], 12) > BOX_W - 12:
            issues.append(f"node '{n['id']}': 小字「{n['sub']}」太長，框內放不下，請縮短")
    labels = []
    for e in edges:
        ends = {e["from"], e["to"]}
        for p, q in zip(e["pts"], e["pts"][1:]):
            for n in nodes:
                if n["id"] in ends:
                    continue
                if seg_hits_box(p, q, box_of(n, 2)):
                    issues.append(f"edge {e['from']}→{e['to']}: 線穿過 node '{n['id']}'，請改 route、bus_x、mid 或節點位置")
        if e["label"]:
            w = text_w(e["label"], 12)
            x, y = e["lp"]
            x0 = {"start": x, "middle": x - w / 2, "end": x - w}[e["anchor"]]
            lb = (x0 - 2, y - 12, x0 + w + 2, y + 3)
            for n in nodes:
                if overlap(lb, box_of(n)):
                    issues.append(f"edge {e['from']}→{e['to']}: 標籤「{e['label']}」壓到 node '{n['id']}'，請用 label_at 移開")
            for other, ob in labels:
                if overlap(lb, ob):
                    issues.append(f"edge {e['from']}→{e['to']}: 標籤「{e['label']}」與「{other}」重疊，請用 label_at 移開")
            labels.append((e["label"], lb))
    return issues


# ---------- 組資料 ----------
def build(spec):
    validate(spec)
    lanes, lane_idx, nodes, total_h = layout(spec)
    by_id = {n["id"]: n for n in nodes}
    ac_order = [ac_ref(a) for a in spec.get("acs", [])]
    gap_acs = {g["n"]: g.get("acs", []) for g in spec["gaps"]}

    edges = []
    for e in spec["edges"]:
        a, b = by_id[e["from"]], by_id[e["to"]]
        pts, r = route_edge(e, a, b, lane_idx)
        label = e.get("label", "")
        lp, anchor = label_pos(e, pts, r) if label else ([0, 0], "start")
        edges.append({"from": e["from"], "to": e["to"], "pts": pts, "label": label, "lp": lp, "anchor": anchor,
                      "risk": bool(e.get("risk")), "on_b": lane_at(lanes, lp[1])["idx"] % 2 == 1})

    out_nodes = []
    for n in nodes:
        if "acs" in n:
            acs = list(n["acs"])
        else:
            acs = sorted({a for g in n.get("gaps", []) for a in gap_acs.get(g, [])}, key=ac_order.index)
        out_nodes.append({"id": n["id"], "x": n["x"], "y": round(n["y"], 1), "title": n["title"], "sub": n.get("sub", ""),
                          "kind": n.get("kind", "normal"), "gaps": n.get("gaps", []), "risks": n.get("risks", []),
                          "detail": n.get("detail", ""), "eng": n.get("eng", ""), "inf": n.get("inf", False), "acs": acs})

    max_x = max(n["x"] for n in nodes) + BOX_W / 2
    for e in edges:
        max_x = max(max_x, *(p[0] for p in e["pts"]))
        if e["label"]:
            w = text_w(e["label"], 12)
            right = {"start": e["lp"][0] + w, "middle": e["lp"][0] + w / 2, "end": e["lp"][0]}[e["anchor"]]
            max_x = max(max_x, right)
    svg_w = int(max_x + RIGHT_PAD)

    gaps = [{"n": g["n"], "title": g["title"], "before": g["before"], "before_basis": g.get("before_basis", ""),
             "before_inference": g.get("before_inference", ""), "before_note": g.get("before_note", ""),
             "after": g["after"], "prs": g["prs"], "acs": g.get("acs", []), "tickets": g.get("tickets", []),
             "eng": g.get("eng", "")} for g in spec["gaps"]]

    def risk(r, ext):
        return {"key": r["key"], "title": r["title"], "text": r["text"], "basis": r["basis"], "inf": r.get("inf", False),
                "eng": r.get("eng", ""), "ext": ext}

    data = {
        "title": spec["title"], "summary": spec["summary"], "note": spec["note"],
        "pr_status": spec.get("pr_status", "未合併"),
        "tickets": [{"key": t["key"], "title": t["title"], "url": t["url"]} for t in spec.get("tickets", [])],
        "prs": [{"key": p["key"], "name": p["name"], "short": p.get("short", ""), "url": p["url"], "base": p["base"], "head": p["head"],
                 "ticket": p.get("ticket", ""), "state": p.get("state", "")} for p in spec["prs"]],
        "acs": [{"ref": ac_ref(a), "id": a["id"], "ticket": a.get("ticket", ""), "text": a["text"]} for a in spec.get("acs", [])],
        "ledes": {k: spec.get("ledes", {}).get(k, v) for k, v in DEFAULT_LEDES.items()},
        "risk_note": spec.get("risk_note", ""),
        "limits": spec.get("limits", []),
        "box": {"w": BOX_W, "h": BOX_H},
        "svg": {"w": svg_w, "h": int(total_h), "label_w": LABEL_W},
        "lanes": [{"y": L["y"], "h": L["h"], "name": L["name"], "sub": L["sub"]} for L in lanes],
        "nodes": out_nodes, "edges": edges, "gaps": gaps,
        "risks": [risk(r, False) for r in spec.get("risks", [])],
        "ext": [risk(r, True) for r in spec.get("out_of_scope", [])],
    }
    return data, check(nodes, edges)


def render(data, standalone=None):
    tpl = TEMPLATE.read_text(encoding="utf-8")
    if DATA_SLOT not in tpl:
        raise SpecError(f"{TEMPLATE} 裡找不到資料插槽 {DATA_SLOT}")
    # "</" inside a JSON string would close the <script> block early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = tpl.replace("__TITLE__", html.escape(data["title"]), 1).replace(DATA_SLOT, payload, 1)
    if standalone:
        page = f'<!doctype html>\n<html lang="zh-Hant" data-theme="{standalone}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>\n{page}\n</body></html>\n'
    return page


def main():
    ap = argparse.ArgumentParser(description="缺口泳道圖：spec.json → 單一 HTML 頁面")
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", help="輸出的 HTML 路徑")
    ap.add_argument("--check", action="store_true", help="只驗證 spec 並檢查版面，不輸出")
    ap.add_argument("--standalone", choices=["light", "dark"], help="另包 doctype 與 data-theme，給截圖用")
    args = ap.parse_args()
    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as ex:
        print(f"讀不到 spec：{ex}", file=sys.stderr)
        return 2
    try:
        data, issues = build(spec)
    except SpecError as ex:
        print("spec 有錯誤：\n" + str(ex), file=sys.stderr)
        return 2
    for i in issues:
        print("版面：" + i)
    if not issues:
        print("OK")
    if args.check:
        return 1 if issues else 0
    if not args.out:
        print("沒有指定 -o 輸出路徑", file=sys.stderr)
        return 2
    Path(args.out).write_text(render(data, args.standalone), encoding="utf-8")
    print(f"已輸出 {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

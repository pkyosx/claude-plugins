---
name: gap-swimlane
description: "Draws a Jira ticket's PRs as a gap swimlane (缺口泳道圖) HTML page: the after-change flow, the gaps each PR fills, related AC and remaining risks. Use for 缺口泳道圖, gap swimlane, or picturing what a cross-service PR set changes. Not for plain flowcharts or for deciding whether a PR can be approved."
---

# gap-swimlane：缺口泳道圖

把一張 Jira 票的一支或多支 PR 畫成一頁缺口泳道圖，讓讀者不讀程式，就能從整條流程看出：PR 改了哪些步驟、補上哪些缺口、對應哪些 AC、還剩哪些風險。圖只畫改動後；帶綠色編號的節點是 PR 新增或修改的步驟，沒有編號的節點就是改動前已有、本票沒改的步驟，改動前的樣子寫在缺口卡片裡。

適合跨服務、流程有多個角色或系統的票，例如 review 前的理解、驗收前的影響評估、交接給新的接手者。只改一兩個檔案、沒有跨服務流程的 PR，直接讀 diff 比較快。這個技能不判斷 PR 能不能 approve。

- 產圖腳本：`${CLAUDE_PLUGIN_ROOT}/skills/gap-swimlane/scripts/gen.py`（只用 Python 標準庫，用 `uv run --script` 執行，不要改寫它）。版面、配色、深淺色、點選連動都在 `assets/template.html`，每張票只寫 spec JSON。
- spec 範例：`${CLAUDE_PLUGIN_ROOT}/skills/gap-swimlane/scripts/example-spec.json`，寫 spec 前先看一次。
- spec 欄位與排版選項：`references/spec-format.md`。
- 檔案位置：在目前的工作資料夾建 `gs/<票號>/`，研究筆記、spec 和輸出的 HTML 都放那裡，不要寫進 plugin 資料夾。

## 硬規則

- **只讀。** 不改任何 repo、不送 PR、不在 PR 或 Jira 留言、不啟動 sandbox 或測試站。疑點只回報給委託人。
- **版本識別。** 頁首寫每個 repo 改動前的 merge base SHA、改動後的 PR head SHA，以及 PR 是否已合併；PR 是 draft 或 CI 還在修時，`pr_status` 寫「SHA 可能更新」。PR 改版後頁面不會自動更新，要重跑；新 commit 只改測試或 lint、不影響流程時，只更新版本表與 `note`。
- **推論必須標示。** 每個缺口的改動前描述、每項風險，都標「確認」（讀程式或留言原文確認）、「推論」（附推論依據）或「部分推論」。讀者要靠這個標記決定能不能直接採信。
- **沒有實際執行驗證時**，`note` 開頭寫「**只讀程式與留言，未實際執行。**」。
- **寫給懂技術的 manager。** `title`、`sub`、`detail` 與卡片正文講功能、行為、影響與取捨；檔案路徑、函式名、commit 放在卡片的 `eng`（工程依據）。
- **缺口徽章只掛在 PR 實際修改的步驟。** 既有、沒被修改的步驟即使是缺口發生的位置也不掛，必要時在 `sub` 寫「既有流程，本票沒改」。掛錯會讓讀者以為本票新增了那個步驟。
- **帳號身分先查清楚。** 真人帳號貼出的 AI review 留言，寫成「某人的帳號貼出 AI review」，不寫成「AI review 帳號」。PR 只有 bot 與作者回覆、沒有人工 review 時，在 `note` 註明。
- **來源不一致時以 gh 與程式為準。** 實作者說明、PR 描述與 GitHub 現況（SHA、CI 狀態、驗證範圍）對不上時，採用可查證或較保守的說法，並把差異寫在 `note` 或對應卡片。

## 工作流程（每次都照這個順序）

1. **建立研究底稿。**
   - 讀 Jira：description、全部 comments、linked issues、refinement 頁面。找不到 refinement 頁時，在筆記寫明搜過哪些地方。
   - **多張票一起交付時**，每張票都照這一步讀一次，PR 清單逐張從 Development 欄位與 `gh search prs` 找齊，只算標題或描述第一行帶本組票號的 PR。另外讀這組功能在系統裡最接近的既有實作（同類觸發、事件、動作、畫面），逐項比對新功能有沒有照同一套做法；做法不同又沒有寫明理由的，列為剩餘風險。spec 的寫法見 `references/spec-format.md` 的「多張票」。
   - **抽出 AC 清單**：把票面 Acceptance Criteria 逐條抄進筆記，保留原編號（AC-01…）。之後寫進 spec 的 `acs`。
   - 讀每支 PR：描述、完整 diff、review 與 inline comments。`gh api` 讀清單一律加 `--paginate`，不加只拿到第一頁 30 筆，後面的留言會漏掉且不會有警告。
   - 用 merge base 讀改動前的程式（`git show <merge-base>:<path>` 或 `gh api .../contents?ref=<sha>`），不切 branch。
   - 筆記章節固定：需求摘要與 AC、各 PR 角色、改動前流程（每步標確認或推論）、改動後流程（每步標新增、修改、不變或刪除）、PR 補上的缺口（附對應 AC）、仍未補上的風險、範圍外的既有問題、未驗證事項。
   - 分流要讀到程式實際的判斷條件：可能是 HTTP 狀態碼、例外類型、資料有沒有變動、欄位有沒有宣告，或完全沒有分流。依實際條件畫分流節點，不要用常見寫法猜。
   - 實作者可以聯絡時，向實作者確認：目前的 PR 與 SHA、有沒有未 push 的改動、改動前後各兩三句、已知的剩餘風險與範圍外事項。實作者的說明在依據寫「實作者說明」；能從程式或留言確認的照常標「確認」。
2. **寫 spec。** 照 `references/spec-format.md`：
   - 一條泳道代表一個角色或系統（使用者、設定畫面、各個服務、背景工作、收件人）。
   - 節點用 `col` 表示先後；分流結果放在同一欄的不同 `row`，用 `bus` 扇出。
   - 每個缺口卡片寫：改動前缺什麼、PR 補了什麼、哪支 PR、對應 AC、依據。缺口與 AC 的關聯明確才填 `acs`，對應不上的留空，並在交付時列出。
   - 剩餘風險寫觸發條件；兩項風險相近時寫明差別。範圍外的既有問題寫明合併 PR 不會引入。
3. **產頁面並檢查。**
   ```bash
   uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/gap-swimlane/scripts/gen.py" "gs/<票號>/spec.json" --check
   uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/gap-swimlane/scripts/gen.py" "gs/<票號>/spec.json" -o "gs/<票號>/<票號>-gap-swimlane.html"
   ```
   有版面提示就調 `route`、`bus_x`、`mid`、`label_at` 或節點的 `col`／`row` 再跑，修到印出「OK」。再用 `--standalone light` 與 `--standalone dark` 各輸出一份，用 Chrome headless 截圖，親眼確認線沒有穿過不相干的框、字沒有被切掉：
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --virtual-time-budget=3000 --window-size=1600,1600 --screenshot="$PWD/gs/<票號>/light.png" "file://$PWD/gs/<票號>/light.html"
   ```
4. **發佈。** 輸出的 HTML 不含 doctype，可以直接發佈成 claude.ai Artifact；執行環境沒有 Artifact 時，交付 HTML 檔路徑。
5. **技術內容複核（不能省）。**
   - 請一位不是製作者的成員，對照程式與留言原文複核：改動前的描述、分流、確認或推論的標記、風險的觸發條件、缺口與 AC 的對應。實作者可以聯絡時，同時請實作者確認事實。
   - PR 還在改時，每輪複核前後都用 gh 重新核對各 PR 的 head；複核期間有新 commit 時，判斷是否影響圖上的缺口或風險（例如新 commit 修掉某項風險，就移到 `risk_note`），並更新版本表。
   - 依意見修正 spec、重產、重新發佈，直到複核者回覆不需要再修正。實際紀錄：三張票的複核各修正 7 到 15 項，例如分支條件畫得太窄、驗證範圍採用了過時的 PR 描述、改動前的原因寫錯、失敗分流誤寫成依 HTTP 狀態碼。複核抓到的幾乎都是內容錯誤，範本擋不住。
   - 沒有其他成員可以複核時，停在這一步，交付時寫明「尚未經獨立複核」，不要自己複核自己。

## 交付

用一段話把頁面連結交給委託人：PR 補上的主要缺口、最重要的剩餘風險（例如部署順序要求、可能重複寄信）、標為推論尚待確認的項目、沒有對應到缺口的 AC，以及是否已經獨立複核。發現的疑點只回報，是否轉給 PR 作者由委託人決定。

## 成本參考

| 工作 | token | 時間 |
|---|---|---|
| 研究底稿（三支 PR、跨三個 repo） | 約 18 萬到 28 萬 | 約 8 到 11 分鐘 |
| 寫 spec | 約 1.5 萬到 3 萬（估計） | 約 5 分鐘 |
| 每輪複核後修正 | 約 5 萬到 10 萬 | 約 3 到 5 分鐘 |

研究與複核是兩張票手畫時的實測，寫 spec 是依 spec 大小估計（手畫一張圖約 16 萬）。複核者的成本不在表內。交付時用這張表說明成本落在研究，不在畫圖。

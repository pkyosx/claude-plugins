# gap-swimlane

Draws one or more Jira tickets' PRs as a gap swimlane (缺口泳道圖) HTML page. The page shows the flow after the PRs merge; numbered badges mark the steps the PRs add or change, lettered badges mark remaining risks, and clicking a node opens a dialog with its detail, gaps, risks and related AC.

Write a JSON spec (lanes, nodes, edges, gaps, risks, AC), then:

```
python3 -I skills/gap-swimlane/scripts/gen.py spec.json -o page.html
```

The script validates the spec, lays out the diagram and prints `OK` when the layout check passes. `--standalone light|dark` writes a full HTML document for screenshots. See `skills/gap-swimlane/references/spec-format.md` for the spec and `skills/gap-swimlane/SKILL.md` for the research and review workflow.

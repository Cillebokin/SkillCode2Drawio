---
name: code-drawio-direct
description: Generate native .drawio files directly from code analysis without using Mermaid as an intermediate format. Use when Codex needs to inspect source code, functions, modules, routes, jobs, scripts, services, or execution paths and create draw.io flowcharts, control-flow diagrams, request workflows, error-path diagrams, or business logic diagrams as editable diagrams.net .drawio XML files.
---

# Code Draw.io Direct

## Overview

Use this skill to analyze code behavior and create an editable `.drawio` file directly. The reliable path is: inspect code, produce a small JSON diagram spec, then run `scripts/spec_to_drawio.py` to generate draw.io XML. The bundled generator supports multi-page diagrams, safe draw.io cell ids, orthogonal multi-segment routing, retry/loop back-edge detection, and lightweight same-rank ordering to reduce crossed lines. If the user asks for PNG, SVG, or PDF, export from the generated `.drawio` with draw.io Desktop while keeping the original `.drawio` file.

## Workflow

1. Define the requested code path: function, method, route, command, background job, module workflow, or cross-service operation.
2. Inspect the code before drawing. Prefer Serena symbol/references tools when available; use `rg` and focused file reads as fallback.
3. Extract a diagram spec grounded in the code:
   - entry point
   - major actions
   - validation and branch decisions
   - loops, retries, and error exits
   - external systems and side effects
   - return/success states
   - subflows that deserve their own page
4. Write a concise flow explanation based on the code. Cover the flow's purpose, main path, key branches, error exits, state changes, and important side effects.
5. Write the spec as JSON. See `references/drawio-spec.md` for the schema.
6. Run `scripts/spec_to_drawio.py` to create the `.drawio` file.
7. If the user requests PNG, SVG, or PDF, read `references/drawio-cli-export.md` and export with embedded diagram XML when supported.
8. If draw.io Desktop is available, optionally open the generated file for a quick visual check.
9. In the final response, list generated files, source files inspected, the concise flow explanation, and any uncertainty.

## File Locations

By default, generate files in the current working directory. If the user explicitly provides a directory or file path, use that path instead.

Default names:

```text
<flow-name>.drawio
<flow-name>.diagram.json
<flow-name>.summary.md    recommended for non-trivial flows
<flow-name>.drawio.png    optional export
<flow-name>.drawio.svg    optional export
<flow-name>.drawio.pdf    optional export
```

When the user provides a directory, keep all generated artifacts in that directory with the same default names. When the user provides a full output file path, write the `.drawio` file there and keep the JSON spec beside it unless the user requested otherwise.

Keep the JSON spec beside the `.drawio` file. The `.drawio` file is the editable diagram artifact; exported PNG/SVG/PDF files are presentation artifacts. Do not delete the `.drawio` file after export. For non-trivial flows, also keep a `.summary.md` file so readers can understand the diagram without re-reading the code.

## Flow Explanation

For every generated diagram, include a concise explanation grounded in the source code. Write this as final-response text for small flows and as `<flow-name>.summary.md` beside the generated `.drawio` file for non-trivial or multi-page flows.

Use this structure:

```markdown
# <Flow Name>

## Purpose
One or two sentences describing what this flow does in the system.

## Main Logic
Three to six bullets describing the normal path from entry to success.

## Key Branches
Bullets for important decisions, fallback paths, retry loops, and early exits.

## Side Effects
List writes to database, files, cache, network calls, UI state, device APIs, logs, or mutations.

## Failure Paths
List meaningful error returns, exceptions, rollback behavior, and recovery behavior.

## Source
List the files/functions used to derive the diagram.
```

Keep explanations short and factual. Do not restate every node. Explain what the diagram means and why each major path exists. Mark inferred behavior clearly.

## Generate Draw.io

Run the bundled script with the active Python. If no output path is provided, the `.drawio` file is written to the current working directory:

```powershell
python scripts/spec_to_drawio.py login-flow.diagram.json
```

When the user explicitly asks for a directory or file path, pass that path as the output argument:

```powershell
python scripts/spec_to_drawio.py login-flow.diagram.json path/to/login-flow.drawio
```

For stricter validation, add `--strict`. In strict mode, warnings are treated as errors and the output file is not written.

If plain `python` is unavailable, use the known local Python executable.

## Optional Export

Only export when the user asks for an image/document output or when a preview artifact is useful. Prefer:

```powershell
drawio -x -f png -e -b 10 -o login-flow.drawio.png login-flow.drawio
drawio -x -f svg -e -b 10 -o login-flow.drawio.svg login-flow.drawio
drawio -x -f pdf -e -b 10 -o login-flow.drawio.pdf login-flow.drawio
```

Use `-e` / `--embed-diagram` for PNG, SVG, and PDF so the exported file can be reopened in draw.io with editable XML. If the draw.io CLI is not on PATH, check `references/drawio-cli-export.md` for portable lookup rules and ask the user for their draw.io Desktop path if needed.

## Diagram Rules

- Generate native draw.io XML through the script; do not hand-write full `.drawio` XML unless the script cannot express the needed diagram.
- Use one diagram page per requested flow.
- Use orthogonal multi-segment connectors by default. Avoid straight diagonal connectors in code flowcharts because they often cross process nodes.
- Use decision nodes for meaningful branches: validation, permission checks, feature flags, retries, fallbacks, and errors.
- Label branch edges with the condition: `valid`, `invalid`, `exists`, `missing`, `retry`, `timeout`, `success`, `failure`.
- For retry, polling, state-machine, or loop-back edges, label the edge and add `"loop": true` when automatic back-edge detection might be ambiguous.
- Represent external systems explicitly: database, filesystem, HTTP API, queue, cache, OS/device API.
- Keep diagrams below roughly 25 nodes. Split larger flows into overview and child diagrams.
- Put complex subfunctions, retry loops, exception handling, state-machine details, and important domain workflows on separate draw.io pages when they would make the main page crowded.
- Mark inferred behavior in the final response; do not encode speculation as fact.
- Do not use online draw.io conversion as a required step; this skill must work in offline environments when Python and draw.io Desktop are available.

## Multi-Page Diagrams

Use multiple draw.io pages when a flow would exceed roughly 25 nodes, when a child function has meaningful internal branches, or when an important error/retry path deserves focused review.

Recommended page structure:

```text
Overview
<Important Subflow Name>
<Important Error or Retry Flow>
```

On the overview page, represent detailed child flows with `kind: "subflow"` nodes. Name the node with the same wording as the child page, for example `Validate order subflow`. The generated `.drawio` file can contain multiple sheets by using top-level `pages` in the JSON spec.

For multi-page diagrams, include a short section per page in the `.summary.md` file. Each section should explain that page's role and how it connects to the overview.

## Edge Routing

The generator defaults to draw.io orthogonal routing and automatically inserts waypoints for cross-layer, same-layer, and backward edges. Detected or explicitly marked loop-back edges are dashed and routed around the outside lane. For individual edges, use:

```json
{ "source": "a", "target": "b", "label": "retry", "route": "side" }
```

Use explicit loop marking when a retry or polling edge returns to an earlier logical step:

```json
{ "source": "increment_attempt", "target": "call_api", "label": "retry", "loop": true }
```

Supported edge route values:

```text
auto      default; orthogonal, with automatic waypoints when needed
side      force the edge to route around the outside lane
direct    no automatic waypoints; use only for short adjacent edges
```

If the automatic route is still visually poor, specify manual points:

```json
{
  "source": "validate",
  "target": "error",
  "label": "invalid",
  "points": [
    { "x": 360, "y": 300 },
    { "x": 620, "y": 300 }
  ]
}
```

Use manual `points` sparingly and keep them in the `.diagram.json` source so future updates preserve the intended route.

## Node Kinds

Supported `kind` values:

```text
start, end, process, decision, external, store, io, note
subflow
```

Use `process` by default. Use `external` for remote services, SDKs, operating-system APIs, and device capabilities. Use `store` for databases, files, caches, and durable state. Use `subflow` on overview pages to point to another draw.io page in the same file.

## Validation

Before finalizing:

- Check that the `.drawio` file exists and is non-empty.
- Confirm every edge references existing node ids.
- Confirm the flow starts at the correct entry point.
- Confirm success and error exits are represented.
- Confirm complex subfunctions are either summarized as `subflow` nodes or moved to separate pages.
- Confirm the flow explanation describes the diagram's purpose, main path, key branches, side effects, and failure paths.
- Confirm the XML has root cells `id="0"` and `id="1"`.
- Confirm every edge has a child `<mxGeometry relative="1" as="geometry" />`.
- Confirm non-adjacent, same-rank, and backward edges have orthogonal waypoints or `route: "side"` if they would otherwise cross nodes.
- Confirm retry, polling, and state-machine loop-back edges are visually dashed or explicitly marked with `"loop": true`.
- Do not add XML comments to generated draw.io XML.
- Ensure special characters in XML attributes are escaped by the generator, especially `&`, `<`, `>`, and `"`.
- Open the file in draw.io Desktop when practical.
- If the file opens blank, edges do not render, or export fails, read `references/drawio-troubleshooting.md`.


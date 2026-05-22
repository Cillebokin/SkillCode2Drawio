# Draw.io Diagram Spec

The bundled script converts a compact JSON spec into native draw.io XML.

## Minimal Example

```json
{
  "title": "Login Flow",
  "direction": "TD",
  "nodes": [
    { "id": "start", "label": "Login request", "kind": "start" },
    { "id": "validate", "label": "Validate credentials", "kind": "decision" },
    { "id": "session", "label": "Create session", "kind": "process" },
    { "id": "error", "label": "Return auth error", "kind": "end" },
    { "id": "success", "label": "Return success", "kind": "end" }
  ],
  "edges": [
    { "source": "start", "target": "validate" },
    { "source": "validate", "target": "session", "label": "valid" },
    { "source": "validate", "target": "error", "label": "invalid", "route": "side" },
    { "source": "session", "target": "success" }
  ]
}
```

## Top-Level Fields

- `title`: Diagram page name.
- `summary`: Optional concise text describing what the page or full diagram does. Keep detailed explanation in `<flow-name>.summary.md`.
- `direction`: `TD` for top-down or `LR` for left-right. Defaults to `TD`.
- `nodes`: Required list of nodes.
- `edges`: Required list of directed edges.
- `pages`: Optional top-level list for multi-page `.drawio` files. When present, each page uses the same fields as a single-page spec.

## Node Fields

- `id`: Required stable id. Use lowercase letters, digits, `_`, or `-`.
- `label`: Required visible text.
- `kind`: Optional. One of `start`, `end`, `process`, `decision`, `external`, `subflow`, `store`, `io`, `note`.
- `x`, `y`, `width`, `height`: Optional manual geometry. If omitted, the script auto-lays out nodes.

## Edge Fields

- `source`: Required source node id.
- `target`: Required target node id.
- `label`: Optional edge label.
- `route`: Optional. One of `auto`, `side`, or `direct`. Defaults to `auto`.
- `loop`: Optional boolean. Set `true` to force this edge to be treated as a loop-back edge.
- `points`: Optional explicit waypoint list. Each point may be `{ "x": 100, "y": 200 }` or `[100, 200]`.

## Edge Routing

The generator uses draw.io orthogonal routing by default:

```text
edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto
```

Default `auto` routing:

- adjacent forward edges use short orthogonal bends when source and target are not aligned
- same-level edges route through an outside lane
- backward or loop-back edges route through an outside lane and use dashed styling
- edges that skip ranks route through an outside lane

Use `route: "side"` when an edge should intentionally go around the outside of the diagram, such as retries, fallback jumps, cancellation, or error exits.

Use `loop: true` when an edge represents retry, polling, or state-machine return flow and should be handled as a back edge even if automatic detection is ambiguous:

```json
{ "source": "increment_attempt", "target": "call_api", "label": "retry", "loop": true }
```

Use `route: "direct"` only for short adjacent edges where a straight vertical or horizontal line is clearer.

Use `points` when exact routing matters:

```json
{
  "source": "retry",
  "target": "send",
  "label": "try again",
  "points": [
    { "x": 760, "y": 420 },
    { "x": 760, "y": 120 }
  ]
}
```

## Multi-Page Example

Use top-level `pages` when a child function or important branch deserves its own draw.io sheet:

```json
{
  "title": "Order Submit Flow",
  "summary": "Handles order submission by validating the order, persisting valid orders, and returning validation errors for invalid input.",
  "direction": "TD",
  "pages": [
    {
      "title": "Overview",
      "summary": "Shows the request-level order submission flow and delegates order validation details to a child page.",
      "nodes": [
        { "id": "start", "label": "Submit order request", "kind": "start" },
        { "id": "validate", "label": "Validate order subflow", "kind": "subflow" },
        { "id": "persist", "label": "Persist order", "kind": "store" },
        { "id": "end", "label": "Return response", "kind": "end" }
      ],
      "edges": [
        { "source": "start", "target": "validate" },
        { "source": "validate", "target": "persist", "label": "valid" },
        { "source": "persist", "target": "end" }
      ]
    },
    {
      "title": "Validate Order Subflow",
      "summary": "Checks stock and address validity before returning either a validation error or a valid result.",
      "nodes": [
        { "id": "start", "label": "Validate order", "kind": "start" },
        { "id": "stock", "label": "Stock available?", "kind": "decision" },
        { "id": "address", "label": "Address valid?", "kind": "decision" },
        { "id": "error", "label": "Return validation error", "kind": "end" },
        { "id": "ok", "label": "Return valid result", "kind": "end" }
      ],
      "edges": [
        { "source": "start", "target": "stock" },
        { "source": "stock", "target": "error", "label": "no", "route": "side" },
        { "source": "stock", "target": "address", "label": "yes" },
        { "source": "address", "target": "error", "label": "no", "route": "side" },
        { "source": "address", "target": "ok", "label": "yes" }
      ]
    }
  ]
}
```

Each page gets its own draw.io sheet. The script keeps single-page specs backward compatible.

## Authoring Rules

- Keep ids stable so future edits produce readable diffs.
- Avoid relying on raw ids in the generated `.drawio`; the generator prefixes draw.io cell ids as `n_*` and `e_*` to avoid collisions with JavaScript built-ins such as `sort`, `filter`, `map`, and `constructor`.
- Use branch labels for every decision edge.
- Use separate end nodes for materially different exits.
- Avoid duplicating implementation details in labels. Prefer behavior over raw function names unless the function name is the user-facing abstraction.
- Prefer `route: "side"` for error paths, retry paths, cross-rank jumps, and loop-back edges.
- Prefer `loop: true` for explicit retry, polling, and state-machine return edges when they are important to the code logic.
- Prefer a `subflow` node plus a child page for complex helper functions, nested workflows, and details that would crowd the overview.
- Include `summary` for every non-trivial page, but keep the full human-readable explanation in the companion `.summary.md`.
- Keep the JSON spec with the generated `.drawio` file.

## Validation Warnings

The generator prints warnings for ambiguous or weak specs, such as missing entry points, decision nodes with fewer than two outgoing edges, or isolated nodes. Add `--strict` to treat warnings as errors; in strict mode, the `.drawio` output is not written.

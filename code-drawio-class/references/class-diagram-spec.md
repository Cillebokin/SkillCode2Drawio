# Class Diagram Spec

The bundled script converts a compact JSON spec into native draw.io XML.

## Minimal Example

```json
{
  "title": "Order Model",
  "direction": "LR",
  "types": [
    {
      "id": "order",
      "name": "Order",
      "kind": "class",
      "namespace": "domain",
      "fields": [
        { "name": "id", "type": "OrderId", "visibility": "-" },
        { "name": "items", "type": "List<OrderItem>", "visibility": "-" }
      ],
      "methods": [
        { "name": "total", "returnType": "Money", "visibility": "+" }
      ]
    },
    {
      "id": "order_item",
      "name": "OrderItem",
      "kind": "class",
      "fields": [
        { "name": "sku", "type": "String" },
        { "name": "quantity", "type": "int" }
      ]
    }
  ],
  "relationships": [
    { "source": "order", "target": "order_item", "type": "composition", "label": "items", "targetMultiplicity": "*" }
  ]
}
```

## Multi-Page Example

Use top-level `pages` when several data-structure groups are unrelated but should be delivered as one `.drawio` file with multiple draw.io sheet tabs.

```json
{
  "title": "Project Data Structures",
  "pages": [
    {
      "title": "01 Core Model",
      "direction": "LR",
      "types": [
        { "id": "order", "name": "Order", "kind": "class" },
        { "id": "order_item", "name": "OrderItem", "kind": "class" }
      ],
      "relationships": [
        { "source": "order", "target": "order_item", "type": "composition", "label": "items" }
      ]
    },
    {
      "title": "02 UI State",
      "direction": "TD",
      "types": [
        { "id": "view_state", "name": "ViewState", "kind": "record" },
        { "id": "filter_state", "name": "FilterState", "kind": "dto" }
      ],
      "relationships": [
        { "source": "view_state", "target": "filter_state", "type": "association", "label": "filter" }
      ]
    }
  ]
}
```

A complete multi-page example is available at `references/example.multi-page.class-diagram.json`.

## Top-Level Fields

- `title`: Diagram page name for single-page specs; file-level title for multi-page specs.
- `summary`: Optional concise text describing the model.
- `direction`: `LR` or `TD`. Defaults to `LR`.
- `types`: Required list of type boxes for single-page specs.
- `relationships`: Optional list of edges.
- `pages`: Optional list of page specs. When present, each page becomes one draw.io sheet tab and top-level `types`/`relationships` are ignored.

## Page Fields

Each item in `pages` uses the same fields as a single-page spec:

- `title`: Required recommended page/sheet name. If omitted, the script uses `Page N`.
- `summary`: Optional concise text describing that page.
- `direction`: `LR` or `TD`. If omitted, it inherits top-level `direction` when present; otherwise defaults to `LR`.
- `types`: Required list of type boxes for that page.
- `relationships`: Optional list of edges for that page.

Relationships cannot cross pages. If the same type appears on multiple pages, repeat it with a stable id inside each page and keep relationships local to that page.

## Type Fields

- `id`: Required stable id. Use lowercase letters, digits, `_`, or `-`.
- `name`: Required visible type name.
- `kind`: Optional. One of `class`, `struct`, `interface`, `enum`, `record`, `type`, `dto`.
- `namespace`: Optional namespace/package/module text.
- `stereotype`: Optional custom stereotype such as `entity`, `value object`, or `service`.
- `fields`: Optional list of fields/properties.
- `methods`: Optional list of methods.
- `notes`: Optional list of short notes.
- `x`, `y`, `width`, `height`: Optional manual geometry.

If omitted, geometry is computed from actual box content. This is preferred for most diagrams because it prevents long field and method lists from overlapping neighboring boxes.

The generator estimates display width with East Asian wide/full-width characters counted wider than ASCII. This improves box sizing for Chinese names, fields, methods, and notes.

If manual `x`, `y`, `width`, or `height` values make boxes overlap, the script emits a warning. With `--strict`, overlap warnings fail generation before writing output.

## Field Items

Field items may be strings:

```json
"- items: List<OrderItem>"
```

or objects:

```json
{ "name": "items", "type": "List<OrderItem>", "visibility": "-", "static": false }
```

Visibility values:

```text
+ public
- private
# protected
~ package/internal
```

## Method Items

Method items may be strings:

```json
"+ total(): Money"
```

or objects:

```json
{
  "name": "total",
  "parameters": [],
  "returnType": "Money",
  "visibility": "+"
}
```

Method `parameters` may contain strings or objects. Object parameters are rendered as `name: type`, with optional defaults:

```json
{
  "name": "addItem",
  "parameters": [
    { "name": "sku", "type": "Sku" },
    { "name": "quantity", "type": "int", "default": "1" }
  ],
  "returnType": "void"
}
```

## Relationship Fields

- `source`: Required source type id.
- `target`: Required target type id.
- `type`: Optional. One of `inherits`, `implements`, `composition`, `aggregation`, `association`, `dependency`.
- `label`: Optional relationship label.
- `sourceMultiplicity`: Optional source multiplicity, such as `1`, `0..1`, `*`.
- `targetMultiplicity`: Optional target multiplicity.
- `route`: Optional. `auto` by default. `direct` may be requested, but the generator will only keep a direct line when it does not cross another type box.
- `points`: Optional explicit waypoint list.

## Relationship Semantics

- `inherits`: derived type points to base type.
- `implements`: concrete type points to interface/protocol.
- `composition`: owning/container type is the source; diamond appears on source side.
- `aggregation`: aggregate/container type is the source; hollow diamond appears on source side.
- `association`: stable field/property/reference.
- `dependency`: parameter/return/local-use/import-only relationship.

## Authoring Rules

- Prefer stable ids so regenerated diagrams produce readable diffs.
- Keep fields and methods short; summaries belong in companion markdown.
- Do not add every method by default. Include methods that reveal lifecycle, mutation, conversion, or domain behavior.
- Do not turn local variables into type boxes unless they are named data structures in the code.
- If ownership is unclear, use `association` and explain uncertainty in the summary.
- If a diagram has more than roughly 15 types or many crossing dependencies, split it into focused pages rather than forcing every type onto one page.
- Use separate `pages` for unrelated data-structure groups. Use an optional overview page only for high-level relationships that are actually present in code.
- Trust auto-routing first. It keeps direct lines when safe and falls back to orthogonal waypoints when a direct line would cross another type box.
- Use manual `points` only for exceptional edges after auto-routing.

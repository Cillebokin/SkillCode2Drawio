---
name: code-drawio-class
description: Generate native draw.io class diagrams and data-structure relationship diagrams from source-code analysis. Use when Codex needs to inspect classes, structs, interfaces, DTOs, enums, inheritance, composition, ownership, references, field types, method signatures, or data model relationships and create editable diagrams.net .drawio XML files without using Mermaid as an intermediate format.
---

# Code Draw.io Class

## Overview

Use this skill to analyze code data structures and create editable `.drawio` class diagrams directly. The reliable path is: inspect code, produce a compact class-diagram JSON spec, then run `scripts/class_spec_to_drawio.py` to generate native draw.io XML.

This skill is for structural diagrams, not runtime flowcharts. Use `code-drawio-direct` for control flow, request flow, retry paths, and business process diagrams.

## Workflow

1. Define the diagram scope: one type, a family of related types, a module, a DTO/model layer, or a bounded data structure. If the request contains multiple unrelated data-structure groups, create one draw.io page per group with top-level `pages`.
2. Inspect the code before drawing. Prefer CodeGraph or Serena for symbols, references, callers/callees, and file structure; use `rg` and focused file reads as fallback.
3. Extract only code-grounded structure:
   - class, struct, interface, enum, type alias, DTO, or record names
   - fields/properties and important types
   - important public methods or behavior-defining methods
   - inheritance and interface implementation
   - composition/aggregation/association/dependency relationships
   - ownership, lifecycle, containment, and multiplicity when evident
4. Exclude unrelated helper functions, temporary locals, UI wiring, and implementation details that do not clarify the data structure.
5. Write the spec as JSON. See `references/class-diagram-spec.md` for the schema.
6. Run `scripts/class_spec_to_drawio.py` to create the `.drawio` file.
7. If the user asks for PNG, SVG, or PDF, export from the generated `.drawio` with draw.io Desktop while keeping the original `.drawio` file.
8. In the final response, list generated files, source files inspected, the structural facts represented, and any uncertainty.

## File Locations

By default, generate files in the current working directory. If the user explicitly provides a directory or file path, use that path instead.

Default names:

```text
<diagram-name>.class-diagram.json
<diagram-name>.drawio
<diagram-name>.summary.md    recommended for non-trivial diagrams
<diagram-name>.drawio.png    optional export
<diagram-name>.drawio.svg    optional export
<diagram-name>.drawio.pdf    optional export
```

Keep the JSON spec beside the `.drawio` file. The `.drawio` file is the editable diagram artifact; exported PNG/SVG/PDF files are presentation artifacts.

## Diagram Content Rules

- Prefer data-structure truth over visual completeness. Do not invent relationships to make the diagram look symmetrical.
- Put the target type near the center/top and group related types around it.
- Use `kind: "struct"` for C/C++ structs and plain data aggregates; use `kind: "class"` for behavior-bearing classes.
- Include private fields only when they explain ownership, persistence, memory layout, or relationships.
- Include methods only when they define object lifecycle, mutation, conversion, or domain behavior. Do not list every getter/setter by default.
- Use relationships consistently:
  - `inherits`: class extends base class
  - `implements`: class implements interface/protocol
  - `composition`: source owns target strongly; target lifecycle depends on source
  - `aggregation`: source contains or references target as a part, but target can live independently
  - `association`: source has a stable field/property/reference to target
  - `dependency`: source uses target in parameters, return values, local calls, or construction without stable ownership
- Mark inferred relationships in the summary, not as definite labels in the diagram.
- Keep a single page under roughly 15 types. Split larger models into focused pages.
- For multiple unrelated class diagrams in one output file, use top-level `pages`; each page has its own `title`, `direction`, `types`, and `relationships`.

## Layout Rules

- Let `class_spec_to_drawio.py` auto-layout the diagram first. The generator uses actual class-box width and height, so fields/methods should not cause overlapping boxes.
- The generator estimates box width with East Asian wide/full-width characters counted wider than ASCII, so Chinese names and members should not be undersized.
- Multi-page specs are laid out independently per page. Do not rely on coordinates, ids, or relationships crossing between pages.
- Manual geometry is allowed, but overlapping type boxes produce warnings. With `--strict`, overlap warnings fail generation.
- The generator uses obstacle-aware relationship routing: it tries a direct line first, but only keeps it when the line does not cross any non-endpoint class box. If direct routing would cross a class box, it falls back to orthogonal routed waypoints.
- If a diagram still looks dense, reduce scope before adding manual coordinates. Prefer one target type plus first-degree dependencies, then create separate diagrams for second-degree dependency groups.
- Use explicit `x`, `y`, `width`, and `height` only when the automatic layout is not enough.
- Use explicit relationship `points` only for the few edges that still need manual routing after obstacle-aware auto-routing.
- Do not model every possible dependency in one page. For a central class with many referenced structs, group relationships by ownership, persistence, UI, algorithm, or serialization concern.

## Generate Draw.io

Run the bundled script with the active Python. If no output path is provided, the `.drawio` file is written to the current working directory:

```powershell
python scripts/class_spec_to_drawio.py order-model.class-diagram.json
```

For multiple unrelated class diagrams, put them in one JSON file under `pages`; the script writes one `.drawio` file with multiple draw.io sheet tabs:

```powershell
python scripts/class_spec_to_drawio.py project-structures.class-diagram.json project-structures.drawio
```

Use `references/example.multi-page.class-diagram.json` as the concrete multi-page JSON pattern.

When the user explicitly asks for a directory or file path, pass that path as the output argument:

```powershell
python scripts/class_spec_to_drawio.py order-model.class-diagram.json path/to/order-model.drawio
```

For stricter validation, add `--strict`. In strict mode, warnings are treated as errors and the output file is not written.

If plain `python` is unavailable, use the known local Python executable.

## Recommended Prompt

```text
Use CodeGraph or Serena to analyze <target type/module> and then use code-drawio-class to generate a native draw.io class diagram.

Requirements:
- inspect the actual code before drawing;
- include only confirmed classes, structs, fields, methods, and relationships;
- distinguish ownership/composition from ordinary references;
- generate .class-diagram.json and .drawio;
- if no output path is specified, generate files in the current directory.
```

## Validation

Before finalizing:

- Confirm every relationship references existing type ids.
- For multi-page specs, confirm each relationship references type ids from the same page only.
- Confirm the diagram uses class/struct/interface/enum boxes, not flowchart nodes.
- Confirm inheritance and implementation arrows point from derived/concrete type to base/interface type.
- Confirm composition/aggregation diamonds are on the owning/container side.
- Confirm no unrelated helper functions or transient locals are represented as types.
- Run `--strict` when practical so unknown kinds, ambiguous ownership labels, and overlapping boxes are caught before delivery.
- Confirm the generated `.drawio` file exists and is non-empty.
- Confirm root cells `id="0"` and `id="1"` exist.
- Open the file in draw.io Desktop when practical.

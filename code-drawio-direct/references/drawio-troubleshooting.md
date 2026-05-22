# Draw.io Troubleshooting

Use this when generated `.drawio` files do not open correctly, open blank, lose edges, or fail export.

## Common Problems

| Problem | Likely Cause | Fix |
| --- | --- | --- |
| File opens blank | Missing root cells `id="0"` and `id="1"` | Ensure the draw.io root has both cells and diagram cells use `parent="1"` |
| Edges do not render | Edge cell is self-closing or lacks geometry | Add child `<mxGeometry relative="1" as="geometry" />` to every edge |
| Edges are straight diagonal lines | Missing orthogonal edge style | Use `edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto` |
| Edges cross process nodes | No waypoint or poor automatic route | Add `route: "side"` or explicit `points` in the `.diagram.json` edge |
| Retry or polling edge is not shown as a loop | Automatic back-edge detection did not match the intended code semantics | Add `"loop": true` to that edge and regenerate |
| Loading fails with `setId is not a function` | Cell ids collide with JavaScript prototype or built-in method names, such as `sort`, `filter`, `map`, `constructor`, or `toString` | Regenerate with `spec_to_drawio.py`; it prefixes generated ids as `n_*` and `e_*` |
| draw.io reports corrupt XML | Unescaped XML special characters | Escape `&`, `<`, `>`, and `"` in attribute values |
| XML parser fails | XML comments or invalid comment content | Do not include any XML comments in generated draw.io XML |
| Export command not found | draw.io Desktop is not on PATH | Use a full executable path or keep the `.drawio` file |
| Exported image is not editable | Missing `-e` / `--embed-diagram` | Re-export PNG/SVG/PDF with `-e` |
| Output file missing | Wrong path or blocked GUI export | Print absolute input/output paths and keep `.drawio` |
| Expected child flow is not a new sheet | Spec used one page instead of top-level `pages` | Move overview and child flow into separate objects under `pages` |
| `--strict` returns exit code 1 | The spec produced validation warnings | Fix the warnings or rerun without `--strict` if the warning is acceptable |

## Required XML Shape

The generated `.drawio` XML should include:

```xml
<mxfile>
  <diagram>
    <mxGraphModel>
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

All visible cells should use `parent="1"` unless the diagram intentionally uses layers or containers.

## Edge Shape

Edges should look like:

```xml
<mxCell id="edge_1" value="valid" style="endArrow=block;html=1;" edge="1" parent="1" source="start" target="next">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

Do not write edge cells as self-closing elements.

#!/usr/bin/env python3
"""Convert compact code-flow JSON specs into native draw.io .drawio files.

The generator is intentionally dependency-free so it works offline. It includes
back-edge detection for loops/retries, a lightweight barycenter ordering pass to
reduce edge crossings, orthogonal waypoint routing, multi-page support, and
safe draw.io cell id prefixing.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path


NODE_STYLES = {
    "start": "ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
    "end": "ellipse;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;",
    "process": "rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "decision": "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
    "external": "rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#e1d5e7;strokeColor=#9673a6;",
    "subflow": "rounded=1;whiteSpace=wrap;html=1;strokeWidth=2;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;",
    "store": "shape=cylinder;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#f5f5f5;strokeColor=#666666;",
    "io": "shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
    "note": "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;darkOpacity=0.05;fillColor=#fff2cc;strokeColor=#d6b656;",
}

EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
    "html=1;endArrow=block;strokeWidth=1.5;"
)

# Back edges get a dashed style to visually distinguish loop-backs.
BACK_EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
    "html=1;endArrow=block;strokeWidth=1.5;dashed=1;dashPattern=6 4;"
)


def safe_mx_id(raw: str, prefix: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", str(raw).strip())
    if not value:
        value = uuid.uuid4().hex[:8]
    if value in {"0", "1"} or not re.match(r"^[A-Za-z_]", value):
        value = f"{prefix}_{value}"
    if not value.startswith(f"{prefix}_"):
        value = f"{prefix}_{value}"
    return value


def unique_mx_id(raw: str, prefix: str, used_ids: set[str]) -> str:
    base = safe_mx_id(raw, prefix)
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# Back-edge detection
# ---------------------------------------------------------------------------

def find_back_edges(nodes: list[dict], edges: list[dict]) -> set[tuple[str, str]]:
    """Detect back edges using DFS coloring.

    A back edge is one whose target is currently on the DFS stack (i.e. a
    GRAY ancestor). These are the edges that close loops in the graph.
    Edges flagged with "loop": true are also treated as back edges so authors
    can override detection if needed.
    """
    graph: dict[str, list[str]] = defaultdict(list)
    explicit_loops: set[tuple[str, str]] = set()
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        graph[source].append(target)
        if edge.get("loop") is True:
            explicit_loops.add((source, target))

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {str(n["id"]): WHITE for n in nodes}
    back_edges: set[tuple[str, str]] = set()

    def visit(u: str) -> None:
        color[u] = GRAY
        for v in graph.get(u, []):
            if color.get(v) == GRAY:
                back_edges.add((u, v))
            elif color.get(v) == WHITE:
                visit(v)
        color[u] = BLACK

    # Iterative DFS would be safer for very deep graphs, but flowcharts
    # rarely exceed a few dozen nodes so recursion is fine here.
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))
    for node in nodes:
        node_id = str(node["id"])
        if color[node_id] == WHITE:
            visit(node_id)

    return back_edges | explicit_loops


# ---------------------------------------------------------------------------
# Rank assignment (ignoring back edges)
# ---------------------------------------------------------------------------

def compute_ranks(
    nodes: list[dict],
    edges: list[dict],
    back_edges: set[tuple[str, str]],
) -> dict[str, int]:
    ids = [str(node["id"]) for node in nodes]
    outgoing: dict[str, list[str]] = defaultdict(list)
    indegree = {node_id: 0 for node_id in ids}

    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        if (source, target) in back_edges:
            continue  # skip back edges so the DAG is acyclic
        if source in indegree and target in indegree:
            outgoing[source].append(target)
            indegree[target] += 1

    queue = deque([node_id for node_id in ids if indegree[node_id] == 0])
    if not queue and ids:
        queue.append(ids[0])

    rank = {node_id: 0 for node_id in ids}
    visited: set[str] = set()
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for target in outgoing[current]:
            rank[target] = max(rank[target], rank[current] + 1)
            indegree[target] -= 1
            if indegree[target] <= 0:
                queue.append(target)

    # Any node still unreached after removing back edges (rare, e.g. an
    # isolated SCC with no entry) is placed below the rest.
    if any(node_id not in visited for node_id in ids):
        fallback_rank = max(rank.values(), default=0) + 1
        for node_id in ids:
            if node_id not in visited:
                rank[node_id] = fallback_rank

    return rank


# ---------------------------------------------------------------------------
# Barycenter ordering within each rank
# ---------------------------------------------------------------------------

def compute_rank_order(
    nodes: list[dict],
    edges: list[dict],
    rank: dict[str, int],
    back_edges: set[tuple[str, str]],
    iterations: int = 4,
) -> dict[str, int]:
    """Return a per-rank ordering index using the barycenter heuristic.

    For each node we compute the average position of its predecessors (or
    successors on reverse passes) and resort the rank by that value. Multiple
    iterations of forward + reverse sweeps converge on a layout with fewer
    edge crossings and straighter main paths.
    """
    ids = [str(node["id"]) for node in nodes]
    by_rank: dict[int, list[str]] = defaultdict(list)
    for node_id in ids:
        by_rank[rank[node_id]].append(node_id)

    # Initial order: keep the JSON-declared order so the author has some
    # influence over otherwise-symmetric cases.
    order: dict[str, int] = {}
    for level in by_rank:
        for idx, node_id in enumerate(by_rank[level]):
            order[node_id] = idx

    forward_parents: dict[str, list[str]] = defaultdict(list)
    forward_children: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        if (source, target) in back_edges:
            continue
        forward_parents[target].append(source)
        forward_children[source].append(target)

    def sort_level(level_ids: list[str], neighbors: dict[str, list[str]]) -> list[str]:
        def key(node_id: str) -> tuple[float, int]:
            neighbor_orders = [order[n] for n in neighbors.get(node_id, []) if n in order]
            if neighbor_orders:
                barycenter = sum(neighbor_orders) / len(neighbor_orders)
            else:
                # Nodes without relevant neighbors keep their current slot so
                # they don't drift unpredictably.
                barycenter = float(order[node_id])
            return (barycenter, order[node_id])
        return sorted(level_ids, key=key)

    levels_sorted = sorted(by_rank)

    for _ in range(iterations):
        # Forward sweep: align with parents.
        for level in levels_sorted[1:]:
            reordered = sort_level(by_rank[level], forward_parents)
            by_rank[level] = reordered
            for idx, node_id in enumerate(reordered):
                order[node_id] = idx
        # Reverse sweep: align with children so symmetric cases settle.
        for level in reversed(levels_sorted[:-1]):
            reordered = sort_level(by_rank[level], forward_children)
            by_rank[level] = reordered
            for idx, node_id in enumerate(reordered):
                order[node_id] = idx

    return order


# ---------------------------------------------------------------------------
# Geometry layout
# ---------------------------------------------------------------------------

def compute_layout(
    nodes: list[dict],
    edges: list[dict],
    direction: str,
) -> tuple[dict[str, tuple[int, int]], dict[str, int], set[tuple[str, str]]]:
    back_edges = find_back_edges(nodes, edges)
    rank = compute_ranks(nodes, edges, back_edges)
    order = compute_rank_order(nodes, edges, rank, back_edges)

    ids = [str(node["id"]) for node in nodes]
    by_rank: dict[int, list[str]] = defaultdict(list)
    for node_id in ids:
        by_rank[rank[node_id]].append(node_id)
    # Re-sort each rank using the final order computed above.
    for level in by_rank:
        by_rank[level].sort(key=lambda nid: order[nid])

    # Centering: for each rank, shift the row so its midpoint lines up with
    # the widest rank's midpoint. This makes the main path read as a column.
    max_per_rank = max((len(group) for group in by_rank.values()), default=1)

    positions: dict[str, tuple[int, int]] = {}
    for level, group in by_rank.items():
        # Offset to center this rank relative to the widest rank.
        leading = (max_per_rank - len(group)) / 2.0
        for index, node_id in enumerate(group):
            slot = leading + index
            if direction == "LR":
                positions[node_id] = (80 + level * 280, int(80 + slot * 150))
            else:
                positions[node_id] = (int(80 + slot * 260), 80 + level * 150)
    return positions, rank, back_edges


def diagram_bounds(geometries: dict[str, dict[str, int]]) -> dict[str, int]:
    left = min(geometry["x"] for geometry in geometries.values())
    top = min(geometry["y"] for geometry in geometries.values())
    right = max(geometry["x"] + geometry["width"] for geometry in geometries.values())
    bottom = max(geometry["y"] + geometry["height"] for geometry in geometries.values())
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def normalize_points(raw_points: object) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    if not isinstance(raw_points, list):
        return points
    for point in raw_points:
        if isinstance(point, dict):
            points.append((int(point["x"]), int(point["y"])))
        elif isinstance(point, list) and len(point) == 2:
            points.append((int(point[0]), int(point[1])))
        else:
            raise ValueError(f"invalid edge point: {point!r}")
    return points


def auto_edge_points(
    edge: dict,
    geometries: dict[str, dict[str, int]],
    ranks: dict[str, int],
    bounds: dict[str, int],
    direction: str,
    index: int,
    is_back_edge: bool,
) -> list[tuple[int, int]]:
    route = str(edge.get("route", "auto")).lower()
    if route in {"direct", "straight", "none"} and not is_back_edge:
        return []

    source = str(edge["source"])
    target = str(edge["target"])
    source_geometry = geometries[source]
    target_geometry = geometries[target]
    source_rank = ranks.get(source, 0)
    target_rank = ranks.get(target, 0)
    rank_gap = target_rank - source_rank

    source_cx = source_geometry["x"] + source_geometry["width"] // 2
    source_cy = source_geometry["y"] + source_geometry["height"] // 2
    source_right = source_geometry["x"] + source_geometry["width"]
    source_bottom = source_geometry["y"] + source_geometry["height"]
    source_left = source_geometry["x"]
    source_top = source_geometry["y"]

    target_cx = target_geometry["x"] + target_geometry["width"] // 2
    target_cy = target_geometry["y"] + target_geometry["height"] // 2
    target_left = target_geometry["x"]
    target_top = target_geometry["y"]
    target_right = target_geometry["x"] + target_geometry["width"]
    target_bottom = target_geometry["y"] + target_geometry["height"]

    lane_offset = 90 + (index % 4) * 36

    # Back edges always route around the outside lane so the loop arrow
    # reads as a clear "return to earlier step" path.
    if is_back_edge:
        if direction == "LR":
            lane_y = bounds["top"] - lane_offset
            return [
                (source_cx, source_top - 20),
                (source_cx, lane_y),
                (target_cx, lane_y),
                (target_cx, target_bottom + 20),
            ]
        else:
            lane_x = bounds["right"] + lane_offset
            return [
                (source_right + 20, source_cy),
                (lane_x, source_cy),
                (lane_x, target_cy),
                (target_right + 20, target_cy),
            ]

    if direction == "LR":
        if route in {"side", "around"} or rank_gap != 1:
            lane_y = bounds["bottom"] + lane_offset
            return [
                (source_right + 40, source_cy),
                (source_right + 40, lane_y),
                (target_left - 40, lane_y),
                (target_left - 40, target_cy),
            ]

        if abs(source_cy - target_cy) < 8:
            return []

        mid_x = source_right + max(40, (target_left - source_right) // 2)
        return [(mid_x, source_cy), (mid_x, target_cy)]

    if route in {"side", "around"} or rank_gap != 1:
        lane_x = bounds["right"] + lane_offset
        source_lane_y = source_bottom + 40
        target_lane_y = target_top - 40
        return [
            (source_cx, source_lane_y),
            (lane_x, source_lane_y),
            (lane_x, target_lane_y),
            (target_cx, target_lane_y),
        ]

    if abs(source_cx - target_cx) < 8:
        return []

    mid_y = source_bottom + max(40, (target_top - source_bottom) // 2)
    return [(source_cx, mid_y), (target_cx, mid_y)]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_spec(spec: dict) -> list[str]:
    """Validate the spec, raising on hard errors and returning warnings."""
    warnings: list[str] = []

    if not isinstance(spec.get("nodes"), list) or not spec["nodes"]:
        raise ValueError("spec must contain a non-empty nodes list")
    if not isinstance(spec.get("edges", []), list):
        raise ValueError("edges must be a list")

    seen = set()
    node_kinds: dict[str, str] = {}
    for node in spec["nodes"]:
        node_id = node.get("id")
        if not node_id:
            raise ValueError("every node needs an id")
        if node_id in seen:
            raise ValueError(f"duplicate node id: {node_id}")
        seen.add(node_id)
        if not node.get("label"):
            raise ValueError(f"node {node_id} needs a label")
        node_kinds[node_id] = str(node.get("kind", "process")).lower()

    indegree: dict[str, int] = {nid: 0 for nid in seen}
    outdegree: dict[str, int] = {nid: 0 for nid in seen}
    for edge in spec.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if source not in seen:
            raise ValueError(f"edge source not found: {source}")
        if target not in seen:
            raise ValueError(f"edge target not found: {target}")
        outdegree[source] += 1
        indegree[target] += 1

    # Soft lints (warnings only)
    has_start_kind = any(kind == "start" for kind in node_kinds.values())
    if not has_start_kind:
        no_input = [nid for nid, deg in indegree.items() if deg == 0]
        if not no_input:
            warnings.append("no start node and every node has an incoming edge; entry point is ambiguous")

    for node_id, kind in node_kinds.items():
        if kind == "decision" and outdegree[node_id] < 2:
            warnings.append(f"decision node '{node_id}' has fewer than 2 outgoing edges")
        if kind != "end" and outdegree[node_id] == 0 and indegree[node_id] == 0:
            warnings.append(f"node '{node_id}' is isolated (no edges)")

    return warnings


def add_geometry(parent: ET.Element, x: int, y: int, width: int, height: int) -> None:
    ET.SubElement(
        parent,
        "mxGeometry",
        {
            "x": str(x),
            "y": str(y),
            "width": str(width),
            "height": str(height),
            "as": "geometry",
        },
    )


def normalize_pages(spec: dict) -> list[dict]:
    pages = spec.get("pages")
    if pages is None:
        return [spec]
    if not isinstance(pages, list) or not pages:
        raise ValueError("pages must be a non-empty list")

    default_direction = spec.get("direction")
    normalized: list[dict] = []
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise ValueError(f"page {index} must be an object")
        page_spec = dict(page)
        if "title" not in page_spec:
            page_spec["title"] = page_spec.get("name", f"Page {index}")
        if "direction" not in page_spec and default_direction is not None:
            page_spec["direction"] = default_direction
        normalized.append(page_spec)
    return normalized


def add_diagram(mxfile: ET.Element, spec: dict) -> list[str]:
    warnings = validate_spec(spec)
    direction = str(spec.get("direction", "TD")).upper()
    if direction not in {"TD", "LR"}:
        direction = "TD"

    diagram = ET.SubElement(
        mxfile,
        "diagram",
        {"id": uuid.uuid4().hex[:12], "name": str(spec.get("title", "Code Flow"))},
    )
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": "1200",
            "dy": "800",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": "1169",
            "pageHeight": "827",
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    used_cell_ids = {"0", "1"}
    node_id_map: dict[str, str] = {}
    node_geometries: dict[str, dict[str, int]] = {}
    positions, ranks, back_edges = compute_layout(
        spec["nodes"], spec.get("edges", []), direction
    )

    for node in spec["nodes"]:
        original_id = str(node["id"])
        mx_id = unique_mx_id(original_id, "n", used_cell_ids)
        node_id_map[original_id] = mx_id
        kind = str(node.get("kind", "process")).lower()
        style = NODE_STYLES.get(kind, NODE_STYLES["process"])
        width = int(node.get("width", 150 if kind != "decision" else 140))
        height = int(node.get("height", 60 if kind != "decision" else 90))
        x, y = positions[original_id]
        x = int(node.get("x", x))
        y = int(node.get("y", y))
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": mx_id,
                "value": str(node["label"]),
                "style": style,
                "vertex": "1",
                "parent": "1",
            },
        )
        add_geometry(cell, x, y, width, height)
        node_geometries[original_id] = {"x": x, "y": y, "width": width, "height": height}

    bounds = diagram_bounds(node_geometries)
    for index, edge in enumerate(spec.get("edges", []), start=1):
        source_raw = str(edge["source"])
        target_raw = str(edge["target"])
        is_back_edge = (source_raw, target_raw) in back_edges
        edge_id = unique_mx_id(edge.get("id", f"e_{index}"), "e", used_cell_ids)
        style = BACK_EDGE_STYLE if is_back_edge else EDGE_STYLE
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": edge_id,
                "value": str(edge.get("label", "")),
                "style": style,
                "edge": "1",
                "parent": "1",
                "source": node_id_map[source_raw],
                "target": node_id_map[target_raw],
            },
        )
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        points = normalize_points(edge.get("points"))
        if not points:
            points = auto_edge_points(
                edge, node_geometries, ranks, bounds, direction, index, is_back_edge
            )
        if points:
            points_element = ET.SubElement(geometry, "Array", {"as": "points"})
            for x, y in points:
                ET.SubElement(points_element, "mxPoint", {"x": str(x), "y": str(y)})

    return warnings


def build_drawio(spec: dict) -> tuple[ET.ElementTree, list[str]]:
    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "modified": now,
            "agent": "code-drawio-direct",
            "version": "29.6.6",
            "type": "device",
        },
    )
    all_warnings: list[str] = []
    for page_spec in normalize_pages(spec):
        page_warnings = add_diagram(mxfile, page_spec)
        page_title = str(page_spec.get("title", "Code Flow"))
        all_warnings.extend(f"[{page_title}] {w}" for w in page_warnings)
    return ET.ElementTree(mxfile), all_warnings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Convert a JSON diagram spec to a draw.io .drawio file.")
    parser.add_argument("spec", help="Input JSON spec path")
    parser.add_argument("output", nargs="?", help="Output .drawio path. Defaults to the current directory.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    if args.output:
        output_path = Path(args.output)
    else:
        stem = spec_path.stem
        if stem.endswith(".diagram"):
            stem = stem[:-len(".diagram")]
        output_path = Path.cwd() / f"{stem}.drawio"
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    tree, warnings = build_drawio(spec)
    if warnings:
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        if args.strict:
            print("strict mode: not writing output because warnings were found", file=sys.stderr)
            return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

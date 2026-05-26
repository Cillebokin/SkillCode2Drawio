#!/usr/bin/env python3
"""Convert compact class-diagram JSON specs into native draw.io files.

The generator is dependency-free so it works offline. It creates UML-like
class/struct/interface boxes and relationship edges with draw.io-compatible
styles.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import sys
import unicodedata
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path


TYPE_COLORS = {
    "class": ("#dae8fc", "#6c8ebf"),
    "struct": ("#d5e8d4", "#82b366"),
    "interface": ("#fff2cc", "#d6b656"),
    "enum": ("#f8cecc", "#b85450"),
    "record": ("#e1d5e7", "#9673a6"),
    "type": ("#f5f5f5", "#666666"),
    "dto": ("#d5e8d4", "#82b366"),
}

EDGE_STYLES = {
    "inherits": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=0;strokeWidth=1.5;",
    "implements": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=0;dashed=1;strokeWidth=1.5;",
    "composition": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;startArrow=diamond;startFill=1;endArrow=open;strokeWidth=1.5;",
    "aggregation": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;startArrow=diamond;startFill=0;endArrow=open;strokeWidth=1.5;",
    "association": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=open;strokeWidth=1.5;",
    "dependency": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=open;dashed=1;strokeWidth=1.5;",
}

DIRECT_EDGE_STYLES = {
    "inherits": "html=1;endArrow=block;endFill=0;strokeWidth=1.5;",
    "implements": "html=1;endArrow=block;endFill=0;dashed=1;strokeWidth=1.5;",
    "composition": "html=1;startArrow=diamond;startFill=1;endArrow=open;strokeWidth=1.5;",
    "aggregation": "html=1;startArrow=diamond;startFill=0;endArrow=open;strokeWidth=1.5;",
    "association": "html=1;endArrow=open;strokeWidth=1.5;",
    "dependency": "html=1;endArrow=open;dashed=1;strokeWidth=1.5;",
}


def safe_mx_id(raw: str, prefix: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", str(raw).strip())
    if not value:
        value = uuid.uuid4().hex[:8]
    if value in {"0", "1"} or not re.match(r"^[A-Za-z_]", value):
        value = f"{prefix}_{value}"
    if not value.startswith(f"{prefix}_"):
        value = f"{prefix}_{value}"
    return value


def unique_mx_id(raw: str, prefix: str, used: set[str]) -> str:
    base = safe_mx_id(raw, prefix)
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def normalize_parameter(item: object) -> str:
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return str(item)

    name = str(item.get("name", "")).strip()
    typ = str(item.get("type", item.get("returnType", ""))).strip()
    default = str(item.get("default", "")).strip()
    if name and typ:
        text = f"{name}: {typ}"
    elif name:
        text = name
    elif typ:
        text = typ
    else:
        text = str(item)
    if default:
        text = f"{text} = {default}"
    return text


def normalize_member(item: object, is_method: bool = False) -> str:
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return str(item)
    visibility = str(item.get("visibility", "")).strip()
    prefix = visibility if visibility in {"+", "-", "#", "~"} else ""
    static = "{static} " if item.get("static") else ""
    name = str(item.get("name", "")).strip()
    typ = str(item.get("type", item.get("returnType", ""))).strip()
    if is_method:
        params = item.get("parameters", [])
        if isinstance(params, list):
            param_text = ", ".join(normalize_parameter(p) for p in params)
        elif params is None or params == "":
            param_text = ""
        else:
            param_text = str(params)
        suffix = f": {typ}" if typ else ""
        return f"{prefix} {static}{name}({param_text}){suffix}".strip()
    suffix = f": {typ}" if typ else ""
    return f"{prefix} {static}{name}{suffix}".strip()


def type_label(item: dict) -> str:
    kind = str(item.get("kind", "class")).lower()
    name = html.escape(str(item["name"]))
    namespace = html.escape(str(item.get("namespace", "")).strip())
    stereotype = str(item.get("stereotype", "")).strip()
    if stereotype:
        stereo = html.escape(f"<<{stereotype}>>")
    elif kind in {"interface", "struct", "enum", "record", "dto"}:
        stereo = html.escape(f"<<{kind}>>")
    else:
        stereo = ""

    parts = ["<div style='font-size:13px;line-height:1.25'>"]
    if namespace:
        parts.append(f"<div style='color:#666666;font-size:11px'>{namespace}</div>")
    if stereo:
        parts.append(f"<div style='color:#666666;font-size:11px'>{stereo}</div>")
    parts.append(f"<div><b>{name}</b></div>")

    fields = [normalize_member(x) for x in item.get("fields", [])]
    methods = [normalize_member(x, is_method=True) for x in item.get("methods", [])]
    notes = [str(x) for x in item.get("notes", [])]

    if fields:
        parts.append("<hr size='1'/>")
        for field in fields:
            parts.append(f"<div align='left'>{html.escape(field)}</div>")
    if methods:
        parts.append("<hr size='1'/>")
        for method in methods:
            parts.append(f"<div align='left'>{html.escape(method)}</div>")
    if notes:
        parts.append("<hr size='1'/>")
        for note in notes:
            parts.append(f"<div align='left'><i>{html.escape(note)}</i></div>")
    parts.append("</div>")
    return "".join(parts)


def type_style(kind: str) -> str:
    fill, stroke = TYPE_COLORS.get(kind, TYPE_COLORS["class"])
    return (
        "rounded=0;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;"
        f"fillColor={fill};strokeColor={stroke};fontSize=12;spacing=8;"
    )


def normalize_pages(spec: dict) -> list[dict]:
    if "pages" not in spec:
        return [spec]
    pages = spec["pages"]
    if not isinstance(pages, list) or not pages:
        raise ValueError("pages must be a non-empty list")

    normalized: list[dict] = []
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise ValueError(f"page {index} must be an object")
        page_spec = dict(page)
        if "direction" not in page_spec and "direction" in spec:
            page_spec["direction"] = spec["direction"]
        if "title" not in page_spec:
            page_spec["title"] = f"Page {index}"
        normalized.append(page_spec)
    return normalized


def validate_page_spec(spec: dict, label: str) -> list[str]:
    warnings: list[str] = []
    if not isinstance(spec.get("types"), list) or not spec["types"]:
        raise ValueError(f"{label} must contain a non-empty types list")
    if not isinstance(spec.get("relationships", []), list):
        raise ValueError(f"{label} relationships must be a list")

    valid_kinds = set(TYPE_COLORS)
    valid_rels = set(EDGE_STYLES)
    ids: set[str] = set()
    for item in spec["types"]:
        type_id = item.get("id")
        if not type_id:
            raise ValueError(f"{label}: every type needs an id")
        if type_id in ids:
            raise ValueError(f"{label}: duplicate type id: {type_id}")
        ids.add(type_id)
        if not item.get("name"):
            raise ValueError(f"{label}: type {type_id} needs a name")
        kind = str(item.get("kind", "class")).lower()
        if kind not in valid_kinds:
            warnings.append(f"{label}: type '{type_id}' has unknown kind '{kind}', rendered as class")

    for rel in spec.get("relationships", []):
        source = rel.get("source")
        target = rel.get("target")
        if source not in ids:
            raise ValueError(f"{label}: relationship source not found: {source}")
        if target not in ids:
            raise ValueError(f"{label}: relationship target not found: {target}")
        rel_type = str(rel.get("type", "association")).lower()
        if rel_type not in valid_rels:
            warnings.append(f"{label}: relationship {source}->{target} has unknown type '{rel_type}', rendered as association")
        if rel_type in {"composition", "aggregation"} and not rel.get("label") and not rel.get("targetMultiplicity"):
            warnings.append(f"{label}: {rel_type} {source}->{target} has no label or target multiplicity")
    return warnings


def validate_spec(spec: dict) -> list[str]:
    warnings: list[str] = []
    if "pages" in spec and ("types" in spec or "relationships" in spec):
        warnings.append("top-level types/relationships are ignored because pages is present")
    for index, page_spec in enumerate(normalize_pages(spec), start=1):
        title = str(page_spec.get("title", f"Page {index}"))
        warnings.extend(validate_page_spec(page_spec, f"page '{title}'"))
    return warnings


def compute_layout(
    types: list[dict],
    relationships: list[dict],
    direction: str,
) -> tuple[dict[str, tuple[int, int]], dict[str, int]]:
    ids = [str(t["id"]) for t in types]
    incoming: dict[str, int] = {x: 0 for x in ids}
    outgoing: dict[str, list[str]] = defaultdict(list)
    rank: dict[str, int] = {x: 0 for x in ids}

    # Put base/interface targets one rank after derived types for inheritance-like
    # relationships, and contained/dependent targets after sources otherwise.
    for rel in relationships:
        source = str(rel["source"])
        target = str(rel["target"])
        if source in incoming and target in incoming:
            outgoing[source].append(target)
            incoming[target] += 1

    queue = deque([x for x in ids if incoming[x] == 0])
    if not queue and ids:
        queue.append(ids[0])
    seen: set[str] = set()
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        for child in outgoing[current]:
            rank[child] = max(rank[child], rank[current] + 1)
            incoming[child] -= 1
            if incoming[child] <= 0:
                queue.append(child)

    if any(x not in seen for x in ids):
        fallback = max(rank.values(), default=0) + 1
        for x in ids:
            if x not in seen:
                rank[x] = fallback

    by_rank: dict[int, list[str]] = defaultdict(list)
    for x in ids:
        by_rank[rank[x]].append(x)

    sizes = {str(item["id"]): type_size(item) for item in types}
    row_gap = 80
    column_gap = 150

    positions: dict[str, tuple[int, int]] = {}
    if direction == "TD":
        rank_widths = {
            level: sum(sizes[type_id][0] for type_id in group) + row_gap * max(0, len(group) - 1)
            for level, group in by_rank.items()
        }
        rank_heights = {
            level: max((sizes[type_id][1] for type_id in group), default=0)
            for level, group in by_rank.items()
        }
        total_width = max(rank_widths.values(), default=0)
        y = 80
        for level, group in sorted(by_rank.items()):
            x = 80 + int((total_width - rank_widths[level]) / 2)
            for type_id in group:
                width, height = sizes[type_id]
                positions[type_id] = (x, y + int((rank_heights[level] - height) / 2))
                x += width + row_gap
            y += rank_heights[level] + column_gap
    else:
        rank_widths = {
            level: max((sizes[type_id][0] for type_id in group), default=0)
            for level, group in by_rank.items()
        }
        rank_heights = {
            level: sum(sizes[type_id][1] for type_id in group) + row_gap * max(0, len(group) - 1)
            for level, group in by_rank.items()
        }
        total_height = max(rank_heights.values(), default=0)
        x = 80
        for level, group in sorted(by_rank.items()):
            y = 80 + int((total_height - rank_heights[level]) / 2)
            for type_id in group:
                width, _height = sizes[type_id]
                positions[type_id] = (x + int((rank_widths[level] - width) / 2), y)
                y += sizes[type_id][1] + row_gap
            x += rank_widths[level] + column_gap
    return positions, rank


def normalize_points(raw: object) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    if not isinstance(raw, list):
        return points
    for point in raw:
        if isinstance(point, dict):
            points.append((int(point["x"]), int(point["y"])))
        elif isinstance(point, list) and len(point) == 2:
            points.append((int(point[0]), int(point[1])))
        else:
            raise ValueError(f"invalid edge point: {point!r}")
    return points


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


def text_display_width(value: str) -> int:
    width = 0
    for char in value:
        if unicodedata.combining(char):
            continue
        if unicodedata.category(char) in {"Cc", "Cf"}:
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
    return width


def type_size(item: dict) -> tuple[int, int]:
    fields = item.get("fields", [])
    methods = item.get("methods", [])
    notes = item.get("notes", [])
    member_lines = [normalize_member(x) for x in fields]
    member_lines.extend(normalize_member(x, is_method=True) for x in methods)
    member_lines.extend(str(x) for x in notes)
    title_lines = [
        str(item.get("namespace", "")),
        str(item.get("stereotype", "")),
        str(item.get("name", "")),
    ]
    longest = max((text_display_width(line) for line in title_lines + member_lines), default=12)
    line_count = 2 + len(fields) + len(methods) + len(notes)
    width = int(item.get("width", max(240, min(520, 95 + longest * 8))))
    height = int(item.get("height", max(90, 52 + line_count * 22)))
    return width, height


def diagram_bounds(geometries: dict[str, dict[str, int]]) -> dict[str, int]:
    left = min(geometry["x"] for geometry in geometries.values())
    top = min(geometry["y"] for geometry in geometries.values())
    right = max(geometry["x"] + geometry["width"] for geometry in geometries.values())
    bottom = max(geometry["y"] + geometry["height"] for geometry in geometries.values())
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def rect_center(geometry: dict[str, int]) -> tuple[float, float]:
    return (
        geometry["x"] + geometry["width"] / 2.0,
        geometry["y"] + geometry["height"] / 2.0,
    )


def boundary_point(geometry: dict[str, int], toward: tuple[float, float]) -> tuple[float, float]:
    cx, cy = rect_center(geometry)
    tx, ty = toward
    dx = tx - cx
    dy = ty - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return (cx, cy)
    half_w = geometry["width"] / 2.0
    half_h = geometry["height"] / 2.0
    scale = min(
        half_w / abs(dx) if abs(dx) > 1e-9 else float("inf"),
        half_h / abs(dy) if abs(dy) > 1e-9 else float("inf"),
    )
    return (cx + dx * scale, cy + dy * scale)


def inflated_rect(geometry: dict[str, int], margin: int = 18) -> tuple[float, float, float, float]:
    return (
        geometry["x"] - margin,
        geometry["y"] - margin,
        geometry["x"] + geometry["width"] + margin,
        geometry["y"] + geometry["height"] + margin,
    )


def point_in_rect(point: tuple[float, float], rect: tuple[float, float, float, float]) -> bool:
    x, y = point
    left, top, right, bottom = rect
    return left <= x <= right and top <= y <= bottom


def rectangles_overlap(a: dict[str, int], b: dict[str, int], gap: int = 0) -> bool:
    return not (
        a["x"] + a["width"] + gap <= b["x"]
        or b["x"] + b["width"] + gap <= a["x"]
        or a["y"] + a["height"] + gap <= b["y"]
        or b["y"] + b["height"] + gap <= a["y"]
    )


def warn_overlapping_types(
    geometries: dict[str, dict[str, int]],
    page_name: str,
    warnings: list[str],
) -> None:
    ids = list(geometries)
    for left_index, left_id in enumerate(ids):
        for right_id in ids[left_index + 1 :]:
            if rectangles_overlap(geometries[left_id], geometries[right_id]):
                warnings.append(f"page '{page_name}': type boxes overlap: {left_id} and {right_id}")


def segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    def orient(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_segment(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> bool:
        return (
            min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9
            and min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9
        )

    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    if abs(o1) < 1e-9 and on_segment(a, c, b):
        return True
    if abs(o2) < 1e-9 and on_segment(a, d, b):
        return True
    if abs(o3) < 1e-9 and on_segment(c, a, d):
        return True
    if abs(o4) < 1e-9 and on_segment(c, b, d):
        return True
    return False


def segment_intersects_rect(
    a: tuple[float, float],
    b: tuple[float, float],
    rect: tuple[float, float, float, float],
) -> bool:
    left, top, right, bottom = rect
    if point_in_rect(a, rect) or point_in_rect(b, rect):
        return True
    corners = [(left, top), (right, top), (right, bottom), (left, bottom)]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    return any(segments_intersect(a, b, c, d) for c, d in edges)


def route_is_clear(
    source: str,
    target: str,
    points: list[tuple[int, int]],
    geometries: dict[str, dict[str, int]],
) -> bool:
    source_geometry = geometries[source]
    target_geometry = geometries[target]
    first_target = points[0] if points else rect_center(target_geometry)
    last_source = points[-1] if points else rect_center(source_geometry)
    start = boundary_point(source_geometry, first_target)
    end = boundary_point(target_geometry, last_source)
    full_path: list[tuple[float, float]] = [start, *points, end]
    for a, b in zip(full_path, full_path[1:]):
        for type_id, geometry in geometries.items():
            if type_id in {source, target}:
                continue
            if segment_intersects_rect(a, b, inflated_rect(geometry)):
                return False
    return True


def auto_relationship_route(
    rel: dict,
    geometries: dict[str, dict[str, int]],
    ranks: dict[str, int],
    bounds: dict[str, int],
    direction: str,
    index: int,
) -> tuple[list[tuple[int, int]], bool]:
    source = str(rel["source"])
    target = str(rel["target"])
    source_geometry = geometries[source]
    target_geometry = geometries[target]
    source_rank = ranks.get(source, 0)
    target_rank = ranks.get(target, 0)

    sx = source_geometry["x"]
    sy = source_geometry["y"]
    sw = source_geometry["width"]
    sh = source_geometry["height"]
    tx = target_geometry["x"]
    ty = target_geometry["y"]
    tw = target_geometry["width"]
    th = target_geometry["height"]

    scx = sx + sw // 2
    scy = sy + sh // 2
    tcx = tx + tw // 2
    tcy = ty + th // 2
    offset = 90 + (index % 5) * 34

    route = str(rel.get("route", "auto")).lower()
    if route in {"direct", "straight", "auto"} and route_is_clear(source, target, [], geometries):
        return [], True
    if route in {"direct", "straight"}:
        # Honor the user's preference only when safe; otherwise fall through to
        # obstacle-avoiding routes so edges do not cross class boxes.
        pass

    candidates: list[list[tuple[int, int]]] = []
    if direction == "TD":
        if target_rank > source_rank:
            mid_y = sy + sh + max(45, (ty - (sy + sh)) // 2)
            candidates.append([(scx, mid_y), (tcx, mid_y)])
        elif target_rank < source_rank:
            lane_x = bounds["right"] + offset
            candidates.append([(sx + sw + 25, scy), (lane_x, scy), (lane_x, tcy), (tx + tw + 25, tcy)])
        else:
            lane_y = bounds["bottom"] + offset
            candidates.append([(scx, sy + sh + 25), (scx, lane_y), (tcx, lane_y), (tcx, ty + th + 25)])
    elif target_rank > source_rank:
        mid_x = sx + sw + max(55, (tx - (sx + sw)) // 2)
        candidates.append([(mid_x, scy), (mid_x, tcy)])
    elif target_rank < source_rank:
        lane_y = bounds["top"] - offset
        candidates.append([(scx, sy - 25), (scx, lane_y), (tcx, lane_y), (tcx, ty - 25)])
    else:
        lane_x = bounds["right"] + offset
        candidates.append([(sx + sw + 25, scy), (lane_x, scy), (lane_x, tcy), (tx + tw + 25, tcy)])

    right_lane = bounds["right"] + offset
    left_lane = bounds["left"] - offset
    top_lane = bounds["top"] - offset
    bottom_lane = bounds["bottom"] + offset
    candidates.extend(
        [
            [(sx + sw + 25, scy), (right_lane, scy), (right_lane, tcy), (tx + tw + 25, tcy)],
            [(sx - 25, scy), (left_lane, scy), (left_lane, tcy), (tx - 25, tcy)],
            [(scx, sy - 25), (scx, top_lane), (tcx, top_lane), (tcx, ty - 25)],
            [(scx, sy + sh + 25), (scx, bottom_lane), (tcx, bottom_lane), (tcx, ty + th + 25)],
        ]
    )

    for points in candidates:
        if route_is_clear(source, target, points, geometries):
            return points, False
    # Last resort: route outside the right lane. This keeps the line away from
    # most boxes even in very dense diagrams; users can still override with
    # explicit points for pathological cases.
    return candidates[-4], False


def create_graph_model(diagram: ET.Element) -> ET.Element:
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
    return root


def build_diagram_page(diagram: ET.Element, spec: dict, warnings: list[str]) -> None:
    direction = str(spec.get("direction", "LR")).upper()
    if direction not in {"LR", "TD"}:
        warnings.append(f"page '{spec.get('title', 'Class Diagram')}' has unknown direction '{direction}', using LR")
        direction = "LR"

    root = create_graph_model(diagram)
    used_ids = {"0", "1"}
    type_id_map: dict[str, str] = {}
    type_geometries: dict[str, dict[str, int]] = {}
    positions, ranks = compute_layout(spec["types"], spec.get("relationships", []), direction)

    for item in spec["types"]:
        raw_id = str(item["id"])
        mx_id = unique_mx_id(raw_id, "t", used_ids)
        type_id_map[raw_id] = mx_id
        kind = str(item.get("kind", "class")).lower()
        if kind not in TYPE_COLORS:
            kind = "class"
        x, y = positions[raw_id]
        x = int(item.get("x", x))
        y = int(item.get("y", y))
        width, height = type_size(item)
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": mx_id,
                "value": type_label(item),
                "style": type_style(kind),
                "vertex": "1",
                "parent": "1",
            },
        )
        add_geometry(cell, x, y, width, height)
        type_geometries[raw_id] = {"x": x, "y": y, "width": width, "height": height}

    warn_overlapping_types(type_geometries, str(spec.get("title", "Class Diagram")), warnings)

    bounds = diagram_bounds(type_geometries)
    for index, rel in enumerate(spec.get("relationships", []), start=1):
        rel_type = str(rel.get("type", "association")).lower()
        points = normalize_points(rel.get("points"))
        is_direct = False
        if not points:
            points, is_direct = auto_relationship_route(rel, type_geometries, ranks, bounds, direction, index)
        style_map = DIRECT_EDGE_STYLES if is_direct else EDGE_STYLES
        style = style_map.get(rel_type, style_map["association"])
        label_parts = []
        if rel.get("sourceMultiplicity"):
            label_parts.append(str(rel["sourceMultiplicity"]))
        if rel.get("label"):
            label_parts.append(str(rel["label"]))
        if rel.get("targetMultiplicity"):
            label_parts.append(str(rel["targetMultiplicity"]))
        label = " ".join(label_parts)
        edge_id = unique_mx_id(rel.get("id", f"rel_{index}"), "r", used_ids)
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": edge_id,
                "value": label,
                "style": style,
                "edge": "1",
                "parent": "1",
                "source": type_id_map[str(rel["source"])],
                "target": type_id_map[str(rel["target"])],
            },
        )
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        if points:
            points_element = ET.SubElement(geometry, "Array", {"as": "points"})
            for x, y in points:
                ET.SubElement(points_element, "mxPoint", {"x": str(x), "y": str(y)})


def build_drawio(spec: dict) -> tuple[ET.ElementTree, list[str]]:
    warnings = validate_spec(spec)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "modified": now,
            "agent": "code-drawio-class",
            "version": "29.6.6",
            "type": "device",
        },
    )

    pages = normalize_pages(spec)
    for index, page_spec in enumerate(pages, start=1):
        page_name = str(page_spec.get("title", f"Page {index}"))
        diagram = ET.SubElement(mxfile, "diagram", {"id": uuid.uuid4().hex[:12], "name": page_name})
        build_diagram_page(diagram, page_spec, warnings)

    return ET.ElementTree(mxfile), warnings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Convert a JSON class diagram spec to a draw.io .drawio file.")
    parser.add_argument("spec", help="Input JSON spec path")
    parser.add_argument("output", nargs="?", help="Output .drawio path. Defaults to the current directory.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    if args.output:
        output_path = Path(args.output)
    else:
        stem = spec_path.stem
        if stem.endswith(".class-diagram"):
            stem = stem[: -len(".class-diagram")]
        output_path = Path.cwd() / f"{stem}.drawio"

    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    tree, warnings = build_drawio(spec)
    if warnings:
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
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

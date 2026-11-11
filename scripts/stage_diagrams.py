"""Generate the progressive stage diagrams from _data/stages.yml.

Usage: python3 scripts/stage_diagrams.py   (requires PyYAML)
Writes _includes/stages/stage-<n>.svg. Styling comes from assets/style.css (.bp-*).
"""
import html
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = yaml.safe_load((ROOT / "_data" / "stages.yml").read_text())
OUT = ROOT / "_includes" / "stages"

X0, PITCH_X, W = 10, 135, 122      # columns
Y0, PITCH_Y, H = 46, 90, 50        # rows
GAP_Y = PITCH_Y - H
WIDTH = 952
ROWMAP = {}  # grid row -> drawn row for the stage being rendered (unused rows collapse)


def rect(slot):
    s = DATA["slots"][slot]
    x, y = X0 + s["c"] * PITCH_X, Y0 + ROWMAP.get(s["r"], s["r"]) * PITCH_Y
    if s.get("span"):
        return x + W / 2 - 17, y - 8, 34, (s["span"] - 1) * PITCH_Y + H + 16
    return x, y, W, H


def cell(slot):
    s = DATA["slots"][slot]
    return s["c"], ROWMAP.get(s["r"], s["r"])


def edge_path(e, boxes):
    fx, fy, fw, fh = rect(e["from"])
    tx, ty, tw, th = rect(e["to"])
    fdx, tdx = e.get("from_dx", 0), e.get("to_dx", 0)
    (fc, fr), (tc, tr) = cell(e["from"]), cell(e["to"])
    route = e.get("route", "auto")
    if route == "top":                     # up into the gap above the source row, across, then down
        sx, ex = fx + fw / 2 + fdx, tx + tw / 2 + tdx
        gy = Y0 - 18 if fr == 0 else fy - GAP_Y / 2
        return f"M{sx},{fy} V{gy} H{ex} V{ty - 2}", (sx + ex) / 2, gy - 4
    if route == "left":                    # down the left of the source column
        sx, gx = fx, fx - 8
        return f"M{sx},{fy + fh / 2} H{gx} V{ty + th / 2} H{tx - 2}", gx - 4, (fy + ty + th) / 2
    if fr == tr:                           # same row: straight
        y = fy + fh / 2
        if tc > fc:
            return f"M{fx + fw},{y} H{tx - 2}", (fx + fw + tx) / 2, y - 5
        return f"M{fx},{y} H{tx + tw + 2}", (fx + tx + tw) / 2, y - 5
    if fc == tc:                           # same column: straight
        x = fx + fw / 2 + fdx
        if tr > fr:
            return f"M{x},{fy + fh} V{ty - 2}", x + 6, (fy + fh + ty) / 2 + 3, "start"
        return f"M{x},{fy} V{ty + th + 2}", x + 6, (ty + th + fy) / 2 + 3, "start"
    # different row and column: via the gutter next to the source row
    sx, ex = fx + fw / 2 + fdx, tx + tw / 2 + tdx
    if tr > fr:
        gy = fy + fh + GAP_Y / 2
        return f"M{sx},{fy + fh} V{gy} H{ex} V{ty - 2}", (sx + ex) / 2, gy - 4
    gy = fy - GAP_Y / 2
    return f"M{sx},{fy} V{gy} H{ex} V{ty + th + 2}", (sx + ex) / 2, gy - 4


def render(stage):
    esc = html.escape
    boxes = {b["slot"]: b for b in stage["boxes"]}
    used = sorted({DATA["slots"][b]["r"] for b in boxes if not DATA["slots"][b].get("span")})
    ROWMAP.clear()
    ROWMAP.update({r: i for i, r in enumerate(used)})
    HEIGHT = Y0 + (len(used) - 1) * PITCH_Y + H + 52
    out = [f'<svg class="bp stage" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
           f'aria-label="Stage {stage["n"]}: {esc(stage["title"])}" xmlns="http://www.w3.org/2000/svg">',
           '<defs><marker id="st-arrow-%d" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
           'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="bp-head"/></marker></defs>'
           % stage["n"]]
    wall = boxes.get("egress-proxy")
    if wall:
        x, y, w, h = rect("egress-proxy")
        cls = "bp-wall new" if wall["kind"] in ("new", "upgraded") else "bp-wall"
        out.append(f'<g class="{cls}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>'
                   f'<text x="{x + w / 2}" y="{y + h / 2}" transform="rotate(-90 {x + w / 2} {y + h / 2})" '
                   f'text-anchor="middle">{esc(wall["label"])}</text></g>')
    marker = f"url(#st-arrow-{stage['n']})"
    labels = []
    out.append('<g class="bp-edge">')
    for e in stage["edges"]:
        d, lx, ly, *anchor = edge_path(e, boxes)
        cls = ' class="dash"' if e.get("style") == "dash" else ""
        start = f' marker-start="{marker}"' if e.get("both") else ""
        out.append(f'<path{cls} d="{d}"{start} marker-end="{marker}"/>')
        if e.get("label"):
            labels.append(f'<text x="{lx}" y="{ly}" text-anchor="{anchor[0] if anchor else "middle"}">{esc(e["label"])}</text>')
    out.append("</g>")
    out.append('<g class="bp-edge-label">' + "".join(labels) + "</g>")
    for b in stage["boxes"]:
        if b["slot"] == "egress-proxy":
            continue
        x, y, w, h = rect(b["slot"])
        kind = {"ext": "ext-actor", "new": "new", "upgraded": "upgraded"}.get(b["kind"], "")
        out.append(f'<g class="bp-box {kind}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7"/>'
                   f'<text class="n" x="{x + w / 2}" y="{y + 21}" text-anchor="middle">{esc(b["label"])}</text>'
                   f'<text class="s" x="{x + w / 2}" y="{y + 37}" text-anchor="middle">{esc(b.get("sub", ""))}</text></g>')
    ly = HEIGHT - 22
    legend = [("new", "New at this stage"), ("upgraded", "Upgraded"), ("", "Carried forward"), ("ext-actor", "Outside the system")]
    for i, (kind, text) in enumerate(legend):
        lx = 12 + i * 170
        out.append(f'<g class="bp-box {kind}"><rect x="{lx}" y="{ly - 11}" width="22" height="14" rx="3"/></g>'
                   f'<text class="bp-legend" x="{lx + 30}" y="{ly}">{text}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for st in DATA["stages"]:
        (OUT / f"stage-{st['n']}.svg").write_text(render(st))
        print(f"wrote stage-{st['n']}.svg")

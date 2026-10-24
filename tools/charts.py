#!/usr/bin/env python3
"""병목 레이더 차트 생성기.

JSON 명세를 읽어 _includes/charts/ 아래에 인라인 SVG를 만든다.
색은 사이트 CSS 변수(--ink, --muted, --line, --accent, --up, --down, --heat-1..5)를
그대로 써서 다크 모드에서도 자동으로 맞는다.

사용법:
  python3 tools/charts.py tools/specs/YYYY-MM-DD.json

차트 종류:
  "hbars"  왼쪽에서 오른쪽으로 자라는 막대 (크기 비교: 납기, 물량 등)
           {"name", "type": "hbars", "title", "unit", "items": [{"label", "value", "note"?}]}
  "bars"   0을 가운데 둔 양방향 막대 (등락률 등, 오르면 빨강·내리면 파랑)
           {"name", "type": "bars", "title", "unit", "items": [{"label", "value"}]}
  "heat"   병목 온도계 (행=분야, 열=시점, 값 1~5)
           {"name", "type": "heat", "title", "cols": ["지금", "1년 뒤", "5년 뒤"],
            "rows": [{"label", "values": [5, 4, 2]}]}
  "compare" 전·후 비교 막대 쌍 (예: 위기 전 vs 지금)
           {"name", "type": "compare", "title", "unit",
            "items": [{"label", "before", "after", "before_label", "after_label"}]}
"""
import json
import os
import sys
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_includes", "charts")

W = 400
FONT = 'font-family="inherit"'
HEAT_WORDS = {1: "여유", 2: "보통", 3: "빠듯", 4: "부족", 5: "심각"}


def num(v):
    if float(v).is_integer():
        return f"{v:,.0f}"
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def fmt(v, unit=""):
    if unit == "%":
        return f"{v:+.2f}%"
    sign = "+" if v > 0 else ("−" if v < 0 else "")
    return f"{sign}{num(abs(v))}{(' ' + unit) if unit else ''}"


def wrap(svg_body, h, title, desc):
    return (
        f'<figure class="chart">\n'
        f'<figcaption>{escape(title)}</figcaption>\n'
        f'<svg viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{escape(desc)}" '
        f'style="max-width:100%;height:auto;display:block" {FONT}>\n{svg_body}</svg>\n'
        f'</figure>\n'
    )


def hbars(c):
    items = c["items"]
    unit = c.get("unit", "")
    row, top = 50, 4
    h = top + row * len(items) + 4
    x0, x1 = 0, W - 70
    m = max(i["value"] for i in items) or 1
    out = []
    for k, it in enumerate(items):
        v = it["value"]
        y = top + k * row
        bw = max(v / m * (x1 - x0), 3)
        label = it["label"] + (f' · {it["note"]}' if it.get("note") else "")
        out.append(f'<g><title>{escape(it["label"])} {num(v)} {escape(unit)}</title>')
        out.append(f'<text x="0" y="{y + 15}" font-size="14" font-weight="600" fill="var(--ink)">{escape(label)}</text>')
        out.append(f'<rect x="{x0}" y="{y + 23}" width="{bw:.1f}" height="18" rx="4" fill="var(--accent)"/>')
        out.append(f'<text x="{x0 + bw + 8:.1f}" y="{y + 37}" font-size="14" font-weight="700" fill="var(--ink)">{num(v)}{escape(unit)}</text>')
        out.append('</g>')
    desc = ", ".join(f'{i["label"]} {num(i["value"])}{unit}' for i in items)
    return wrap("\n".join(out) + "\n", h, c["title"], desc)


def bars(c):
    items = c["items"]
    unit = c.get("unit", "")
    row, top, label_w = 40, 6, 104
    h = top + row * len(items) + 8
    plot_l, plot_r = label_w, W - 12
    mid = (plot_l + plot_r) / 2
    half = (plot_r - plot_l) / 2 - 62
    m = max(abs(i["value"]) for i in items) or 1
    out = [f'<line x1="{mid}" y1="{top - 4}" x2="{mid}" y2="{h - 4}" stroke="var(--muted)" stroke-width="1.5"/>']
    for k, it in enumerate(items):
        v = it["value"]
        y = top + k * row
        cy = y + row / 2
        bw = max(abs(v) / m * half, 3)
        color = "var(--up)" if v > 0 else ("var(--down)" if v < 0 else "var(--muted)")
        x = mid if v >= 0 else mid - bw
        out.append(f'<g><title>{escape(it["label"])} {escape(fmt(v, unit))}</title>')
        out.append(f'<text x="0" y="{cy + 5}" font-size="15" font-weight="600" fill="var(--ink)">{escape(it["label"])}</text>')
        out.append(f'<rect x="{x:.1f}" y="{cy - 10}" width="{bw:.1f}" height="20" rx="4" fill="{color}"/>')
        tx = mid + bw + 8 if v >= 0 else mid - bw - 8
        anchor = "start" if v >= 0 else "end"
        out.append(f'<text x="{tx:.1f}" y="{cy + 5}" font-size="14" font-weight="700" text-anchor="{anchor}" fill="var(--ink)">{escape(fmt(v, unit))}</text>')
        out.append('</g>')
    desc = ", ".join(f'{i["label"]} {fmt(i["value"], unit)}' for i in items)
    return wrap("\n".join(out) + "\n", h, c["title"], desc)


def heat(c):
    cols, rows = c["cols"], c["rows"]
    label_w, head, row, gap = 132, 30, 40, 3
    cw = (W - label_w) / len(cols)
    h = head + row * len(rows) + 4
    out = []
    for j, name in enumerate(cols):
        out.append(f'<text x="{label_w + cw * j + cw / 2:.1f}" y="18" font-size="13" font-weight="700" text-anchor="middle" fill="var(--muted)">{escape(name)}</text>')
    for i, r in enumerate(rows):
        y = head + i * row
        out.append(f'<text x="0" y="{y + row / 2 + 5:.1f}" font-size="14" font-weight="600" fill="var(--ink)">{escape(r["label"])}</text>')
        for j, v in enumerate(r["values"]):
            v = int(v)
            x = label_w + cw * j
            out.append(f'<g><title>{escape(r["label"])} · {escape(cols[j])}: {v} ({HEAT_WORDS[v]})</title>')
            out.append(f'<rect x="{x + gap / 2:.1f}" y="{y + gap / 2:.1f}" width="{cw - gap:.1f}" height="{row - gap:.1f}" rx="6" fill="var(--heat-{v})"/>')
            out.append(f'<text x="{x + cw / 2:.1f}" y="{y + row / 2 + 5:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="var(--heat-ink-{v})">{v} {HEAT_WORDS[v]}</text>')
            out.append('</g>')
    desc = "; ".join(f'{r["label"]}: ' + ", ".join(f"{cols[j]} {v}" for j, v in enumerate(r["values"])) for r in rows)
    return wrap("\n".join(out) + "\n", h, c["title"], desc)


def compare(c):
    items = c["items"]
    unit = c.get("unit", "")
    block = 92
    h = block * len(items) + 4
    x1 = W - 96
    out = []
    for k, it in enumerate(items):
        y = k * block
        m = max(it["before"], it["after"]) or 1
        out.append(f'<text x="0" y="{y + 16}" font-size="14" font-weight="700" fill="var(--ink)">{escape(it["label"])}</text>')
        for n, (key, lab, color) in enumerate([("before", it.get("before_label", "전"), "var(--muted)"),
                                                 ("after", it.get("after_label", "지금"), "var(--accent)")]):
            v = it[key]
            by = y + 26 + n * 30
            bw = max(v / m * (x1 - 60), 3)
            out.append(f'<g><title>{escape(it["label"])} {escape(lab)}: {num(v)} {escape(unit)}</title>')
            out.append(f'<text x="0" y="{by + 14}" font-size="13" fill="var(--muted)">{escape(lab)}</text>')
            out.append(f'<rect x="60" y="{by + 2}" width="{bw:.1f}" height="18" rx="4" fill="{color}"/>')
            out.append(f'<text x="{60 + bw + 8:.1f}" y="{by + 16}" font-size="14" font-weight="700" fill="var(--ink)">{num(v)}{escape(unit)}</text>')
            out.append('</g>')
    desc = "; ".join(f'{i["label"]}: {num(i["before"])} → {num(i["after"])}{unit}' for i in items)
    return wrap("\n".join(out) + "\n", h, c["title"], desc)


KINDS = {"hbars": hbars, "bars": bars, "heat": heat, "compare": compare}


def main(path):
    with open(path, encoding="utf-8") as f:
        spec = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    for c in spec["charts"]:
        svg = KINDS[c["type"]](c)
        name = f'{spec["date"]}-{c["name"]}.svg'
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote _includes/charts/{name}  →  {{% include charts/{name} %}}")


if __name__ == "__main__":
    main(sys.argv[1])

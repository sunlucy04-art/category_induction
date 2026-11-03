"""
Build strategy_schematic.html: a one-page map of the test trials, grouped by
category structure (Lucy and Sam share one, Ana has another, plus the trials
that name no kid), showing each trial's answer options and the strategy each
option maps to.

Everything comes from the real experiment files (high nameability), so
re-run this after changing the design:
  training_trials.csv / test_trials.csv / shape_color_roles.csv
  images/high_nameability/shape_outlines/*.svg

Usage: python3 make_strategy_schematic.py
"""

from collections import Counter
from html import escape
from pathlib import Path

from make_overview import read_csv, read_svg_path, swatch_hex

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "strategy_schematic.html"
CONDITION = "high_nameability"

# Plain-language meaning of each strategy code (see option_strategy in
# generate_design.py), and its pill color.
STRATEGIES = {
    "most_frequent_color_kid_match": ("the named kid's most frequent color", "#2a78d6"),
    "conjunction_kid_match": ("the color the named kid mostly used on this shape (the named kid's own shapes)", "#eb6834"),
    "conjunction_other_kid": ("the color this shape mostly had, when a different kid drew it (no kid named: whoever drew it)", "#c98500"),
    "most_frequent_color_other_kid": ("the most frequent color of the kid who usually draws this shape", "#008300"),
    "named_kid_other_color": ("a color the named kid used less often, on other shapes", "#6e6e6e"),
    "most_frequent_unrelated_kid": ("the most frequent color of a kid unrelated to this trial (not named, never drew this shape)", "#8a8a8a"),
    "never_used": ("a color the named kid never used (no kid named: never used on this shape)", "#a8a8a8"),
    "correct": ("memory questions: the right answer", "#6250d6"),
}

GROUPS = {
    "agree": ("Agree", "The kid's usual color is also the color they always used on this shape, so every strategy gives the same answer. A baseline."),
    "classic_disagree": ("Classic disagree", "The kid's own shape: their usual color vs. the color they mostly used on this shape."),
    "cross_category_unique_color": ("Cross-category: Ana's shape", "A shape only Ana draws, said to be by Lucy. Each strategy has its own option."),
    "cross_category_shared_color": ("Cross-category: the other kid's shape", "Sam's shape, said to be by Lucy. The shape's usual color (C5) is also a color Lucy used on Lucy's own S1s, so that option fits two strategies."),
    "category_only": ("Category only", "Only the kid's name, no shape."),
    "memory_probe_conflict": ("Memory probe: own shape", "\"What color did the kid use for this shape?\" The right answer is not the kid's usual color."),
    "memory_probe_no_conflict": ("Memory probe: shared shape (S3)", "Same question; here the right answer is also the kid's usual color."),
    "kid_not_named": ("Kid not named", "Shape only: infer who drew it and use their usual color, or go by the shape's own color."),
    "kid_not_named_control": ("Kid not named: control (S3)", "Every kid draws S3, each in their usual color, so there is no single drawer or shape color."),
}

SECTIONS = [
    ("Lucy and Sam", "Lucy and Sam have the same structure, so Lucy's trials are shown. Sam's are the mirror image (swap S1 and S2, C1 and C2) with the same strategies.",
     "Lucy", ["agree", "classic_disagree", "cross_category_unique_color", "cross_category_shared_color", "category_only",
              "memory_probe_conflict", "memory_probe_no_conflict"]),
    ("Ana", "Ana uses the usual color less often (5 of 8), and Ana's own shape is always the same other color (3 of 3). Ana has no cross-category trials.",
     "Ana", ["agree", "classic_disagree", "category_only", "memory_probe_conflict", "memory_probe_no_conflict"]),
    ("No kid named", "\"Someone made this new drawing.\" Lucy's shape is shown (Sam's S2 is the mirror image), then Ana's shape, then the control.",
     "none", ["kid_not_named", "kid_not_named_control"]),
]

MIRROR = str.maketrans({"1": "2", "2": "1"})


def mirrored(codes):
    # Lucy <-> Sam: S1 <-> S2 and C1 <-> C2
    return [c.translate(MIRROR) if c[:1] in "SC" else c for c in codes]


def main():
    # shape / color below are the role codes (S1, C5), which the page is written in
    def with_roles(rows):
        return [dict(r, shape=r["shape_role"], color=r["color_role"]) for r in rows
                if r["condition"] == CONDITION and r["color_version"] == "1"]
    training = with_roles(read_csv("training_trials.csv"))
    tests = with_roles(read_csv("test_trials.csv"))
    roles = {r["role"]: r["file_name"] for r in read_csv("shape_color_roles.csv")
             if r["condition"] == CONDITION and r["color_version"] == "1"}
    image_dir = ROOT / "images" / CONDITION
    hexes = {c: swatch_hex(image_dir / "colors" / f"{roles[c]}.png") for c in roles if c.startswith("C")}
    shapes = {s: read_svg_path(image_dir / "shape_outlines" / f"{roles[s]}.svg") for s in roles if s.startswith("S")}

    def fig(shape, fill, size):
        s = shapes[shape]
        width = max(s["w"], 1.1 * 256 / size)
        return (f'<svg viewBox="0 0 256 256" width="{size}" height="{size}" aria-label="{shape}">'
                f'<path d="{s["d"]}" fill="{fill}" stroke="#2A2A2A" stroke-width="{width:.2f}" stroke-linejoin="round"/></svg>')

    def options(t):
        return [(t[f"opt{i}"], t[f"strategy_opt{i}"], t[f"key_opt{i}"]) for i in range(1, 6) if t.get(f"opt{i}")]

    # Sam's trials must be Lucy's mirror image, or the "same structure" claim is wrong.
    for t in (t for t in tests if t["kid"] == "Lucy"):
        sam = [s for s in tests if s["kid"] == "Sam" and s["test_type"] == t["test_type"]
               and s["shape"] == t["shape"].translate(MIRROR)]
        assert len(sam) == 1, t["id"]
        lucy_codes = [o[0] for o in options(t)]
        lucy_strategies = dict(zip(mirrored(lucy_codes), [o[1] for o in options(t)]))
        assert {c: s for c, s, _ in options(sam[0])} == lucy_strategies, t["id"]

    def pills(strategy):
        return "".join(f'<span class="pill" style="--c:{STRATEGIES[s][1]}">{escape(s)}</span>' for s in strategy.split("-"))

    def trial_row(t):
        name, what = GROUPS[t["trial_group"]]
        if t["shape"] == "none":
            figure = '<div class="blank">no shape</div>'
        else:
            figure = fig(t["shape"], "#FFFFFF", 84)
        prompt = t["prompt"] or ""
        opts = "".join(
            f'<div class="opt"><div class="sw" style="background:{hexes[c]}"></div><div class="code">{c}</div>'
            f'{pills(s)}<div class="why">{escape(k)}</div></div>'
            for c, s, k in options(t))
        return (f'<div class="trial"><div class="what"><h3>{escape(name)}</h3><p>{escape(what)}</p>'
                f'<div class="stim">{figure}<div><div class="prompt">{escape(prompt)}</div>'
                f'<div class="q">{escape(t["question"])}</div><div class="id">{t["id"]}, shape {t["shape"]}</div></div></div></div>'
                f'<div class="opts">{opts}</div></div>')

    kids = list(dict.fromkeys(r["kid"] for r in training))
    structure = ""
    for kid in kids:
        mine = sorted((r for r in training if r["kid"] == kid), key=lambda r: (r["shape"], r["color"]))
        usual, n = Counter(r["color"] for r in mine).most_common(1)[0]
        figs = "".join(fig(r["shape"], hexes[r["color"]], 40) for r in mine)
        structure += (f'<div class="kid"><b>{kid}</b><div class="figs">{figs}</div>'
                      f'<div class="stat">Usual color {usual} on {n} of {len(mine)}</div></div>')

    legend = "".join(f'<div class="leg">{pills(code)}<span>{escape(text)}</span></div>' for code, (text, _) in STRATEGIES.items())

    body = ""
    for title, note, kid, groups in SECTIONS:
        rows = []
        for g in groups:
            matches = [t for t in tests if t["trial_group"] == g and t["kid"] == kid]
            if g == "kid_not_named":
                matches = [t for t in matches if t["shape"] in ("S1", "S4")]
            rows += sorted(matches, key=lambda t: t["shape"])
        body += f'<section><h2>{escape(title)}</h2><p class="note">{escape(note)}</p>{"".join(trial_row(t) for t in rows)}</section>'

    # Color version -> color role mapping (the page above shows version 1).
    version_rows = [r for r in read_csv("shape_color_roles.csv") if r["condition"] == CONDITION and r["kind"] == "color"]
    versions = sorted({r["color_version"] for r in version_rows}, key=int)
    head = "".join(f"<th>Version {v}</th>" for v in versions)
    body_rows = ""
    for role in sorted({r["role"] for r in version_rows}):
        mine = {r["color_version"]: r for r in version_rows if r["role"] == role}
        cells = "".join(
            f'<td><span class="vsw" style="background:{swatch_hex(image_dir / "colors" / (mine[v]["file_name"] + ".png"))}"></span>'
            f'{escape(mine[v]["color_name"])} <span class="vnum">({mine[v]["number"]})</span></td>' for v in versions)
        body_rows += f'<tr><th>{role}<div class="vjob">{escape(mine[versions[0]]["job"])}</div></th>{cells}</tr>'
    version_table = (f'<section><h2>Color versions</h2><p class="note">Each participant gets one of {len(versions)} color versions, '
                     f'chosen at the setup screen and saved as <code>color_version</code>. A version changes only which real color '
                     f'plays each color role (file number in brackets); across the versions every color plays every role once. '
                     f'Shapes, trials and strategies are the same in every version.</p>'
                     f'<div class="vwrap"><table class="vtable"><thead><tr><th>Role</th>{head}</tr></thead><tbody>{body_rows}</tbody></table></div></section>')

    OUT.write_text(TEMPLATE.replace("{structure}", structure).replace("{legend}", legend)
                   .replace("{body}", body).replace("{versions}", version_table))
    print(f"wrote {OUT.name}")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trial Types and Strategies</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#F6F6F4;--panel:#FFFFFF;--ink:#1D1F21;--muted:#5C6166;--line:#D7D9DB;--canvas:#EDEDEB}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){--bg:#16181A;--panel:#202326;--ink:#ECEDEE;--muted:#A2A7AC;--line:#373B3F;--canvas:#2A2D30;color-scheme:dark}
}
:root[data-theme="dark"]{--bg:#16181A;--panel:#202326;--ink:#ECEDEE;--muted:#A2A7AC;--line:#373B3F;--canvas:#2A2D30;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Atkinson Hyperlegible",system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:28px 16px 48px}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:20px;margin:0 0 2px}
h3{font-size:15px;margin:0 0 2px}
p{margin:0}
.sub,.note{color:var(--muted)}
.note{margin-bottom:14px}
section,.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:20px}
.kids{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-top:10px}
.kid{background:var(--canvas);border-radius:10px;padding:10px 12px}
.figs{display:flex;flex-wrap:wrap;gap:2px;margin:6px 0}
.figs svg{background:#fff;border-radius:4px}
.stat{font-size:13px;color:var(--muted)}
.legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:6px 18px;margin-top:10px}
.leg{display:flex;gap:8px;align-items:baseline;font-size:14px}
.pill{display:inline-block;font-size:12px;font-weight:700;line-height:1.3;padding:2px 7px;border-radius:6px;margin:2px 2px 0 0;
  color:var(--ink);background:color-mix(in srgb,var(--c) 18%,var(--panel));border:1px solid color-mix(in srgb,var(--c) 70%,var(--panel));white-space:nowrap}
.trial{display:grid;grid-template-columns:minmax(220px,300px) 1fr;gap:16px;padding:16px 0;border-top:1px solid var(--line)}
.what p{color:var(--muted);font-size:14px}
.stim{display:flex;gap:10px;align-items:center;margin-top:8px}
.stim svg,.blank{background:#fff;border-radius:8px;flex:none}
.blank{width:84px;height:84px;display:grid;place-items:center;font-size:12px;color:#888;border:1px dashed #bbb;background:transparent}
.prompt{font-weight:700}
.q{font-size:14px}
.id{font-size:12px;color:var(--muted)}
.opts{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;align-items:start}
.opt{text-align:center}
.sw{height:44px;border-radius:8px;border:1px solid var(--line)}
.code{font-size:13px;font-weight:700;margin:4px 0 2px}
.why{font-size:12px;color:var(--muted);margin-top:4px;line-height:1.35}
.vwrap{overflow-x:auto}
.vtable{border-collapse:collapse;width:100%;font-size:14px}
.vtable th,.vtable td{border-top:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:middle;white-space:nowrap}
.vtable thead th{border-top:none;color:var(--muted);font-weight:700}
.vjob{font-weight:400;font-size:12px;color:var(--muted);white-space:normal;max-width:220px}
.vsw{display:inline-block;width:18px;height:18px;border-radius:4px;border:1px solid var(--line);vertical-align:middle;margin-right:6px}
.vnum{color:var(--muted);font-size:12px}
@media (max-width:760px){
  .trial{grid-template-columns:1fr}
  .opts{grid-template-columns:repeat(3,minmax(0,1fr))}
}
</style>
</head>
<body>
<div class="wrap">
<h1>Trial types and strategies</h1>
<p class="sub">Every prediction trial and color memory question in pilot 2 (high nameability), grouped by the kid's category structure. Colors are color version 1 of 5; the versions only change which real color plays each role, so the strategies are the same in every version. Under each answer option: its color code, the strategy it maps to (the saved <code>strategy</code> column), and the answer key's specific reason. An option with two pills fits both strategies (saved joined with "-").</p>
<div class="card"><h2>What each kid drew</h2><div class="kids">{structure}</div></div>
<div class="card"><h2>Strategy codes</h2><div class="legend">{legend}</div></div>
{body}
{versions}
<p class="sub" style="margin-top:20px">Not shown: "Who drew this?" and "Which shape did the kid draw most often?", whose options are kids and shapes (strategies: correct, other_drawer_of_shape / never_drew_shape, named_kid_other_shape / never_drawn). Built by make_strategy_schematic.py from the experiment's trial lists. For the full walkthrough of the session (training, attention checks and every test trial), see kids_drawings_pilot2_demo.html.</p>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()

"""
Build kids_drawings_pilot2_demo.html: a self-contained walkthrough of the pilot 2 design
(like the advisor's trial demo) for sharing with the advisor and RAs.

Everything on the page comes from the real experiment files, so re-run
this after changing the design:
  training_trials.csv / test_trials.csv / design_roles.csv  structure, trials, answer keys
  images/*/shape_outlines/*.svg                                 traced shape outlines
  images/*/colors/*.png                                         color values
  experiment.js                                                 block/check/timing/demo settings

The page layout and behavior live in overview_template.html; this script
only fills in its data.

Usage: python3 make_overview.py
"""

from pathlib import Path
import csv
import json
import re

from PIL import Image

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "overview_template.html"
OUT = ROOT / "kids_drawings_pilot2_demo.html"

CONDITION_LABELS = {"high_nameability": "High nameability", "low_nameability": "Low nameability"}

SETTINGS = {
    "trainingBlocks": "TRAINING_BLOCKS",
    "drawingMs": "TRAINING_DRAWING_MS",
    "gapMs": "TRAINING_GAP_MS",
    "checksPerBlock": "ONE_BACK_CHECKS_PER_BLOCK",
    "maxRotation": "JITTER_MAX_ROTATION_DEG",
    "demoDrawings": "DEMO_TRAINING_COUNT",
    "demoChecks": "DEMO_CHECKS",
    "demoTests": "DEMO_TEST_COUNT",
}


def read_csv(name):
    with open(ROOT / name, newline="") as f:
        return list(csv.DictReader(f))


def read_settings():
    source = (ROOT / "experiment.js").read_text()
    values = {}
    for key, const in SETTINGS.items():
        match = re.search(rf"^const {const} = ([\d.]+);", source, re.M)
        assert match, f"{const} not found in experiment.js"
        values[key] = float(match.group(1)) if "." in match.group(1) else int(match.group(1))
    return values


def read_svg_path(path):
    svg = path.read_text()
    return {
        "d": re.search(r' d="([^"]+)"', svg).group(1),
        "w": float(re.search(r'stroke-width="([\d.]+)"', svg).group(1)),
    }


def swatch_hex(path):
    image = Image.open(path).convert("RGB")
    return "#%02X%02X%02X" % image.getpixel((image.width // 2, image.height // 2))


def main():
    training = read_csv("training_trials.csv")
    tests = read_csv("test_trials.csv")
    roles = read_csv("design_roles.csv")

    # The structure and test trials are the same in every condition (in S/C
    # codes), so take them from the first one.
    first = training[0]["design"]
    data = {
        "settings": read_settings(),
        "training": [dict(kid=r["kid"], shape=r["shape"], color=r["color"]) for r in training if r["design"] == first],
        "tests": [],
        "conditions": {},
    }

    for r in (t for t in tests if t["design"] == first):
        options, i = [], 1
        while r.get(f"opt{i}"):
            options.append({"code": r[f"opt{i}"], "key": r[f"key_opt{i}"]})
            i += 1
        data["tests"].append({k: r[k] for k in (
            "id", "test_type", "kid", "shape", "prompt", "question", "response_type",
            "figure_color", "correct_answer", "ans_category", "ans_within_conjunction",
            "ans_shape_based", "ans_as_if_other_kid", "diagnostic_for")} | {"options": options})

    for r in roles:
        condition = data["conditions"].setdefault(r["condition"], {
            "label": CONDITION_LABELS.get(r["condition"], r["condition"]), "shapes": {}, "colors": {}})
        image_dir = ROOT / "images" / r["condition"]
        if r["role"].startswith("S"):
            shape = read_svg_path(image_dir / "shape_outlines" / f"{r['stimulus_id']}.svg")
            shape |= {"id": r["stimulus_id"], "num": int(re.search(r"(\d+)$", r["stimulus_id"]).group(1))}
            condition["shapes"][r["role"]] = shape
        else:
            condition["colors"][r["role"]] = {
                "id": r["stimulus_id"], "hex": swatch_hex(image_dir / "colors" / f"{r['stimulus_id']}.png")}

    page = TEMPLATE.read_text().replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    OUT.write_text(page)
    print(f"wrote {OUT.name} ({len(data['training'])} training drawings, {len(data['tests'])} test trials, "
          f"{len(data['conditions'])} conditions)")


if __name__ == "__main__":
    main()

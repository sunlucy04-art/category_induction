"""
Generate the pilot 2 trial lists from the advisor's one-block demo design.

The category structure (which kid draws which shape in which color) comes
from advisor_demo/training_trials_1block.csv, written in abstract codes:
3 kids, shapes S1-S4, colors C1-C5. Every participant sees exactly that
structure. This script fills it with real stimuli: the shape roles are
fixed (SHAPE_ROLES below, same shape numbers in both conditions), and the
condition's 5 colors are assigned to the C1-C5 roles in COLOR_VERSIONS
different ways (no color keeps its role from one version to the next).
Each participant gets one version.

Test trials per version: the advisor's 13 from
advisor_demo/make_test_trials.py, plus memory questions about every kid
(see memory_trials below).

Outputs (read by experiment.js):
  training_trials.csv  the 24 training drawings of every version
  test_trials.csv      the test trials of every version
  design_versions.csv  which shape/color fills each S/C role in each version
                       (for analysis; not read by the experiment)

Re-run whenever the template, the stimuli, or the settings below change.
"""

from collections import Counter
from pathlib import Path
import csv
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "advisor_demo/training_trials_1block.csv"
MAKE_TEST_TRIALS = ROOT / "advisor_demo/make_test_trials.py"

# Fixed so the same design is produced every time this is run.
DESIGN_SEED = 2026

# Which shape number fills each of the template's shape roles, in both
# conditions (e.g. 13 -> high_shape13 / low_shape13):
#   S1  drawn only by Lucy (mostly in C5)
#   S2  drawn only by Sam (mostly in C5)
#   S3  drawn by every kid, each in their usual color
#   S4  drawn only by Ana, always in C4
SHAPE_ROLES = {"S1": 13, "S2": 1, "S3": 10, "S4": 7}

# Number of different color-to-role assignments per condition.
COLOR_VERSIONS = 2

CONDITIONS = {
    "high_nameability": "images/high_nameability",
    "low_nameability": "images/low_nameability",
}


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    # Rows can have different columns (e.g. 3 vs 5 response options), so the
    # header is every column in first-seen order and missing cells are blank.
    fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)


def assign_color_roles(rng, colors, previous):
    # Shuffle colors onto C1-C5; for later versions, retry until no color
    # keeps the role it had in the previous version.
    while True:
        roles = rng.sample(colors, len(colors))
        if previous is None or all(a != b for a, b in zip(roles, previous)):
            return roles


def make_test_trials(training_rows):
    with tempfile.TemporaryDirectory() as tmp:
        train_path, test_path = Path(tmp) / "train.csv", Path(tmp) / "test.csv"
        write_csv(train_path, training_rows)
        subprocess.run([sys.executable, str(MAKE_TEST_TRIALS), str(train_path), str(test_path)],
                       check=True, stdout=subprocess.DEVNULL)
        return read_csv(test_path)


def mode(counter):
    return counter.most_common(1)[0][0]


def memory_trials(rows, first_id):
    """Memory questions about the training drawings, for every kid:
      who_drew             a training drawing (shape in the kid's color for it): who drew it?
      memory_probe         kid + shape: what color did the kid use for it?
                           (the advisor's script already makes Ana's; this adds the others)
      most_frequent_shape  which shape did the kid draw most often?
    """
    kids = list(dict.fromkeys(r["kid"] for r in rows))
    colors = sorted({r["color"] for r in rows})
    shapes = sorted({r["shape"] for r in rows})
    colors_of = lambda kid, shape: Counter(r["color"] for r in rows if r["kid"] == kid and r["shape"] == shape)
    usual = {k: mode(Counter(r["color"] for r in rows if r["kid"] == k)) for k in kids}
    shapes_of = {k: Counter(r["shape"] for r in rows if r["kid"] == k) for k in kids}

    out = []
    def add(test_type, kid, shape, prompt, question, response_type, options, keys, correct, figure_color="", diag=""):
        out.append(dict(id=f"T{first_id + len(out):02d}", test_type=test_type, kid=kid, shape=shape, token="NA",
                        prompt=prompt, question=question, ans_category="NA", ans_within_conjunction="NA",
                        ans_shape_based="NA", ans_as_if_other_kid="NA", diagnostic_for=diag,
                        **{f"opt{i}": o for i, o in enumerate(options, 1)},
                        **{f"key_opt{i}": keys[o] for i, o in enumerate(options, 1)},
                        correct_answer=correct, response_type=response_type, figure_color=figure_color))

    for kid in kids:
        for shape in shapes_of[kid]:
            color = mode(colors_of(kid, shape))
            keys = {}
            for other in kids:
                if other == kid: keys[other] = "correct"
                elif shape in shapes_of[other]: keys[other] = f"also drew {shape}s, but in {mode(colors_of(other, shape))}"
                elif usual[other] == color: keys[other] = f"{other}'s usual color, but never drew an {shape}"
                else: keys[other] = f"never drew an {shape}"
            add("who_drew", "none", shape, "You saw this drawing earlier.", "Who drew this?", "kid", kids, keys, kid,
                figure_color=color, diag=f"memory for who drew {kid}'s {shape}s")

    for kid in kids:
        for shape in shapes_of[kid]:
            if kid == kids[-1]:
                continue  # the advisor's script already made these (Ana's) memory probes
            mc, keys = colors_of(kid, shape), {}
            n, total = mc[mode(mc)], sum(mc.values())
            for c in colors:
                others = [k for k in kids if k != kid and usual[k] == c]
                if c == mode(mc): keys[c] = f"correct: {'all ' if n == total else ''}{n} of {kid}'s {total} {shape}s"
                elif mc[c]: keys[c] = f"{kid}'s color on {mc[c]} of {total} {shape}s"
                elif others: keys[c] = f"{others[0]}'s usual color"
                elif c == usual[kid]: keys[c] = f"{kid}'s usual, but never on an {shape}"
                else: keys[c] = f"never used by {kid} on an {shape}"
            add("memory_probe", kid, shape, f"{kid} drew this shape earlier.", f"What color did {kid} use for this shape?",
                "color", colors, keys, mode(mc), diag=f"memory for the color of {kid}'s {shape}s")

    for kid in kids:
        sc, total = shapes_of[kid], sum(shapes_of[kid].values())
        keys = {s: (f"correct: {sc[s]} of {kid}'s {total}" if s == mode(sc) else
                    f"{kid}'s other shape ({sc[s]} of {total})" if sc[s] else f"never drawn by {kid}") for s in shapes}
        add("most_frequent_shape", kid, "none", "", f"Which shape did {kid} draw most often?", "shape", shapes, keys,
            mode(sc), diag=f"memory for {kid}'s most frequent shape")

    return out


def main():
    rng = random.Random(DESIGN_SEED)
    template = read_csv(TEMPLATE)
    assert set(SHAPE_ROLES) == {r["shape"] for r in template}, "SHAPE_ROLES must cover the template's shapes"
    color_codes = sorted({r["color"] for r in template})

    training_out, test_out, design_out = [], [], []

    for condition, image_dir in CONDITIONS.items():
        prefix = condition.split("_")[0]
        shape_of = {code: f"{prefix}_shape{n}" for code, n in SHAPE_ROLES.items()}
        for shape_id in shape_of.values():
            assert (ROOT / image_dir / "shape_outlines" / f"{shape_id}.png").exists(), f"missing {shape_id}"
        colors = sorted(p.stem for p in (ROOT / image_dir / "colors").glob("*.png"))
        assert len(colors) == len(color_codes), f"{condition}: need {len(color_codes)} colors, found {len(colors)}"

        previous_colors = None
        for v in range(COLOR_VERSIONS):
            design = f"{condition}_v{v + 1}"
            previous_colors = assign_color_roles(rng, colors, previous_colors)
            color_of = dict(zip(color_codes, previous_colors))
            # Drawings use the traced vector (SVG) versions made by
            # prepare_nameability_stimuli.py, which stay crisp when scaled/rotated.
            outline = lambda code: f"{image_dir}/shape_outlines/{shape_of[code]}.svg"
            swatch = lambda code: f"{image_dir}/colors/{color_of[code]}.png"
            composite = lambda s, c: f"{image_dir}/all_shapes/{shape_of[s]}_{color_of[c]}.svg"

            for role, stimulus_id in {**shape_of, **color_of}.items():
                design_out.append(dict(condition=condition, design=design, role=role, stimulus_id=stimulus_id))

            for r in template:
                training_out.append(dict(
                    condition=condition, design=design, **r,
                    shape_id=shape_of[r["shape"]], color_id=color_of[r["color"]],
                    image=composite(r["shape"], r["color"]),
                    color_image=swatch(r["color"]), shape_image=outline(r["shape"]),
                ))

            tests = make_test_trials(template)
            for t in tests:
                t.update(response_type="color", figure_color="", correct_answer="")
                if t["test_type"] == "memory_probe":
                    t["prompt"] = f"{t['kid']} drew this shape earlier."
                    t["question"] = f"What color did {t['kid']} use for this shape?"
                    t["correct_answer"] = t["ans_shape_based"].split(" ")[0]
            tests += memory_trials(template, len(tests) + 1)

            for t in tests:
                if t["test_type"] == "who_drew":
                    figure = composite(t["shape"], t["figure_color"])
                elif t["shape"] in shape_of:
                    figure = outline(t["shape"])
                else:
                    figure = ""
                row = dict(condition=condition, design=design, **t,
                           shape_id=shape_of.get(t["shape"], ""), figure_image=figure)
                i = 1
                while f"opt{i}" in t:
                    code = t[f"opt{i}"]
                    if t["response_type"] == "color":
                        row[f"opt{i}_id"], row[f"opt{i}_image"] = color_of[code], swatch(code)
                    elif t["response_type"] == "shape":
                        row[f"opt{i}_id"], row[f"opt{i}_image"] = shape_of[code], outline(code)
                    else:
                        row[f"opt{i}_id"], row[f"opt{i}_image"] = code, ""
                    i += 1
                test_out.append(row)

    write_csv(ROOT / "training_trials.csv", training_out)
    write_csv(ROOT / "test_trials.csv", test_out)
    write_csv(ROOT / "design_versions.csv", design_out)
    print(f"wrote {len(training_out)} training rows and {len(test_out)} test rows "
          f"for {len({r['design'] for r in training_out})} design versions")


if __name__ == "__main__":
    main()

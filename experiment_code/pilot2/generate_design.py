"""
Generate the pilot 2 trial lists from the advisor's one-block demo design.

The category structure (which kid draws which shape in which color) comes
from advisor_demo/training_trials_1block.csv, written in abstract codes:
3 kids, shapes S1-S4, colors C1-C5. Every participant sees exactly that
structure. This script fills it with real stimuli. As in the advisor's
demo, the roles are fixed for everyone (no counterbalancing):
SHAPE_ROLES and COLOR_ROLES below.

Test trials: the advisor's 13 from advisor_demo/make_test_trials.py, the 8
prediction trials for the kid + shape pairings those don't use (see
extra_prediction_trials), and memory questions about every kid (see
memory_trials).

Outputs (read by experiment.js):
  training_trials.csv  the 24 training drawings, per condition
  test_trials.csv      the test trials, per condition
  design_roles.csv  which shape/color fills each S/C role per condition
                       (for analysis; not read by the experiment)

Re-run whenever the template, the stimuli, or the settings below change.
"""

from collections import Counter
from pathlib import Path
import csv
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "advisor_demo/training_trials_1block.csv"
MAKE_TEST_TRIALS = ROOT / "advisor_demo/make_test_trials.py"

# Which shape number fills each of the template's shape roles, in both
# conditions (e.g. 13 -> high_shape13 / low_shape13):
#   S1  drawn only by Lucy (mostly in C5)
#   S2  drawn only by Sam (mostly in C5)
#   S3  drawn by every kid, each in their usual color
#   S4  drawn only by Ana, always in C4
SHAPE_ROLES = {"S1": 13, "S2": 1, "S3": 10, "S4": 7}

# Which color fills each color role, matched to the advisor's demo colors
# as closely as our sets allow:
#   C1 Lucy's usual, C2 Sam's usual, C3 Ana's usual,
#   C4 every S4 (Ana's own shape), C5 2 of 3 of Lucy's S1s and Sam's S2s
COLOR_ROLES = {
    # red, blue, yellow, orange (demo: green, not in our set), purple
    "high_nameability": {"C1": "high_color1", "C2": "high_color4", "C3": "high_color3",
                         "C4": "high_color2", "C5": "high_color5"},
    # dusty pink, slate, terracotta, olive, pale lime
    # (demo: mauve, teal, tan, olive, lavender)
    "low_nameability": {"C1": "low_color1", "C2": "low_color10", "C3": "low_color2",
                        "C4": "low_color3", "C5": "low_color6"},
}

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


def make_test_trials(training_rows):
    with tempfile.TemporaryDirectory() as tmp:
        train_path, test_path = Path(tmp) / "train.csv", Path(tmp) / "test.csv"
        write_csv(train_path, training_rows)
        subprocess.run([sys.executable, str(MAKE_TEST_TRIALS), str(train_path), str(test_path)],
                       check=True, stdout=subprocess.DEVNULL)
        return read_csv(test_path)


def mode(counter):
    return counter.most_common(1)[0][0]


def extra_prediction_trials(rows, first_id):
    """Prediction trials for the kid + shape pairings the advisor's 13 don't
    use, so that every pairing is tested once and nothing is repeated:
      cross_category_conflict  Lucy + S2, Sam + S1 (the other kid's own shape; no Ana
                               cross-category trials, which aren't meaningful)
      classic_disagree         Ana + S4 (her own shape, never in her usual color)
      agree                    Ana + S3
      kid_not_named            S1, S2 (one kid's own shape), S3 (every kid's shape)
    Answer keys follow advisor_demo/make_test_trials.py's wording for each type.
    """
    kids = list(dict.fromkeys(r["kid"] for r in rows))
    colors = sorted({r["color"] for r in rows})
    shapes = sorted({r["shape"] for r in rows})
    cnt = lambda kid=None, shape=None: Counter(
        r["color"] for r in rows if kid in (None, r["kid"]) and shape in (None, r["shape"]))
    usual = {k: mode(cnt(k)) for k in kids}
    drawers = {s: [k for k in kids if cnt(k, s)] for s in shapes}
    frac = lambda c, col: f"{c[col]} of {sum(c.values())}"

    def where(col):
        return " and ".join(f"{s}s" for s in sorted({r["shape"] for r in rows if r["color"] == col}))

    def base_key(kid):
        # Same labels as make_test_trials.py's base_key.
        key, mine = {}, cnt(kid)
        for col in colors:
            others = [k for k in kids if k != kid and usual[k] == col]
            if col == usual[kid]: key[col] = f"{kid}'s usual ({frac(mine, col)})"
            elif others: key[col] = f"{others[0]}'s usual color"
            elif mine[col]: key[col] = f"{kid}'s other color ({frac(mine, col)}, all {where(col)})"
            else: key[col] = f"never used by {kid} (only on {where(col)})"
        return key

    out = []
    def add(test_type, kid, shape, cat, conj, shp, asif, diag, key):
        prompt = f"{kid} made this new drawing." if kid != "none" else "Someone made this new drawing."
        out.append(dict(id=f"T{first_id + len(out):02d}", test_type=test_type, kid=kid, shape=shape, token="NA",
                        prompt=prompt, question="What color do you think it is?", ans_category=cat,
                        ans_within_conjunction=conj, ans_shape_based=shp, ans_as_if_other_kid=asif,
                        diagnostic_for=diag, **{f"opt{i}": c for i, c in enumerate(colors, 1)},
                        **{f"key_opt{i}": key[c] for i, c in enumerate(colors, 1)},
                        response_type="color", figure_color="", correct_answer=""))

    lucy, sam, ana = kids

    for kid, shape in [(lucy, "S2"), (sam, "S1")]:
        sc, other = cnt(shape=shape), drawers[shape][0]
        key = base_key(kid)
        key[usual[kid]] = f"{kid}'s usual (category answer)"
        key[mode(sc)] = f"{sc[mode(sc)]} of the {sum(sc.values())} {shape}s were {mode(sc)} (shape-based answer)"
        key[usual[other]] = f"{other}'s usual (as if {other} drew it)"
        add("cross_category_conflict", kid, shape, usual[kid], "NA", mode(sc), usual[other],
            "category membership vs shape", key)

    dc = cnt(ana, "S4")
    key = base_key(ana)
    key[usual[ana]] = f"{ana}'s usual (category answer)"
    key[mode(dc)] = f"{dc[mode(dc)]} of {ana}'s {sum(dc.values())} S4s (conjunction answer)"
    add("classic_disagree", ana, "S4", usual[ana], mode(dc), mode(cnt(shape="S4")), "NA",
        "category summary vs within-category conditioning", key)

    key = base_key(ana)
    key[usual[ana]] = f"{ana}'s usual, and all of {ana}'s S3s"
    add("agree", ana, "S3", usual[ana], mode(cnt(ana, "S3")), "mixed", "NA", "learning/attention check", key)

    for shape in ["S1", "S2"]:
        owner, sc = drawers[shape][0], cnt(shape=shape)
        key = {c: f"{k}'s usual color" for k, c in usual.items()}
        key.update({c: f"never on an {shape}" for c in colors if c not in key})
        key[usual[owner]] = f"{owner}'s usual (guess {owner}, use {owner}'s usual color)"
        key[mode(sc)] = f"{sc[mode(sc)]} of the {sum(sc.values())} {shape}s were {mode(sc)} (shape-based answer)"
        add("kid_not_named", "none", shape, f"{usual[owner]} (if {owner} is guessed)", "NA", mode(sc), "NA",
            f"uncertain kid: guess {owner} and use the usual color vs shape-based", key)

    # S3 is drawn by every kid in their own usual color, so there is no
    # single kid to guess and no shape-based answer: a control.
    key = {c: f"{k}'s usual color (all of {k}'s S3s)" for k, c in usual.items()}
    key.update({c: "never on an S3" for c in colors if c not in key})
    add("kid_not_named", "none", "S3", "NA", "NA", "mixed", "NA",
        "control: shape drawn by every kid, each in their usual color", key)

    return out


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
    template = read_csv(TEMPLATE)
    assert set(SHAPE_ROLES) == {r["shape"] for r in template}, "SHAPE_ROLES must cover the template's shapes"
    color_codes = sorted({r["color"] for r in template})

    training_out, test_out, design_out = [], [], []

    for condition, image_dir in CONDITIONS.items():
        prefix = condition.split("_")[0]
        shape_of = {code: f"{prefix}_shape{n}" for code, n in SHAPE_ROLES.items()}
        for shape_id in shape_of.values():
            assert (ROOT / image_dir / "shape_outlines" / f"{shape_id}.png").exists(), f"missing {shape_id}"
        color_of = COLOR_ROLES[condition]
        assert set(color_of) == set(color_codes), f"{condition}: COLOR_ROLES must cover {color_codes}"
        for color_id in color_of.values():
            assert (ROOT / image_dir / "colors" / f"{color_id}.png").exists(), f"missing {color_id}"

        design = condition
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
        # Drop the advisor's cross-category trial for Ana (Ana + S1): only
        # Lucy's and Sam's cross-category trials are meaningful. IDs keep the
        # advisor's numbering (so T10 is skipped); new trials start at T14.
        next_id = len(tests) + 1
        ana = list(dict.fromkeys(r["kid"] for r in template))[-1]
        tests = [t for t in tests if not (t["test_type"] == "cross_category_conflict" and t["kid"] == ana)]
        extra = extra_prediction_trials(template, next_id)
        tests += extra + memory_trials(template, next_id + len(extra))

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
    write_csv(ROOT / "design_roles.csv", design_out)
    print(f"wrote {len(training_out)} training rows and {len(test_out)} test rows "
          f"for {len({r['design'] for r in training_out})} conditions")


if __name__ == "__main__":
    main()

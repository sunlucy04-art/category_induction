"""
Generate the pilot 2 v2 trial lists from the advisor's one-block demo design.

The category structure (which kid likes drawings of which shape in which color) comes
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
  attention_checks.csv the fixed set of attention checks (see attention_checks)
  shape_color_roles.csv  which shape/color file fills each S/C role per
                         condition, and the role's job in the design
                         (for analysis; not read by the experiment)

Every test option also gets a strategy code (strategy_opt1..N, see
option_strategy) naming what choosing it reflects, in terms of the trial's
roles rather than particular kids or colors, so functionally equivalent
trials share codes.

Re-run whenever the template, the stimuli, or the settings below change.
"""

from collections import Counter
from pathlib import Path
import csv
import random
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "advisor_demo/training_trials_1block.csv"
MAKE_TEST_TRIALS = ROOT / "advisor_demo/make_test_trials.py"

# Which shape number fills each of the template's shape roles (e.g. 13 ->
# low_shape13). The kids "like" drawings (the cover story): each kid's
# category is the set of drawings they like.
#   S1  liked only by Lucy (mostly in C5)
#   S2  liked only by Sam (mostly in C5)
#   S3  liked by every kid, each in their usual color
#   S4  liked only by Ana, always in C4
SHAPE_ROLES = {"S1": 13, "S2": 1, "S3": 10, "S4": 7}

# Pilot 2 v2 uses the less nameable shapes (low pool) with the more nameable
# colors (high pool): the nameable shapes had color associations that were
# too salient (e.g. an orange fox).
SHAPE_POOL = "low"

# Which color fills each color role, matched to the advisor's demo colors
# as closely as our sets allow:
#   C1 Lucy's usual, C2 Sam's usual, C3 Ana's usual,
#   C4 every S4 (Ana's own shape), C5 2 of 3 of Lucy's S1s and Sam's S2s
COLOR_ROLES = {
    # red, blue, yellow, orange (demo: green, not in our set), purple
    "low_shape_high_color": {"C1": "high_color1", "C2": "high_color4", "C3": "high_color3",
                             "C4": "high_color2", "C5": "high_color5"},
}

# What each role does in the design, for shape_color_roles.csv.
ROLE_JOBS = {
    "S1": "Lucy's own shape (only Lucy likes it, mostly in C5)",
    "S2": "Sam's own shape (only Sam likes it, mostly in C5)",
    "S3": "liked by every kid, each in their own most frequent color",
    "S4": "Ana's own shape (only Ana likes it, always in C4)",
    "C1": "Lucy's most frequent color",
    "C2": "Sam's most frequent color",
    "C3": "Ana's most frequent color",
    "C4": "the color of every S4",
    "C5": "the less frequent color on Lucy's S1s and Sam's S2s",
}
COLOR_NAMES = {
    "high_color1": "red", "high_color4": "blue", "high_color3": "yellow", "high_color2": "orange", "high_color5": "purple",
    "low_color1": "dusty pink", "low_color10": "slate", "low_color2": "terracotta", "low_color3": "olive", "low_color6": "pale lime",
}

# Color counterbalancing: participants get one of COLOR_VERSIONS versions
# (chosen at the experiment's setup screen) that shuffle which real color
# plays each color role. Version v shifts COLOR_ROLES' colors v - 1 places
# along C1..C5, a Latin square: across the versions, every color plays every
# role exactly once. Version 1 is COLOR_ROLES as written. Shapes are not
# counterbalanced.
COLOR_VERSIONS = 5


def color_version(base, version):
    codes = sorted(base)
    return {code: base[codes[(i + version - 1) % len(codes)]] for i, code in enumerate(codes)}


CONDITIONS = {
    "low_shape_high_color": "images/low_shape_high_color",
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


def participant_wording(test_type, kid, shape):
    """The prompt and question participants see on a test trial. Cover story:
    the kids like (prefer) drawings; they don't make them."""
    if test_type == "who_liked":
        return "You saw this drawing earlier.", "Who liked this drawing?"
    if test_type == "memory_probe":
        return f"{kid} liked this shape earlier.", "What color was it?"
    if test_type == "who_liked_shape":
        return "", "Who liked this shape?"
    if test_type == "who_liked_color":
        return "", "Who liked this color?"
    if test_type == "color_liked_only_by_kid":
        return "", f"Which color did only {kid} like?"
    if test_type == "shape_liked_by_all":
        return "", "Which shape did all the kids like?"
    if test_type == "shape_liked_only_by_kid":
        return "", f"Which shape did only {kid} like?"
    if kid == "none":
        prompt = "Someone likes this new drawing."
    elif shape == "none":
        prompt = f"{kid} likes a new drawing."
    else:
        prompt = f"{kid} likes this new drawing."
    return prompt, "What color do you think it is?"


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
    likers = {s: [k for k in kids if cnt(k, s)] for s in shapes}
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
            else: key[col] = f"never in {kid}'s drawings (only on {where(col)})"
        return key

    out = []
    def add(test_type, kid, shape, cat, conj, shp, asif, diag, key):
        prompt, question = participant_wording(test_type, kid, shape)
        out.append(dict(id=f"T{first_id + len(out):02d}", test_type=test_type, kid=kid, shape=shape, token="NA",
                        prompt=prompt, question=question, ans_category=cat,
                        ans_within_conjunction=conj, ans_shape_based=shp, ans_as_if_other_kid=asif,
                        diagnostic_for=diag, **{f"opt{i}": c for i, c in enumerate(colors, 1)},
                        **{f"key_opt{i}": key[c] for i, c in enumerate(colors, 1)},
                        response_type="color", figure_color="", correct_answer=""))

    lucy, sam, ana = kids

    for kid, shape in [(lucy, "S2"), (sam, "S1")]:
        sc, other = cnt(shape=shape), likers[shape][0]
        key = base_key(kid)
        key[usual[kid]] = f"{kid}'s usual"
        key[mode(sc)] = f"{sc[mode(sc)]} of the {sum(sc.values())} {shape}s were {mode(sc)}"
        key[usual[other]] = f"{other}'s usual"
        add("cross_category_conflict", kid, shape, usual[kid], "NA", mode(sc), usual[other], "", key)

    dc = cnt(ana, "S4")
    key = base_key(ana)
    key[usual[ana]] = f"{ana}'s usual"
    key[mode(dc)] = f"{dc[mode(dc)]} of {ana}'s {sum(dc.values())} S4s"
    add("classic_disagree", ana, "S4", usual[ana], mode(dc), mode(cnt(shape="S4")), "NA", "", key)

    key = base_key(ana)
    key[usual[ana]] = f"{ana}'s usual, and all of {ana}'s S3s"
    add("agree", ana, "S3", usual[ana], mode(cnt(ana, "S3")), "mixed", "NA", "", key)

    for shape in ["S1", "S2"]:
        owner, sc = likers[shape][0], cnt(shape=shape)
        key = {c: f"{k}'s usual color" for k, c in usual.items()}
        key.update({c: f"never on an {shape}" for c in colors if c not in key})
        key[usual[owner]] = f"{owner}'s usual"
        key[mode(sc)] = f"{sc[mode(sc)]} of the {sum(sc.values())} {shape}s were {mode(sc)}"
        add("kid_not_named", "none", shape, f"{usual[owner]} (if {owner} is guessed)", "NA", mode(sc), "NA", "", key)

    # S3 is liked by every kid in their own usual color, so there is no
    # single kid to guess and no single shape color: a control.
    key = {c: f"{k}'s usual color (all of {k}'s S3s)" for k, c in usual.items()}
    key.update({c: "never on an S3" for c in colors if c not in key})
    add("kid_not_named", "none", "S3", "NA", "NA", "mixed", "NA", "", key)

    return out


def memory_trials(rows, first_id):
    """Memory questions about the training drawings, for every kid:
      who_liked            every distinct training drawing (each kid's shape-color
                           combinations, 8 in all): who liked it?
      memory_probe         kid + shape: what color was it? Only for shapes the kid
                           always liked in one color (each kid's S3, Ana's S4), so there
                           is one right answer. (The advisor's script already makes
                           Ana's; this adds Lucy's and Sam's S3.)
      shape_liked_by_all   which shape did all the kids like? (S3)
      shape_liked_only_by_kid
                           which shape did only this kid like? (the kid's own shape)
      who_liked_shape      an uncolored outline: who liked this shape? Only shapes one
                           kid liked (S1, S2, S4; S3 was liked by every kid)
      who_liked_color      a color swatch: who liked this color? Only colors one kid
                           liked (C1-C4; C5 was liked by Lucy and Sam)
      color_liked_only_by_kid
                           which color did only this kid like? Only kids with exactly
                           one such color (Lucy C1, Sam C2; Ana has two, C3 and C4)
    """
    kids = list(dict.fromkeys(r["kid"] for r in rows))
    colors = sorted({r["color"] for r in rows})
    shapes = sorted({r["shape"] for r in rows})
    colors_of = lambda kid, shape: Counter(r["color"] for r in rows if r["kid"] == kid and r["shape"] == shape)
    usual = {k: mode(Counter(r["color"] for r in rows if r["kid"] == k)) for k in kids}
    shapes_of = {k: Counter(r["shape"] for r in rows if r["kid"] == k) for k in kids}

    out = []
    def add(test_type, kid, shape, response_type, options, keys, correct, figure_color="", diag=""):
        prompt, question = participant_wording(test_type, kid, shape)
        out.append(dict(id=f"T{first_id + len(out):02d}", test_type=test_type, kid=kid, shape=shape, token="NA",
                        prompt=prompt, question=question, ans_category="NA", ans_within_conjunction="NA",
                        ans_shape_based="NA", ans_as_if_other_kid="NA", diagnostic_for=diag,
                        **{f"opt{i}": o for i, o in enumerate(options, 1)},
                        **{f"key_opt{i}": keys[o] for i, o in enumerate(options, 1)},
                        correct_answer=correct, response_type=response_type, figure_color=figure_color))

    for kid in kids:
        for shape, color in dict.fromkeys((r["shape"], r["color"]) for r in rows if r["kid"] == kid):
            keys = {}
            for other in kids:
                if other == kid: keys[other] = "correct"
                elif shape in shapes_of[other]: keys[other] = f"also liked {shape}s, but in {mode(colors_of(other, shape))}"
                elif usual[other] == color: keys[other] = f"{other}'s usual color, but never liked an {shape}"
                else: keys[other] = f"never liked an {shape}"
            add("who_liked", "none", shape, "kid", kids, keys, kid,
                figure_color=color, diag=f"memory for who liked {kid}'s {shape}s in {color}")

    for kid in kids:
        for shape in shapes_of[kid]:
            if kid == kids[-1]:
                continue  # the advisor's script already made these (Ana's) memory probes
            mc, keys = colors_of(kid, shape), {}
            if len(mc) > 1:
                continue  # the kid liked this shape in more than one color: no single right answer
            n, total = mc[mode(mc)], sum(mc.values())
            for c in colors:
                others = [k for k in kids if k != kid and usual[k] == c]
                if c == mode(mc): keys[c] = f"correct: {'all ' if n == total else ''}{n} of {kid}'s {total} {shape}s"
                elif mc[c]: keys[c] = f"{kid}'s color on {mc[c]} of {total} {shape}s"
                elif others: keys[c] = f"{others[0]}'s usual color"
                elif c == usual[kid]: keys[c] = f"{kid}'s usual, but never on an {shape}"
                else: keys[c] = f"never on {kid}'s {shape}s"
            add("memory_probe", kid, shape, "color", colors, keys, mode(mc),
                diag=f"memory for the color of {kid}'s {shape}s")

    likers_of = {s: [k for k in kids if shapes_of[k][s]] for s in shapes}
    shared = next(s for s in shapes if len(likers_of[s]) == len(kids))
    keys = {s: "correct" if s == shared else f"only {likers_of[s][0]} liked it" for s in shapes}
    add("shape_liked_by_all", "none", "none", "shape", shapes, keys, shared,
        diag="memory for the shape every kid liked")

    for kid in kids:
        own = next(s for s in shapes if likers_of[s] == [kid])
        keys = {s: ("correct" if s == own else "every kid liked it" if s == shared
                    else f"only {likers_of[s][0]} liked it") for s in shapes}
        add("shape_liked_only_by_kid", kid, "none", "shape", shapes, keys, own,
            diag=f"memory for the shape only {kid} liked")

    for s in shapes:
        if len(likers_of[s]) != 1:
            continue  # liked by every kid: no single right answer
        owner = likers_of[s][0]
        keys = {k: "correct" if k == owner else f"never liked {s}" for k in kids}
        add("who_liked_shape", "none", s, "kid", kids, keys, owner,
            diag=f"memory for which kid liked {s}")

    color_likers = {c: [k for k in kids if any(r["kid"] == k and r["color"] == c for r in rows)] for c in colors}
    for c in colors:
        if len(color_likers[c]) != 1:
            continue  # liked by more than one kid: no single right answer
        owner = color_likers[c][0]
        keys = {k: "correct" if k == owner else f"never liked {c}" for k in kids}
        add("who_liked_color", "none", "none", "kid", kids, keys, owner,
            figure_color=c, diag=f"memory for which kid liked {c}")

    for kid in kids:
        only = [c for c in colors if color_likers[c] == [kid]]
        if len(only) != 1:
            continue  # more than one color only this kid liked: no single right answer
        keys = {c: ("correct" if c == only[0]
                    else f"liked by {' and '.join(color_likers[c])}" if kid in color_likers[c]
                    else f"only {color_likers[c][0]} liked it" if len(color_likers[c]) == 1
                    else f"liked by {' and '.join(color_likers[c])}") for c in colors}
        add("color_liked_only_by_kid", kid, "none", "color", colors, keys, only[0],
            diag=f"memory for the color only {kid} liked")

    return out


def option_strategy(t, option, rows):
    """What choosing `option` on test trial `t` reflects, named by role
    (the named kid, the kid who likes the shape, any other kid), not by
    which kid or color it is, so functionally equivalent trials share codes.
    When an option fits more than one strategy, every one is listed, joined
    with "-" in the order below.

    Prediction trials (agree, classic_disagree, cross_category_conflict,
    category_only, kid_not_named):
      most_frequent_color_kid_match   the named kid's most frequent color
      conjunction_kid_match           the color this shape mostly had in the
                                      drawings the named kid liked (only for
                                      the named kid's own shapes)
      conjunction_other_kid           the color this shape mostly had, when a
                                      different kid than the one named liked
                                      it (no kid named: whoever liked it;
                                      none for S3, which has no single most
                                      common color)
      most_frequent_color_other_kid   the most frequent color of a kid who
                                      likes this shape, when the named kid
                                      doesn't ("as if that kid liked it"; no
                                      kid named: any kid who liked it)
      named_kid_other_color           a less frequent color in the named
                                      kid's drawings, never on this shape
    and, only when none of those fit:
      most_frequent_unrelated_kid     the most frequent color of a kid unrelated
                                      to this trial (not named, and never liked
                                      this shape)
      never_used                      never in the named kid's drawings (no
                                      kid named: never on this shape)
    memory_probe: correct (the named kid's color on this shape),
      most_frequent_color_kid_match, named_kid_other_color, then
      most_frequent_unrelated_kid / never_used.
    who_liked: correct, other_kid_liked_shape, never_liked_shape.
    shape_liked_by_all: correct, one_kid_only_shape (a shape only one kid liked).
    shape_liked_only_by_kid: correct, shape_liked_by_all (the shared shape),
      other_kid_only_shape (another kid's own shape).
    who_liked_shape: correct, never_liked_shape.
    who_liked_color: correct, never_liked_color.
    color_liked_only_by_kid: correct, shared_color (a color this kid liked but
      so did another kid), other_kid_only_color (a color only another kid
      liked).
    """
    kids = list(dict.fromkeys(r["kid"] for r in rows))
    usual = {k: mode(Counter(r["color"] for r in rows if r["kid"] == k)) for k in kids}
    kid, shape, test_type = t["kid"], t["shape"], t["test_type"]
    named = kid in usual
    likers = list(dict.fromkeys(r["kid"] for r in rows if r["shape"] == shape))

    if test_type == "who_liked":
        if option == t["correct_answer"]: return "correct"
        return "other_kid_liked_shape" if option in likers else "never_liked_shape"
    if test_type == "who_liked_shape":
        return "correct" if option == t["correct_answer"] else "never_liked_shape"
    if test_type == "who_liked_color":
        return "correct" if option == t["correct_answer"] else "never_liked_color"
    if test_type == "color_liked_only_by_kid":
        if option == t["correct_answer"]: return "correct"
        option_likers = {r["kid"] for r in rows if r["color"] == option}
        return "shared_color" if kid in option_likers else "other_kid_only_color"
    if test_type in ("shape_liked_by_all", "shape_liked_only_by_kid"):
        if option == t["correct_answer"]: return "correct"
        option_likers = {r["kid"] for r in rows if r["shape"] == option}
        if test_type == "shape_liked_by_all": return "one_kid_only_shape"
        return "shape_liked_by_all" if option_likers == set(kids) else "other_kid_only_shape"

    kid_colors = {r["color"] for r in rows if r["kid"] == kid}
    kid_shape_colors = Counter(r["color"] for r in rows if r["kid"] == kid and r["shape"] == shape)
    shape_colors = Counter(r["color"] for r in rows if r["shape"] == shape)
    top = shape_colors.most_common(2)
    shape_mode = top[0][0] if top and (len(top) == 1 or top[0][1] > top[1][1]) else None

    codes = []
    if test_type == "memory_probe":
        if option == t["correct_answer"]: codes.append("correct")
        if option == usual[kid]: codes.append("most_frequent_color_kid_match")
    else:
        if named and option == usual[kid]: codes.append("most_frequent_color_kid_match")
        if kid_shape_colors and option == mode(kid_shape_colors): codes.append("conjunction_kid_match")
        if kid not in likers:
            if option == shape_mode: codes.append("conjunction_other_kid")
            if option in {usual[d] for d in likers}: codes.append("most_frequent_color_other_kid")
    if named and option in kid_colors and option != usual[kid] and option not in kid_shape_colors:
        codes.append("named_kid_other_color")
    if not codes:
        codes.append("most_frequent_unrelated_kid" if option in usual.values() else "never_used")
    return "-".join(codes)


# The advisor's script tags its answer keys with strategy names, e.g.
# "Lucy's usual (category answer)": the strategy_opt codes name the strategy
# now, so the keys keep only the factual reason ("Lucy's usual").
STRATEGY_TAG = re.compile(r" \((category answer|conjunction answer|shape-based answer|as if \w+ drew it|guess \w+, use \w+'s usual color)\)$")


# What each prediction trial group pits against what, in strategy codes
# (replaces the advisor's diagnostic_for wording for these trials).
DIAGNOSTIC_FOR = {
    "agree": "baseline: most_frequent_color_kid_match and conjunction_kid_match are the same option",
    "classic_disagree": "most_frequent_color_kid_match vs conjunction_kid_match",
    "cross_category_unique_color": "most_frequent_color_kid_match vs conjunction_other_kid vs most_frequent_color_other_kid",
    "cross_category_shared_color": "most_frequent_color_kid_match vs conjunction_other_kid vs most_frequent_color_other_kid "
                                   "(conjunction_other_kid is also named_kid_other_color)",
    "category_only": "most_frequent_color_kid_match, with no shape shown",
    "kid_not_named": "most_frequent_color_other_kid vs conjunction_other_kid",
    "kid_not_named_control": "control: every kid likes this shape, each in their own most frequent color",
}


def trial_group(row):
    """Functionally equivalent test trials. test_type alone mixes a few that
    aren't, so those are split using the options' strategy codes:
      cross_category_unique_color  the shape's color is one the named kid
                                   never used (S4)
      cross_category_shared_color  it is also the named kid's own less
                                   frequent color, so choosing it is
                                   ambiguous (S1/S2)
      kid_not_named_control        no single kid likes the shape (S3)
      who_liked_shared_shape       other kids also liked this shape (S3)
      memory_probe_no_conflict     the correct color is also the kid's most
                                   frequent color (S3)
    Every other trial's group is its test_type.
    """
    strategies = [v for k, v in row.items() if k.startswith("strategy_opt")]
    test_type = row["test_type"]
    if test_type == "cross_category_conflict":
        return "cross_category_unique_color" if "conjunction_other_kid" in strategies else "cross_category_shared_color"
    if test_type == "kid_not_named" and "conjunction_other_kid" not in strategies:
        return "kid_not_named_control"
    if test_type == "who_liked":
        return "who_liked_shared_shape" if "other_kid_liked_shape" in strategies else "who_liked_unique_shape"
    if test_type == "memory_probe":
        return "memory_probe_no_conflict" if "correct-most_frequent_color_kid_match" in strategies else "memory_probe_conflict"
    return test_type


# Attention checks: a fixed set, the same for every participant, so each check
# can be compared across people. Every training drawing gets exactly one
# check (24 in all), in a fixed block and of a fixed type; only where it falls
# within its block differs between participants (the drawings are shuffled),
# and it always comes right after its drawing.
TRAINING_BLOCKS = 4
CHECK_TYPES = ["kid", "color", "shape"]
CHECK_SEED = 2026  # the list is drawn once with this seed, so it never changes


def attention_checks(rows):
    """One check per training drawing, balanced so every block has 6 checks,
    2 of each type and 2 per kid (a kid's two checks in a block are different
    types), and each kid gets each type 2-3 times over the session."""
    kids = list(dict.fromkeys(r["kid"] for r in rows))
    rng = random.Random(CHECK_SEED)
    while True:
        block_of = {}
        for kid in kids:
            ids = [r["id"] for r in rows if r["kid"] == kid]
            rng.shuffle(ids)
            per_block = len(ids) // TRAINING_BLOCKS
            for i, drawing in enumerate(ids):
                block_of[drawing] = i // per_block + 1
        type_of = {}
        for block in range(1, TRAINING_BLOCKS + 1):
            ids = [r["id"] for r in rows if block_of[r["id"]] == block]
            types = CHECK_TYPES * (len(ids) // len(CHECK_TYPES))
            rng.shuffle(types)
            type_of.update(zip(ids, types))
        kid_of = {r["id"]: r["kid"] for r in rows}
        same_type_in_block = any(
            len({type_of[d] for d in block_of if block_of[d] == b and kid_of[d] == kid}) < 2
            for b in range(1, TRAINING_BLOCKS + 1) for kid in kids)
        counts = Counter((kid_of[d], type_of[d]) for d in type_of)
        if not same_type_in_block and all(2 <= counts[(k, t)] <= 3 for k in kids for t in CHECK_TYPES):
            break
    order = sorted(rows, key=lambda r: (block_of[r["id"]], r["id"]))
    return [dict(check_id=f"AC{i:02d}", training_block=block_of[r["id"]], id=r["id"],
                 check_type=type_of[r["id"]], kid=r["kid"], shape_role=r["shape"], color_role=r["color"])
            for i, r in enumerate(order, 1)]


def main():
    template = read_csv(TEMPLATE)
    assert set(SHAPE_ROLES) == {r["shape"] for r in template}, "SHAPE_ROLES must cover the template's shapes"
    color_codes = sorted({r["color"] for r in template})

    training_out, test_out, roles_out = [], [], []

    for condition, image_dir in CONDITIONS.items():
        shape_of = {code: f"{SHAPE_POOL}_shape{n}" for code, n in SHAPE_ROLES.items()}
        for shape_id in shape_of.values():
            assert (ROOT / image_dir / "shape_outlines" / f"{shape_id}.png").exists(), f"missing {shape_id}"
        color_of = COLOR_ROLES[condition]
        assert set(color_of) == set(color_codes), f"{condition}: COLOR_ROLES must cover {color_codes}"
        for color_id in color_of.values():
            assert (ROOT / image_dir / "colors" / f"{color_id}.png").exists(), f"missing {color_id}"

        base_colors = color_of
        for version in range(1, COLOR_VERSIONS + 1):
            color_of = color_version(base_colors, version)
            design = condition
            # stimulus is the file name of what's on screen (the traced SVGs and
            # swatches made by prepare_nameability_stimuli.py): a filled drawing
            # (low_shape13_high_color5), an outline alone (low_shape13), a color
            # swatch alone (high_color5), or blank when nothing is shown. shape
            # and color are the file numbers (13, 5).
            number = lambda file_id: int(re.search(r"(\d+)$", file_id).group(1))
            shape_num = lambda code: number(shape_of[code]) if code in shape_of else ""
            color_num = lambda code: number(color_of[code]) if code in color_of else ""

            for role, file_id in {**shape_of, **color_of}.items():
                roles_out.append(dict(
                    condition=condition, color_version=version, role=role, kind="shape" if role.startswith("S") else "color",
                    number=number(file_id), file_name=file_id,
                    color_name=COLOR_NAMES.get(file_id, ""), job=ROLE_JOBS[role]))

            for r in template:
                training_out.append(dict(
                    condition=condition, design=design, color_version=version, id=r["id"],
                    stimulus=f"{shape_of[r['shape']]}_{color_of[r['color']]}",
                    kid=r["kid"], kid_usual_color=r["kid_usual_color"],
                    shape_role=r["shape"], shape=shape_num(r["shape"]),
                    color_role=r["color"], color=color_num(r["color"]),
                    token=r["token"], shape_description=r["shape_role"],
                ))

            tests = make_test_trials(template)
            for t in tests:
                t.update(response_type="color", figure_color="", correct_answer="")
                t["prompt"], t["question"] = participant_wording(t["test_type"], t["kid"], t["shape"])
                if t["test_type"] == "memory_probe":
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
                # What's on screen: a training drawing (who_liked), an uncolored
                # outline, a color swatch alone (who_liked_color), or nothing.
                shape, color = t["shape"], t["figure_color"]
                if shape in shape_of and color:
                    stimulus = f"{shape_of[shape]}_{color_of[color]}"
                elif shape in shape_of:
                    stimulus = shape_of[shape]
                elif color:
                    stimulus = color_of[color]
                else:
                    stimulus = ""
                row = dict(condition=condition, design=design, color_version=version, id=t["id"], stimulus=stimulus,
                           **{k: v for k, v in t.items() if k not in ("id", "shape", "figure_color")},
                           shape_role=shape, shape=shape_num(shape),
                           color_role=color, color=color_num(color))
                i = 1
                while f"opt{i}" in t:
                    code = t[f"opt{i}"]
                    row[f"strategy_opt{i}"] = option_strategy(t, code, template)
                    row[f"key_opt{i}"] = re.sub(r"never used by (\w+)", r"never in \1's drawings",
                                            STRATEGY_TAG.sub("", row[f"key_opt{i}"]))
                    i += 1
                row["trial_group"] = trial_group(row)
                row["diagnostic_for"] = DIAGNOSTIC_FOR.get(row["trial_group"], row["diagnostic_for"])
                test_out.append(row)

    write_csv(ROOT / "training_trials.csv", training_out)
    write_csv(ROOT / "test_trials.csv", test_out)
    write_csv(ROOT / "shape_color_roles.csv", roles_out)
    write_csv(ROOT / "attention_checks.csv", attention_checks(template))
    print(f"wrote {len(training_out)} training rows and {len(test_out)} test rows "
          f"for {len({r['design'] for r in training_out})} conditions x {COLOR_VERSIONS} color versions")


if __name__ == "__main__":
    main()

"""Generate the test-trial CSV from a training-block CSV.

Usage: python make_test_trials.py training_trials_1block.csv test_trials_1block.csv

Training CSV needs columns: kid, shape, token, color (one row per drawing).
Trial roles are inferred from the structure of the block, so kid names and
shape/color codes can change from block to block:
  link shape      drawn by one kid only, always in one color that isn't that kid's usual (S4)
  carrier kid     the kid who drew the link shape (Ana)
  disagree shape  drawn by one kid only, mostly in a color that isn't that kid's usual (S1, S2)
  common shape    drawn by every kid (S3)
"""
import csv, sys
from collections import Counter

rows = list(csv.DictReader(open(sys.argv[1])))
kids = list(dict.fromkeys(r["kid"] for r in rows))
colors = sorted({r["color"] for r in rows})
shapes = sorted({r["shape"] for r in rows})

def cnt(kid=None, shape=None):
    return Counter(r["color"] for r in rows if kid in (None, r["kid"]) and shape in (None, r["shape"]))
def mode(c): return c.most_common(1)[0][0]
usual = {k: mode(cnt(k)) for k in kids}
drawers = {s: {r["kid"] for r in rows if r["shape"] == s} for s in shapes}
owner = {s: next(iter(d)) for s, d in drawers.items() if len(d) == 1}

link = next(s for s, k in owner.items() if len(cnt(shape=s)) == 1 and mode(cnt(shape=s)) != usual[k])
carrier = owner[link]
disagree = {owner[s]: s for s in owner if s != link and mode(cnt(shape=s)) != usual[owner[s]]}
common = next(s for s in shapes if len(drawers[s]) == len(kids))
targets = [k for k in kids if k != carrier]

ntok = Counter({s: max(int(r["token"][1:]) for r in rows if r["shape"] == s) for s in shapes})
def new_token(s): ntok[s] += 1; return f"t{ntok[s]}"
def frac(c, col): return f"{c[col]} of {sum(c.values())}"
def where(col):
    on = sorted({r["shape"] for r in rows if r["color"] == col})
    return " and ".join(f"{s}s" for s in on)

def base_key(kid):
    """Label every color relative to the named kid."""
    key, mine = {}, cnt(kid)
    for col in colors:
        others = [k for k in kids if k != kid and usual[k] == col]
        if col == usual[kid]: key[col] = f"{kid}'s usual ({frac(mine, col)})"
        elif others: key[col] = f"{others[0]}'s usual color"
        elif mine[col]: key[col] = f"{kid}'s other color ({frac(mine, col)}, all {where(col)})"
        else: key[col] = f"never used by {kid} (only on {where(col)})"
    return key

out = []
def add(tt, kid, shape, prompt, q, cat, conj, shp, asif, diag, key):
    out.append(dict(id=f"T{len(out)+1:02d}", test_type=tt, kid=kid, shape=shape,
        token=new_token(shape) if shape != "none" else "NA", prompt=prompt, question=q,
        ans_category=cat, ans_within_conjunction=conj, ans_shape_based=shp, ans_as_if_other_kid=asif,
        diagnostic_for=diag, **{f"opt{i}": c for i, c in enumerate(colors, 1)},
        **{f"key_opt{i}": key[c] for i, c in enumerate(colors, 1)}))

NEW, MEM = "What color do you think it is?", "What color did she use?"

def cross(kid, s):
    sc, other = cnt(shape=s), mode(Counter(r["kid"] for r in rows if r["shape"] == s))
    key = base_key(kid)
    key[usual[kid]] = f"{kid}'s usual (category answer)"
    key[mode(sc)] = f"{frac(sc, mode(sc))} {s}s were {mode(sc)} (shape-based answer)"
    key[usual[other]] = f"{other}'s usual (as if {other} drew it)"
    add("cross_category_conflict", kid, s, f"{kid} made this new drawing.", NEW, usual[kid], "NA",
        mode(sc), usual[other], "category membership vs shape", key)

def cat_only(kid):
    add("category_only", kid, "none", f"{kid} made a new drawing.", NEW, usual[kid], "NA", "NA", "NA",
        "memory for kid's usual color", base_key(kid))

for kid in targets:
    key = base_key(kid); key[usual[kid]] = f"{kid}'s usual, and all of {kid}'s {common}s"
    add("agree", kid, common, f"{kid} made this new drawing.", NEW, usual[kid], mode(cnt(kid, common)),
        "mixed", "NA", "learning/attention check", key)
    s = disagree[kid]; dc = cnt(kid, s); key = base_key(kid)
    key[usual[kid]] = f"{kid}'s usual (category answer)"
    key[mode(dc)] = f"{dc[mode(dc)]} of {kid}'s {sum(dc.values())} {s}s (conjunction answer)"
    add("classic_disagree", kid, s, f"{kid} made this new drawing.", NEW, usual[kid], mode(dc),
        mode(cnt(shape=s)), "NA", "category summary vs within-category conditioning", key)
    cross(kid, link)
    cat_only(kid)

cat_only(carrier)
cross(carrier, sorted(disagree.values())[0])

key = {c: f"{k}'s usual color" for k, c in usual.items()}
key.update({c: f"never on an {link}" for c in colors if c not in key})
key[usual[carrier]] = f"{carrier}'s usual (guess {carrier}, use {carrier}'s usual color)"
key[mode(cnt(shape=link))] = f"every {link} was {mode(cnt(shape=link))} (shape-based answer)"
add("kid_not_named", "none", link, "Someone made this new drawing.", NEW, f"{usual[carrier]} (if {carrier} is guessed)",
    "NA", mode(cnt(shape=link)), "NA", f"uncertain kid: guess {carrier} and use the usual color vs shape-based", key)

for s in [link] + [s for s in shapes if s != link and carrier in drawers[s]]:
    mc = cnt(carrier, s); key = base_key(carrier)
    key[mode(mc)] = f"correct: all {mc[mode(mc)]} of {carrier}'s {s}s" if len(mc) == 1 else f"correct: {mc[mode(mc)]} of {carrier}'s {sum(mc.values())} {s}s"
    if mode(mc) != usual[carrier]: key[usual[carrier]] = f"{carrier}'s usual, but never on an {s}"
    add("memory_probe", carrier, s, f"{carrier} drew this shape during training.", MEM, "NA", "NA",
        f"{mode(mc)} (correct)", "NA", f"memory for the color of {carrier}'s {s}s", key)

with open(sys.argv[2], "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(f"wrote {len(out)} test trials to {sys.argv[2]}")

from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import csv
import itertools
import math
import random
import re


# ============================================================
# ONLY EDIT THIS SECTION
# ============================================================

SETTINGS = {
    # If you keep the same seed, you get the same random version again.
    # Change this number if you want a new random version.
    "random_seed": 20260909,

    # Each painter/category has the same total number of examples.
    "examples_per_category": 8,

    # How many of a category's examples belong to the critical/test shape.
    # The rest of examples_per_category are split as evenly as possible
    # across the filler shapes. The critical shape gets a fixed, larger
    # share on purpose: with too few examples, the "dominant frequency"
    # requirement below can only ever be satisfied at 100%, which leaves no
    # room for the proportions to actually vary category to category.
    "critical_shape_example_count": 4,

    # How many distinct shapes each category has. One of these is the
    # critical/test shape; the rest are fillers. Same number for every
    # category.
    "shapes_per_category": 4,

    # One question per category, so there will be `number_of_categories`
    # formal trials total (one per category, since trials_per_category = 1).
    "trials_per_category": 1,

    # Change this number if you want more or fewer categories/trials.
    "number_of_categories": 25,

    # Which slice of PAINTER_NAMES this run uses (painter names 0-24, then
    # 25-49, ...). Only matters when you're generating more than one
    # condition that will later be merged into a single experiment (e.g.
    # high vs. low nameability) — set this to a different offset for each
    # run so no painter name gets reused across conditions.
    "painter_name_offset": 25,

    # A short name for this run, used to name its output files
    # (master_trial_list_<run_name>.csv, experiment_design_reference_<run_name>/)
    # so multiple condition runs don't overwrite each other. When you're
    # generating a single condition, this can be anything — the file merge
    # step is what produces the actual master_trial_list.csv the experiment
    # reads.
    "run_name": "low_nameability",

    # ------------------------------------------------------------------
    # Stimulus files. Point these at a different stimulus set's folders to
    # reuse this whole generator on a completely different set of shapes and
    # fills (gabor patches, colors, or anything else) — nothing else in this
    # file needs to change. Every shape and every fill is identified purely
    # by its filename, discovered automatically, never hand-listed:
    #   - outlines_dir has one file per shape:            "{shape_id}.png"
    #   - fill_dir has one file per fill:                 "{fill_id}.png"
    #   - shapes_dir has one file per shape x fill combo:  "{shape_id}_{fill_id}.png"
    # ------------------------------------------------------------------
    "outlines_dir": "images/low_nameability/shape_outlines",
    "fill_dir": "images/low_nameability/colors",
    "shapes_dir": "images/low_nameability/all_shapes",

    # Whether this script should synthesize the fill images itself (sine-
    # wave gabor gratings) before reading fill_dir. Set this to False for a
    # stimulus set where fill_dir is already populated with your own fill
    # images (e.g. colors, other textures) — the script will just use
    # whatever's already sitting there and skip synthesis entirely.
    "synthesize_gabor_fills": False,

    # Only used when synthesize_gabor_fills is True. Each key becomes a fill
    # id (i.e. the filename gabor1.png, gabor2.png, ... in fill_dir); each
    # value is how many grating cycles that gabor patch gets.
    "gabor_synthesis_cycles": {
        "gabor1": 2,
        "gabor2": 5,
        "gabor3": 10,
        "gabor4": 20,
    },
}


ROOT = Path(__file__).resolve().parent


def _natural_sort_key(name):
    # So shape2 sorts before shape10, not after.
    return [int(chunk) if chunk.isdigit() else chunk.lower() for chunk in re.split(r"(\d+)", name)]


def discover_ids(directory):
    # Every image file's name (minus extension) becomes an id.
    if not directory.is_dir():
        raise FileNotFoundError(f"Stimulus folder not found: {directory}")
    ids = [path.stem for path in directory.iterdir() if path.is_file() and not path.name.startswith(".")]
    if not ids:
        raise FileNotFoundError(f"No image files found in: {directory}")
    return sorted(ids, key=_natural_sort_key)


def synthesize_gabor_fills():
    # Pure sine-wave gabor patches, used as the two trial-choice images.
    # Only runs when SETTINGS["synthesize_gabor_fills"] is True. For a
    # stimulus set with its own pre-made fill images (e.g. colors), leave
    # that off and just drop the images straight into fill_dir instead.
    fill_dir = ROOT / SETTINGS["fill_dir"]
    fill_dir.mkdir(parents=True, exist_ok=True)

    size = 420
    center = (size - 1) / 2
    contrast = 0.90
    angle = math.radians(45)
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)

    for fill_id, cycles in SETTINGS["gabor_synthesis_cycles"].items():
        image = Image.new("RGB", (size, size), "white")
        pixels = image.load()

        for y in range(size):
            for x in range(size):
                dx = x - center
                dy = y - center
                rotated_x = dx * cos_angle + dy * sin_angle
                wave = math.cos(2 * math.pi * cycles * rotated_x / size)
                value = 127.5 + 127.5 * contrast * wave
                gray = max(0, min(255, int(round(value))))
                pixels[x, y] = (gray, gray, gray)

        image.save(fill_dir / f"{fill_id}.png")


if SETTINGS["synthesize_gabor_fills"]:
    synthesize_gabor_fills()

# The complete shape pool and fill (gabor/color/whatever) pool, discovered
# straight from what's on disk — nothing hand-listed here.
SHAPE_POOL = discover_ids(ROOT / SETTINGS["outlines_dir"])
FILL_POOL = discover_ids(ROOT / SETTINGS["fill_dir"])

# Cycle counts are only meaningful for synthesized gabor fills; for any
# other kind of fill (colors, etc.) this is just an empty lookup, and
# anything that reports cycles skips it automatically.
FILL_CYCLES = SETTINGS["gabor_synthesis_cycles"] if SETTINGS["synthesize_gabor_fills"] else {}


def validate_stimulus_files():
    # Confirm every shape x fill combination actually has a composite image
    # before we start planning categories around it.
    shapes_dir = ROOT / SETTINGS["shapes_dir"]
    missing = [
        f"{shape}_{fill}.png"
        for shape in SHAPE_POOL
        for fill in FILL_POOL
        if not (shapes_dir / f"{shape}_{fill}.png").exists()
    ]
    if missing:
        preview = ", ".join(missing[:10]) + (", ..." if len(missing) > 10 else "")
        raise FileNotFoundError(f"Missing {len(missing)} composite image(s) in {shapes_dir}: {preview}")


validate_stimulus_files()


# These are category names shown to participants.
# If you want different names later, edit this list.
PAINTER_NAMES = [
    "Emily", "Isabella", "Grace", "Olivia", "Sophia",
    "Ava", "Mia", "Charlotte", "Amelia", "Harper",
    "Lily", "Ella", "Chloe", "Victoria", "Aria",
    "Scarlett", "Layla", "Nora", "Riley", "Zoey",
    "Hannah", "Luna", "Stella", "Aurora", "Leah",
    # Second block of 25, for when generating a second condition (e.g. a
    # separate high/low nameability run via painter_name_offset below) that
    # needs to end up in the same merged experiment — every painter name
    # across BOTH runs needs to stay unique, or the participant would see
    # the same name used for two unrelated painters.
    "Abigail", "Emma", "Madison", "Elizabeth", "Avery",
    "Sofia", "Camila", "Penelope", "Violet", "Mila",
    "Nova", "Ivy", "Eleanor", "Hazel", "Willow",
    "Ruby", "Naomi", "Josephine", "Audrey", "Brooklyn",
    "Bella", "Claire", "Skylar", "Lucy", "Paisley",
]


def _partitions(total, max_value, max_parts):
    # Every non-increasing sequence of positive integers, of length up to
    # max_parts, summing to total, with no single part above max_value.
    if max_parts == 0:
        if total == 0:
            yield ()
        return
    if total == 0:
        yield ()
        return
    for value in range(min(total, max_value), 0, -1):
        for rest in _partitions(total - value, value, max_parts - 1):
            yield (value,) + rest


def enumerate_plurality_patterns(total, max_parts):
    # Every way to split `total` examples across at most `max_parts`
    # frequencies (sorted largest-first) where the largest is an
    # unambiguous, strictly-greater-than-every-other-single-count winner —
    # i.e. every gabor-count "shape" a category could legally have, e.g.
    # (5, 3), (4, 3, 1), (4, 2, 1, 1), (3, 2, 2, 1)... Recomputed from
    # whatever examples_per_category / critical_shape_example_count / fill
    # count you're using, so this doesn't need updating by hand if those
    # settings change.
    return [
        parts for parts in _partitions(total, total, max_parts)
        if len(parts) == 1 or parts[0] > parts[1]
    ]


def is_pair_feasible(category_pattern, critical_pattern, n_frequencies):
    # Checks a (category_pattern, critical_pattern) pair properly: the
    # critical shape's OWN top count needs a category-wide slot (other than
    # general's) with enough room, AND every one of its remaining, smaller
    # counts needs its own distinct slot (which can include general's own
    # slot, since general is allowed to show up as noise inside the
    # critical shape's examples too) with enough leftover room. Checking
    # only the top count isn't enough — e.g. category pattern (5, 3) has
    # room for critical pattern (2, 1, 1)'s top count, but only ONE other
    # slot (general's) is left over for its two remaining 1's, which need
    # two distinct slots — so that pairing doesn't actually work out.
    non_general_capacities = list(category_pattern[1:]) + [0] * (n_frequencies - 1 - len(category_pattern[1:]))
    for index, capacity in enumerate(non_general_capacities):
        if capacity < critical_pattern[0]:
            continue
        remaining_capacities = non_general_capacities[:index] + non_general_capacities[index + 1:]
        remaining_capacities.append(category_pattern[0])
        remaining_capacities.sort(reverse=True)
        remaining_demands = sorted(critical_pattern[1:], reverse=True)
        if all(demand <= capacity for demand, capacity in zip(remaining_demands, remaining_capacities)):
            return True
    return False


def feasible_configuration_pairs(category_patterns, critical_patterns, n_frequencies):
    return [
        (category_pattern, critical_pattern)
        for category_pattern in category_patterns
        for critical_pattern in critical_patterns
        if is_pair_feasible(category_pattern, critical_pattern, n_frequencies)
    ]


CATEGORY_GABOR_PATTERNS = enumerate_plurality_patterns(SETTINGS["examples_per_category"], len(FILL_POOL))
CRITICAL_GABOR_PATTERNS = enumerate_plurality_patterns(SETTINGS["critical_shape_example_count"], len(FILL_POOL))
CONFIGURATION_PAIRS = feasible_configuration_pairs(CATEGORY_GABOR_PATTERNS, CRITICAL_GABOR_PATTERNS, len(FILL_POOL))

if not CONFIGURATION_PAIRS:
    raise ValueError(
        "No (category, critical shape) gabor-count pattern is jointly satisfiable with the current "
        "examples_per_category / critical_shape_example_count / number of fills. The critical shape "
        "needs enough of its own examples, and the category needs enough room outside its top frequency, "
        "for the critical shape's own dominant frequency to have somewhere to win."
    )


def make_random_category_plans():
    rng = random.Random(SETTINGS["random_seed"] + 42)
    frequencies = list(FILL_POOL)
    n_fillers = SETTINGS["shapes_per_category"] - 1

    # Cycle evenly through every feasible (category, critical shape) gabor
    # pattern pair, so each one gets used as close to equally often as
    # possible (differing by at most 1) no matter how many categories you
    # generate — this is the actual counterbalancing.
    shuffled_configuration_pairs = list(CONFIGURATION_PAIRS)
    rng.shuffle(shuffled_configuration_pairs)

    all_shape_combinations = []
    for test_shape in SHAPE_POOL:
        filler_pool = [shape for shape in SHAPE_POOL if shape != test_shape]
        for fillers in itertools.combinations(filler_pool, n_fillers):
            all_shape_combinations.append((test_shape, fillers))

    rng.shuffle(all_shape_combinations)

    test_shape_counts = {shape: 0 for shape in SHAPE_POOL}
    shape_dominant_counts = {frequency: 0 for frequency in frequencies}
    used_combinations = set()
    category_plans = []

    painter_offset = SETTINGS["painter_name_offset"]
    painter_slice = PAINTER_NAMES[painter_offset:painter_offset + SETTINGS["number_of_categories"]]
    for category_index, painter in enumerate(painter_slice):
        unused = [
            combo for combo in all_shape_combinations
            if (combo[0], tuple(sorted(combo[1]))) not in used_combinations
        ]
        min_test_count = min(test_shape_counts[combo[0]] for combo in unused)
        balanced_candidates = [
            combo for combo in unused
            if test_shape_counts[combo[0]] == min_test_count
        ]
        test_shape, fillers = rng.choice(balanced_candidates)
        used_combinations.add((test_shape, tuple(sorted(fillers))))
        test_shape_counts[test_shape] += 1

        general = frequencies[category_index % len(frequencies)]
        possible_shape_dominants = [frequency for frequency in frequencies if frequency != general]
        shape_dominant = min(
            possible_shape_dominants,
            key=lambda frequency: (shape_dominant_counts[frequency], rng.random()),
        )
        shape_dominant_counts[shape_dominant] += 1

        category_pattern, critical_pattern = shuffled_configuration_pairs[
            category_index % len(shuffled_configuration_pairs)
        ]

        category_plans.append({
            "painter": painter,
            "general_dominant": general,
            "critical_test_shape": test_shape,
            "shape_dominant": shape_dominant,
            "filler_shapes": list(fillers),
            "category_gabor_pattern": category_pattern,
            "critical_gabor_pattern": critical_pattern,
        })

    return category_plans


CATEGORY_PLANS = make_random_category_plans()


def assign_pattern_counts(top_frequency, pattern, other_frequencies, rng):
    # Turns a magnitude pattern like (4, 3, 1) into an actual {frequency:
    # count} map: top_frequency gets the largest count, and the remaining
    # counts land on a randomly chosen subset of other_frequencies (so
    # which specific frequency comes in 2nd/3rd/... varies category to
    # category, not just how many examples that place gets).
    remaining_counts = list(pattern[1:])
    chosen_frequencies = rng.sample(other_frequencies, len(remaining_counts))
    counts = {top_frequency: pattern[0]}
    counts.update(zip(chosen_frequencies, remaining_counts))
    for frequency in FILL_POOL:
        counts.setdefault(frequency, 0)
    return counts


def build_category_frequency_lists(general, shape_dominant, category_pattern, critical_pattern, filler_counts, rng, max_attempts=2000):
    # Constructs exact per-shape frequency lists matching the category's
    # assigned patterns exactly (not just probably). The two random
    # assignment steps below are retried together until they're mutually
    # consistent — the critical shape's own counts can never exceed what
    # the category-wide pattern makes available for that same frequency,
    # since fillers have to supply the difference and can't contribute a
    # negative amount.
    non_general_frequencies = [frequency for frequency in FILL_POOL if frequency != general]
    non_shape_dominant_frequencies = [frequency for frequency in FILL_POOL if frequency != shape_dominant]

    for _ in range(max_attempts):
        category_counts = assign_pattern_counts(general, category_pattern, non_general_frequencies, rng)
        if category_counts[shape_dominant] < critical_pattern[0]:
            continue

        critical_counts = assign_pattern_counts(shape_dominant, critical_pattern, non_shape_dominant_frequencies, rng)
        filler_totals = {
            frequency: category_counts[frequency] - critical_counts[frequency]
            for frequency in FILL_POOL
        }
        if any(count < 0 for count in filler_totals.values()):
            continue

        critical_frequency_list = []
        for frequency, count in critical_counts.items():
            critical_frequency_list.extend([frequency] * count)
        rng.shuffle(critical_frequency_list)

        filler_pool = []
        for frequency, count in filler_totals.items():
            filler_pool.extend([frequency] * count)
        rng.shuffle(filler_pool)

        filler_frequency_lists = []
        cursor = 0
        for count in filler_counts:
            filler_frequency_lists.append(filler_pool[cursor:cursor + count])
            cursor += count

        return critical_frequency_list, filler_frequency_lists

    raise ValueError(
        f"Could not fit category pattern {category_pattern} and critical shape pattern {critical_pattern} "
        f"together after {max_attempts} attempts."
    )


def is_strict_plurality(frequency_list, target_frequency):
    counts = Counter(frequency_list)
    target_count = counts[target_frequency]
    return all(target_count > count for frequency, count in counts.items() if frequency != target_frequency)


def split_examples_across_shapes(total_examples, shapes_per_category, rng):
    base = total_examples // shapes_per_category
    remainder = total_examples % shapes_per_category
    counts = [base] * shapes_per_category
    for index in rng.sample(range(shapes_per_category), remainder):
        counts[index] += 1
    return counts


def build_categories():
    categories = {}
    used_combinations = set()
    rng = random.Random(SETTINGS["random_seed"] + 7)

    for plan in CATEGORY_PLANS:
        painter = plan["painter"]
        general = plan["general_dominant"]
        test_shape = plan["critical_test_shape"]
        shape_dominant = plan["shape_dominant"]
        filler_shapes = plan["filler_shapes"]
        category_pattern = plan["category_gabor_pattern"]
        critical_pattern = plan["critical_gabor_pattern"]

        shape_combo = (test_shape, tuple(sorted(filler_shapes)))
        if shape_combo in used_combinations:
            raise ValueError(f"{painter} repeats the exact same test/filler shape combination as another category.")
        used_combinations.add(shape_combo)

        test_count = SETTINGS["critical_shape_example_count"]
        n_fillers = SETTINGS["shapes_per_category"] - 1
        filler_total = SETTINGS["examples_per_category"] - test_count
        if n_fillers < 1 or filler_total < n_fillers:
            raise ValueError(
                "critical_shape_example_count leaves too few examples for the filler shapes "
                "to carry the category's general dominant frequency."
            )
        filler_counts = split_examples_across_shapes(filler_total, n_fillers, rng)

        # Build examples that match the category's assigned gabor-count
        # patterns exactly (this is what makes the plurality rules hold and
        # what makes the counterbalancing in CONFIGURATION_PAIRS meaningful
        # — every category really does land on the pattern it was assigned,
        # not just something probably close to it).
        test_frequencies, filler_frequency_lists = build_category_frequency_lists(
            general, shape_dominant, category_pattern, critical_pattern, filler_counts, rng
        )

        shapes = [
            {
                "shape": shape,
                "role": "filler",
                "example_count": count,
                "frequency_list": frequency_list,
            }
            for shape, count, frequency_list in zip(filler_shapes, filler_counts, filler_frequency_lists)
        ]
        shapes.append({
            "shape": test_shape,
            "role": "test",
            "shape_dominant": shape_dominant,
            "example_count": test_count,
            "frequency_list": test_frequencies,
        })

        categories[painter] = {
            "general_dominant": general,
            "shapes": shapes,
        }

    return categories


CATEGORIES = build_categories()

# ============================================================
# USUALLY DO NOT EDIT BELOW THIS LINE
# ============================================================

OUTLINE_IMAGES = {
    shape: f"{SETTINGS['outlines_dir']}/{shape}.png"
    for shape in SHAPE_POOL
}

# Fallback thumbnail bounding box for any shape that isn't explicitly sized
# below. Add a shape here (using its discovered id, e.g. "shape3") only if
# its default thumbnail looks wrong. These current values were hand-tuned
# for this stimulus set's 8 shapes (shape1-shape8); a new stimulus set can
# just leave this empty and rely on the default until specific shapes need
# a custom crop.
DEFAULT_MAX_IMAGE_SIZE = (120, 100)
MAX_IMAGE_SIZE = {
    "shape1": (125, 84),
    "shape2": (118, 100),
    "shape3": (128, 88),
    "shape4": (130, 84),
    "shape5": (105, 105),
    "shape6": (105, 105),
    "shape7": (105, 105),
    "shape8": (112, 98),
}


def image_path(shape, frequency):
    return f"{SETTINGS['shapes_dir']}/{shape}_{frequency}.png"


def gabor_patch_path(frequency):
    return f"{SETTINGS['fill_dir']}/{frequency}.png"


def check_design():
    for painter, category in CATEGORIES.items():
        test_shapes = [shape for shape in category["shapes"] if shape["role"] == "test"]
        if len(test_shapes) != 1:
            raise ValueError(f"{painter} must have exactly one test shape.")

        if len(category["shapes"]) != SETTINGS["shapes_per_category"]:
            raise ValueError(f"{painter} must have exactly {SETTINGS['shapes_per_category']} shapes.")

        total_examples = sum(shape["example_count"] for shape in category["shapes"])
        if total_examples != SETTINGS["examples_per_category"]:
            raise ValueError(f"{painter} must have exactly {SETTINGS['examples_per_category']} examples.")

        general = category["general_dominant"]
        test = test_shapes[0]
        if test["shape_dominant"] == general:
            raise ValueError(f"{painter}'s test shape dominant frequency must differ from the category dominant frequency.")

        if not is_strict_plurality(test["frequency_list"], test["shape_dominant"]):
            raise ValueError(f"{painter}'s test shape dominant frequency is not a clear winner within that shape.")

        all_frequencies_in_category = [
            frequency
            for shape in category["shapes"]
            for frequency in shape["frequency_list"]
        ]
        if not is_strict_plurality(all_frequencies_in_category, general):
            raise ValueError(f"{painter}'s category dominant frequency is not a strict plurality across the whole category.")


def generate_examples():
    rng = random.Random(SETTINGS["random_seed"])
    rows = []

    for painter, category in CATEGORIES.items():
        general = category["general_dominant"]

        for shape_info in category["shapes"]:
            shape = shape_info["shape"]
            role = shape_info["role"]
            shape_dominant = shape_info.get("shape_dominant", general)
            frequencies = list(shape_info["frequency_list"])
            rng.shuffle(frequencies)

            for repeat, actual_frequency in enumerate(frequencies, start=1):
                row = {
                    "painter": painter,
                    "shape": shape,
                    "shape_role": role,
                    "is_test_shape": "yes" if role == "test" else "no",
                    "general_dominant_frequency": general,
                    "shape_dominant_frequency": shape_dominant,
                    "actual_frequency": actual_frequency,
                    "uses_general_dominant": "yes" if actual_frequency == general else "no",
                    "uses_shape_dominant": "yes" if actual_frequency == shape_dominant else "no",
                    "image": image_path(shape, actual_frequency),
                    "repeat_inside_shape": repeat,
                }
                if actual_frequency in FILL_CYCLES:
                    row["actual_frequency_cycles"] = FILL_CYCLES[actual_frequency]
                rows.append(row)

    rng.shuffle(rows)
    return rows


def crop_nonwhite(image):
    gray = image.convert("L")
    mask = gray.point(lambda p: 255 if p < 247 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return image
    padding = 12
    x0, y0, x1, y1 = bbox
    return image.crop((
        max(0, x0 - padding),
        max(0, y0 - padding),
        min(image.width, x1 + padding),
        min(image.height, y1 + padding),
    ))


def make_thumbnail(row):
    image = Image.open(ROOT / row["image"]).convert("RGB")
    image = crop_nonwhite(image)
    image.thumbnail(MAX_IMAGE_SIZE.get(row["shape"], DEFAULT_MAX_IMAGE_SIZE), Image.Resampling.LANCZOS)
    return image


def draw_example_board(example_rows, annotated=False):
    cell_w = 900
    cell_h = 650
    margin_x = 70
    margin_y = 78
    header_h = 40
    columns = 2
    rows_count = math.ceil(len(CATEGORIES) / columns)
    width = margin_x * 2 + cell_w * 2
    height = margin_y * 2 + header_h + cell_h * rows_count

    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf", 30)
        small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 11)
    except OSError:
        title_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    slots = [
        (95, 90), (255, 85), (420, 95), (585, 90), (750, 105),
        (145, 220), (325, 225), (505, 215), (685, 230),
        (100, 365), (275, 380), (455, 365), (635, 375), (800, 380),
    ]

    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    placed_rows = []

    for index, painter in enumerate(CATEGORIES.keys()):
        col = index % columns
        row = index // columns
        x0 = margin_x + col * cell_w
        y0 = margin_y + header_h + row * cell_h

        draw.rectangle([x0, y0, x0 + cell_w, y0 + cell_h], outline="black", width=2)
        title_box = draw.textbbox((0, 0), painter, font=title_font)
        draw.text((x0 + (cell_w - (title_box[2] - title_box[0])) / 2, y0 - 36), painter, fill="black", font=title_font)

        painter_rows = [example.copy() for example in example_rows if example["painter"] == painter]
        rng = random.Random(SETTINGS["random_seed"] + index + 100)
        rng.shuffle(painter_rows)

        slot_order = slots[:len(painter_rows)]
        rng.shuffle(slot_order)

        for example_number, (example, (cx, cy)) in enumerate(zip(painter_rows, slot_order), start=1):
            thumbnail = make_thumbnail(example)
            px = int(x0 + cx - thumbnail.width / 2)
            py = int(y0 + cy - thumbnail.height / 2)
            canvas.paste(thumbnail, (px, py))

            if annotated:
                label = f"{example['shape_role']} {example['shape']} {example['actual_frequency']}"
                label_box = draw.textbbox((0, 0), label, font=small_font)
                lx = px + max(0, (thumbnail.width - (label_box[2] - label_box[0])) / 2)
                ly = py + thumbnail.height + 1
                draw.rectangle([lx - 2, ly - 1, lx + (label_box[2] - label_box[0]) + 2, ly + (label_box[3] - label_box[1]) + 2], fill="white")
                draw.text((lx, ly), label, fill=(55, 55, 55), font=small_font)

            example["example_number_in_painter_box"] = example_number
            example["x_position_in_cell"] = cx
            example["y_position_in_cell"] = cy
            placed_rows.append(example)

    return canvas, placed_rows


def category_example_image_name(painter, annotated=False):
    suffix = "_annotated" if annotated else ""
    return f"proportion_category_example_{painter.lower()}{suffix}.png"


def draw_single_category_board(example_rows, painter, annotated=False):
    width = 820
    height = 365
    margin_top = 64

    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf", 30)
        small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 11)
    except OSError:
        title_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    slots = [
        (95, 66), (250, 64), (405, 68), (560, 64), (710, 70),
        (150, 190), (330, 194), (510, 188), (690, 194),
    ]

    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([28, margin_top, width - 28, height - 28], outline="black", width=2)

    title_box = draw.textbbox((0, 0), painter, font=title_font)
    draw.text(((width - (title_box[2] - title_box[0])) / 2, 16), painter, fill="black", font=title_font)

    painter_rows = [example.copy() for example in example_rows if example["painter"] == painter]
    rng = random.Random(SETTINGS["random_seed"] + 500 + list(CATEGORIES.keys()).index(painter))
    rng.shuffle(painter_rows)
    slot_order = slots[:len(painter_rows)]
    rng.shuffle(slot_order)

    placed_rows = []
    for example_number, (example, (cx, cy)) in enumerate(zip(painter_rows, slot_order), start=1):
        thumbnail = make_thumbnail(example)
        px = int(cx - thumbnail.width / 2)
        py = int(margin_top + cy - thumbnail.height / 2)
        canvas.paste(thumbnail, (px, py))

        if annotated:
            label = f"{example['shape_role']} {example['shape']} {example['actual_frequency']}"
            label_box = draw.textbbox((0, 0), label, font=small_font)
            lx = px + max(0, (thumbnail.width - (label_box[2] - label_box[0])) / 2)
            ly = py + thumbnail.height + 1
            draw.rectangle([lx - 2, ly - 1, lx + (label_box[2] - label_box[0]) + 2, ly + (label_box[3] - label_box[1]) + 2], fill="white")
            draw.text((lx, ly), label, fill=(55, 55, 55), font=small_font)

        example["single_category_example_number"] = example_number
        example["single_category_x_position"] = cx
        example["single_category_y_position"] = cy
        placed_rows.append(example)

    return canvas, placed_rows


def draw_all_single_category_boards(example_rows):
    placed_rows = []
    for painter in CATEGORIES.keys():
        # The experiment page now builds each category example display from the
        # item-level CSV, so we only need the positions, not pre-rendered boards.
        _, clean_rows = draw_single_category_board(example_rows, painter, annotated=False)
        placed_rows.extend(clean_rows)
    return placed_rows


def generate_master_trial_list(example_rows):
    # One row per trial (= one row per category/painter, since
    # trials_per_category = 1). Every item and gabor reference is the exact
    # filename that was shown, so nothing has to be re-derived downstream.
    trial_rows = []
    rng = random.Random(SETTINGS["random_seed"] + 999)

    for painter, category in CATEGORIES.items():
        general = category["general_dominant"]
        test_shape_info = [shape for shape in category["shapes"] if shape["role"] == "test"][0]
        critical_shape = test_shape_info["shape"]
        shape_dominant = test_shape_info["shape_dominant"]

        item_images = [row["image"] for row in example_rows if row["painter"] == painter]
        rng.shuffle(item_images)

        row = {
            "painter": painter,
            "critical_shape": critical_shape,
            "category_dominant_gabor": general,
            "critical_shape_dominant_gabor": shape_dominant,
            "target_probe_outline": OUTLINE_IMAGES[critical_shape],
            "category_induction_gabor": gabor_patch_path(general),
            "feature_feature_gabor": gabor_patch_path(shape_dominant),
        }
        for item_number, item_image in enumerate(item_images, start=1):
            row[f"item{item_number}_name"] = item_image

        trial_rows.append(row)

    rng.shuffle(trial_rows)
    ordered_rows = []
    for index, row in enumerate(trial_rows, start=1):
        ordered_rows.append({"trial_id": f"trial_{index:03d}", **row})
    return ordered_rows


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def gabor_count_pattern(frequency_list):
    # The full shape of a distribution, e.g. (4, 3, 1) or (5, 2, 1) — every
    # frequency that appears, sorted largest-first, regardless of which
    # specific gabor id got which count. Two categories with the same
    # dominant share (e.g. 4/8 = 0.5) can still have very different shapes
    # here (4-2-1-1 vs 4-3-1-0), which a bare "share" number hides.
    return tuple(sorted(Counter(frequency_list).values(), reverse=True))


def summarize_examples(example_rows):
    summary = []
    for painter in CATEGORIES.keys():
        category = CATEGORIES[painter]
        rows = [row for row in example_rows if row["painter"] == painter]
        general = category["general_dominant"]
        test_shape = [shape for shape in category["shapes"] if shape["role"] == "test"][0]
        shape_dominant = test_shape["shape_dominant"]

        test_rows = [row for row in rows if row["shape_role"] == "test"]
        test_dominant_count = sum(1 for row in test_rows if row["actual_frequency"] == shape_dominant)
        category_general_count = sum(1 for row in rows if row["actual_frequency"] == general)

        filler_shapes = [shape for shape in category["shapes"] if shape["role"] == "filler"]
        filler_example_proportions = tuple(sorted(
            round(shape["example_count"] / len(rows), 3) for shape in filler_shapes
        ))

        summary.append({
            "painter": painter,
            "shapes_per_category": len(category["shapes"]),
            "total_examples": len(rows),
            "general_dominant_frequency": general,
            "general_dominant_count_category_wide": category_general_count,
            "general_dominant_share_category_wide": round(category_general_count / len(rows), 3),
            "category_wide_gabor_count_pattern": ",".join(map(str, gabor_count_pattern(
                [row["actual_frequency"] for row in rows]
            ))),
            "test_shape": test_shape["shape"],
            "shape_dominant_frequency": shape_dominant,
            "test_shape_total_examples": len(test_rows),
            "test_shape_dominant_count": test_dominant_count,
            "test_shape_dominant_share": round(test_dominant_count / len(test_rows), 3),
            "critical_shape_gabor_count_pattern": ",".join(map(str, gabor_count_pattern(
                [row["actual_frequency"] for row in test_rows]
            ))),
            "critical_shape_example_proportion": round(len(test_rows) / len(rows), 3),
            "filler_shape_example_proportions": ",".join(str(p) for p in filler_example_proportions),
        })
    return summary


def summarize_statistical_configurations(design_summary_rows):
    # Groups categories/trials by their "statistical configuration": the
    # full shape of the category-wide gabor distribution (e.g. "4,3,1" vs
    # "5,2,1" vs "4,2,1,1" — not just the dominant's share, since two very
    # different-looking distributions can share the same dominant share)
    # combined with the full shape of the critical shape's own distribution.
    # This is what actually varies category to category by design; example
    # counts per shape are intentionally left out of the key since they're
    # a fixed setting today, not a condition that varies.
    groups = {}
    for row in design_summary_rows:
        config_key = (
            row["category_wide_gabor_count_pattern"],
            row["critical_shape_gabor_count_pattern"],
        )
        groups.setdefault(config_key, []).append(row["painter"])

    configuration_rows = []
    for config_key, painters in sorted(groups.items(), key=lambda item: -len(item[1])):
        category_pattern, critical_pattern = config_key
        configuration_rows.append({
            "trial_count": len(painters),
            "category_wide_gabor_count_pattern": category_pattern,
            "critical_shape_gabor_count_pattern": critical_pattern,
            "painters": ";".join(painters),
        })
    return configuration_rows


def print_configuration_summary(configuration_rows, total_trials):
    print(f"\nStatistical configurations ({len(configuration_rows)} distinct, {total_trials} trials total):")
    for row in configuration_rows:
        print(
            f"  {row['trial_count']} trial(s) -- "
            f"category-wide pattern=({row['category_wide_gabor_count_pattern']}), "
            f"critical-shape pattern=({row['critical_shape_gabor_count_pattern']}) "
            f"[{row['painters']}]"
        )


def main():
    check_design()
    example_rows = generate_examples()
    clean_board, placed_rows = draw_example_board(example_rows, annotated=False)
    annotated_board, _ = draw_example_board(example_rows, annotated=True)
    single_category_rows = draw_all_single_category_boards(example_rows)
    trial_rows = generate_master_trial_list(example_rows)
    summary_rows = summarize_examples(example_rows)
    configuration_rows = summarize_statistical_configurations(summary_rows)

    # QA/debug files only — not read by the live experiment (experiment.js
    # only reads master_trial_list.csv). Kept separate so it's obvious at a
    # glance what does and doesn't need to be uploaded with the experiment.
    # Named per run_name so multiple condition runs don't overwrite each
    # other's QA files.
    run_name = SETTINGS["run_name"]
    reference_dir = ROOT / f"experiment_design_reference_{run_name}"
    reference_dir.mkdir(parents=True, exist_ok=True)

    clean_board.save(reference_dir / "proportion_example_board.png")
    annotated_board.save(reference_dir / "proportion_example_board_annotated.png")
    write_csv(reference_dir / "proportion_example_list.csv", placed_rows)
    write_csv(reference_dir / "proportion_single_category_example_list.csv", single_category_rows)
    write_csv(reference_dir / "proportion_design_summary.csv", summary_rows)
    write_csv(reference_dir / "statistical_configuration_summary.csv", configuration_rows)

    # This is an intermediate, per-condition file — NOT what the live
    # experiment reads. Run merge_trial_lists.py after generating every
    # condition to build the final, shuffled master_trial_list.csv.
    trial_list_path = ROOT / f"master_trial_list_{run_name}.csv"
    write_csv(trial_list_path, trial_rows)

    print("Generated:")
    print(trial_list_path)
    print(reference_dir / "proportion_example_board.png")
    print(reference_dir / "proportion_example_board_annotated.png")
    print(reference_dir / "proportion_example_list.csv")
    print(reference_dir / "proportion_single_category_example_list.csv")
    print(reference_dir / "proportion_design_summary.csv")
    print(reference_dir / "statistical_configuration_summary.csv")

    print_configuration_summary(configuration_rows, total_trials=len(summary_rows))


if __name__ == "__main__":
    main()

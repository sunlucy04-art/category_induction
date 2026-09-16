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

    # How strongly the critical shape's own examples favor its own dominant
    # frequency. Each category draws its own weight (uniformly) from this
    # range, so the exact proportion is jittered a little category to
    # category instead of being a fixed ratio. Whatever weight is drawn, the
    # generator keeps resampling that shape's examples until its dominant
    # frequency actually comes out as the single most common one.
    "critical_shape_dominant_weight_range": (0.55, 0.80),

    # Same idea, but for how strongly each filler shape's examples are
    # randomly sampled toward the category's general (cross-category)
    # dominant frequency. Each filler shape draws its own weight
    # independently, so filler shapes act as noise around the general
    # frequency rather than a hand-picked "third frequency" slot.
    "filler_dominant_weight_range": (0.45, 0.70),

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
    "outlines_dir": "images/shape_outines",
    "fill_dir": "images/gabor_frequencies",
    "shapes_dir": "images/all_shapes",

    # Whether this script should synthesize the fill images itself (sine-
    # wave gabor gratings) before reading fill_dir. Set this to False for a
    # stimulus set where fill_dir is already populated with your own fill
    # images (e.g. colors, other textures) — the script will just use
    # whatever's already sitting there and skip synthesis entirely.
    "synthesize_gabor_fills": True,

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
]


def make_random_category_plans():
    rng = random.Random(SETTINGS["random_seed"] + 42)
    frequencies = list(FILL_POOL)
    n_fillers = SETTINGS["shapes_per_category"] - 1

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

    for category_index, painter in enumerate(PAINTER_NAMES[:SETTINGS["number_of_categories"]]):
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

        category_plans.append({
            "painter": painter,
            "general_dominant": general,
            "critical_test_shape": test_shape,
            "shape_dominant": shape_dominant,
            "filler_shapes": list(fillers),
        })

    return category_plans


CATEGORY_PLANS = make_random_category_plans()


def sample_weighted_frequencies(n_examples, dominant_frequency, all_frequencies, dominant_weight, rng):
    # Draws each example's frequency independently: `dominant_weight` chance of
    # the target frequency, with the rest of the probability spread evenly
    # across the other frequencies (this is the "noise").
    other_frequencies = [frequency for frequency in all_frequencies if frequency != dominant_frequency]
    weights = [dominant_weight] + [(1 - dominant_weight) / len(other_frequencies)] * len(other_frequencies)
    frequencies = [dominant_frequency] + other_frequencies
    return rng.choices(frequencies, weights=weights, k=n_examples)


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
    frequencies = list(FILL_POOL)
    critical_weight_range = SETTINGS["critical_shape_dominant_weight_range"]
    filler_weight_range = SETTINGS["filler_dominant_weight_range"]
    max_attempts = 2000

    for plan in CATEGORY_PLANS:
        painter = plan["painter"]
        general = plan["general_dominant"]
        test_shape = plan["critical_test_shape"]
        shape_dominant = plan["shape_dominant"]
        filler_shapes = plan["filler_shapes"]

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

        # Two plurality rules must both hold, so there's always a single
        # clear winner (no ties) at both levels:
        #   1. Within the critical shape's own examples, its own dominant
        #      frequency (shape_dominant) must be the clear winner.
        #   2. Across the WHOLE category (critical shape + every filler
        #      combined), the category's general frequency must be the
        #      clear winner — and it's structurally guaranteed different
        #      from shape_dominant already, from the planning step above.
        # The critical shape's and every filler shape's examples are
        # redrawn together on each attempt, so an unlucky combination just
        # gets resampled as a whole rather than getting stuck chasing one
        # rule while violating the other.
        for _ in range(max_attempts):
            critical_weight = rng.uniform(*critical_weight_range)
            test_frequencies = sample_weighted_frequencies(test_count, shape_dominant, frequencies, critical_weight, rng)
            if not is_strict_plurality(test_frequencies, shape_dominant):
                continue

            filler_frequency_lists = [
                sample_weighted_frequencies(count, general, frequencies, rng.uniform(*filler_weight_range), rng)
                for count in filler_counts
            ]
            all_frequencies_in_category = test_frequencies + [
                frequency for frequency_list in filler_frequency_lists for frequency in frequency_list
            ]
            if is_strict_plurality(all_frequencies_in_category, general):
                break
        else:
            raise ValueError(
                f"{painter}: could not find examples where {shape_dominant} is a clear winner within the "
                f"critical shape AND {general} is a clear winner across the whole category after "
                f"{max_attempts} attempts. Try raising critical_shape_example_count's margin below "
                f"examples_per_category, or narrowing the dominant-weight ranges."
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
        row["question_text"] = f"This new painting belongs to {painter}. What could the inside look like most likely?"

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

        summary.append({
            "painter": painter,
            "shapes_per_category": len(category["shapes"]),
            "total_examples": len(rows),
            "general_dominant_frequency": general,
            "general_dominant_count_category_wide": category_general_count,
            "general_dominant_share_category_wide": round(category_general_count / len(rows), 3),
            "test_shape": test_shape["shape"],
            "shape_dominant_frequency": shape_dominant,
            "test_shape_total_examples": len(test_rows),
            "test_shape_dominant_count": test_dominant_count,
            "test_shape_dominant_share": round(test_dominant_count / len(test_rows), 3),
        })
    return summary


def main():
    check_design()
    example_rows = generate_examples()
    clean_board, placed_rows = draw_example_board(example_rows, annotated=False)
    annotated_board, _ = draw_example_board(example_rows, annotated=True)
    single_category_rows = draw_all_single_category_boards(example_rows)
    trial_rows = generate_master_trial_list(example_rows)
    summary_rows = summarize_examples(example_rows)

    # QA/debug files only — not read by the live experiment (experiment.js
    # only reads master_trial_list.csv). Kept separate so it's obvious at a
    # glance what does and doesn't need to be uploaded with the experiment.
    reference_dir = ROOT / "experiment_design_reference"
    reference_dir.mkdir(parents=True, exist_ok=True)

    clean_board.save(reference_dir / "proportion_example_board.png")
    annotated_board.save(reference_dir / "proportion_example_board_annotated.png")
    write_csv(reference_dir / "proportion_example_list.csv", placed_rows)
    write_csv(reference_dir / "proportion_single_category_example_list.csv", single_category_rows)
    write_csv(reference_dir / "proportion_design_summary.csv", summary_rows)

    write_csv(ROOT / "master_trial_list.csv", trial_rows)

    print("Generated:")
    print(ROOT / "master_trial_list.csv")
    print(reference_dir / "proportion_example_board.png")
    print(reference_dir / "proportion_example_board_annotated.png")
    print(reference_dir / "proportion_example_list.csv")
    print(reference_dir / "proportion_single_category_example_list.csv")
    print(reference_dir / "proportion_design_summary.csv")


if __name__ == "__main__":
    main()

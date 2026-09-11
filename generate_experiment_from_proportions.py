from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import csv
import math
import random


# ============================================================
# ONLY EDIT THIS SECTION
# ============================================================

SETTINGS = {
    # If you keep the same seed, you get the same random version again.
    # Change this number if you want a new random version.
    "random_seed": 20260909,

    # Each painter/category has the same total number of examples.
    "examples_per_category": 8,

    # Gabor frequency values.
    "frequencies": {
        "F1": {"cycles": 2},
        "F2": {"cycles": 5},
        "F3": {"cycles": 10},
        "F4": {"cycles": 20},
    },

    # One question per category, so there will be 10 formal trials total.
    "trials_per_category": 1,

    # Change this number if you want more or fewer categories/trials.
    "number_of_categories": 25,
}


SHAPE_POOL = [
    "emily_shape",
    "isabella_shape",
    "grace_shape",
    "olivia_shape",
    "blocky_shape",
    "branch_shape",
    "flower_shape",
    "mushroom_shape",
]


# These are the allowed 8-item statistical makeups.
# Every makeup has:
# - 3 shapes total
# - 1 critical test shape
# - 2 filler shapes
# - 3 examples using the critical shape's own dominant frequency
# - 4 or 5 examples using the category/general dominant frequency
# - 0 or 1 example using a third frequency
# The third frequency is not always present and is not always placed in the same shape.
STATISTICAL_MAKEUPS = {
    "A": {
        "test": ["shape", "shape", "shape", "general"],
        "filler_1": ["general", "general"],
        "filler_2": ["general", "third"],
    },
    "B": {
        "test": ["shape", "shape", "shape"],
        "filler_1": ["general", "general", "general"],
        "filler_2": ["general", "third"],
    },
    "C": {
        "test": ["shape", "shape", "shape"],
        "filler_1": ["general", "general", "third"],
        "filler_2": ["general", "general"],
    },
    "D": {
        "test": ["shape", "shape", "shape", "general"],
        "filler_1": ["general", "third"],
        "filler_2": ["general", "general"],
    },
    "E": {
        "test": ["shape", "shape", "shape"],
        "filler_1": ["general", "general", "general"],
        "filler_2": ["general", "general"],
    },
}


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
    frequencies = list(SETTINGS["frequencies"].keys())
    makeup_names = list(STATISTICAL_MAKEUPS.keys())

    all_shape_combinations = []
    for test_shape in SHAPE_POOL:
        filler_pool = [shape for shape in SHAPE_POOL if shape != test_shape]
        for first_index in range(len(filler_pool)):
            for second_index in range(first_index + 1, len(filler_pool)):
                all_shape_combinations.append((
                    test_shape,
                    filler_pool[first_index],
                    filler_pool[second_index],
                ))

    rng.shuffle(all_shape_combinations)

    test_shape_counts = {shape: 0 for shape in SHAPE_POOL}
    shape_dominant_counts = {frequency: 0 for frequency in frequencies}
    used_combinations = set()
    category_plans = []

    for category_index, painter in enumerate(PAINTER_NAMES[:SETTINGS["number_of_categories"]]):
        unused = [
            combo for combo in all_shape_combinations
            if (combo[0], tuple(sorted(combo[1:]))) not in used_combinations
        ]
        min_test_count = min(test_shape_counts[combo[0]] for combo in unused)
        balanced_candidates = [
            combo for combo in unused
            if test_shape_counts[combo[0]] == min_test_count
        ]
        test_shape, filler_1, filler_2 = rng.choice(balanced_candidates)
        used_combinations.add((test_shape, tuple(sorted([filler_1, filler_2]))))
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
            "filler_shapes": [filler_1, filler_2],
            "makeup": makeup_names[category_index % len(makeup_names)],
        })

    return category_plans


CATEGORY_PLANS = make_random_category_plans()


def choose_third_frequency(general_dominant, shape_dominant, category_index):
    possible = [
        frequency for frequency in SETTINGS["frequencies"]
        if frequency not in {general_dominant, shape_dominant}
    ]
    return possible[category_index % len(possible)]


def resolve_frequency(label, general_dominant, shape_dominant, third_frequency):
    if label == "general":
        return general_dominant
    if label == "shape":
        return shape_dominant
    if label == "third":
        return third_frequency
    return label


def build_categories_from_makeups():
    categories = {}
    used_combinations = set()

    for category_index, plan in enumerate(CATEGORY_PLANS):
        painter = plan["painter"]
        general = plan["general_dominant"]
        test_shape = plan["critical_test_shape"]
        shape_dominant = plan["shape_dominant"]
        filler_1, filler_2 = plan["filler_shapes"]
        makeup = STATISTICAL_MAKEUPS[plan["makeup"]]
        third = choose_third_frequency(general, shape_dominant, category_index)

        shape_combo = (test_shape, tuple(sorted([filler_1, filler_2])))
        if shape_combo in used_combinations:
            raise ValueError(f"{painter} repeats the exact same test/filler shape combination as another category.")
        used_combinations.add(shape_combo)

        categories[painter] = {
            "general_dominant": general,
            "statistical_makeup": plan["makeup"],
            "third_frequency": third,
            "shapes": [
                {
                    "shape": filler_1,
                    "role": "filler",
                    "example_count": len(makeup["filler_1"]),
                    "frequency_list": [resolve_frequency(label, general, general, third) for label in makeup["filler_1"]],
                },
                {
                    "shape": filler_2,
                    "role": "filler",
                    "example_count": len(makeup["filler_2"]),
                    "frequency_list": [resolve_frequency(label, general, general, third) for label in makeup["filler_2"]],
                },
                {
                    "shape": test_shape,
                    "role": "test",
                    "shape_dominant": shape_dominant,
                    "example_count": len(makeup["test"]),
                    "frequency_list": [resolve_frequency(label, general, shape_dominant, third) for label in makeup["test"]],
                },
            ],
        }

    return categories


CATEGORIES = build_categories_from_makeups()

# ============================================================
# USUALLY DO NOT EDIT BELOW THIS LINE
# ============================================================

ROOT = Path(__file__).resolve().parent
IMAGE_FOLDER = ROOT / "images" / "v6_clear_frequency_shapes"
GABOR_OPTION_FOLDER = ROOT / "images" / "gabor_frequency_options"

FREQUENCY_FILE_NAMES = {
    "F1": "F1_2cycles",
    "F2": "F2_5cycles",
    "F3": "F3_10cycles",
    "F4": "F4_20cycles",
}

OUTLINE_IMAGES = {
    "emily_shape": "images/trial_target_outlines/emily_shape_1_outline.png",
    "isabella_shape": "images/trial_target_outlines/isabella_shape_1_outline.png",
    "grace_shape": "images/trial_target_outlines/grace_shape_1_outline.png",
    "olivia_shape": "images/trial_target_outlines/olivia_shape_1_outline.png",
    "blocky_shape": "images/trial_target_outlines/emily_shape_2_outline.png",
    "branch_shape": "images/trial_target_outlines/grace_shape_2_outline.png",
    "flower_shape": "images/trial_target_outlines/isabella_shape_2_outline.png",
    "mushroom_shape": "images/trial_target_outlines/olivia_shape_2_outline.png",
}

MAX_IMAGE_SIZE = {
    "emily_shape": (125, 84),
    "isabella_shape": (118, 100),
    "grace_shape": (128, 88),
    "olivia_shape": (130, 84),
    "blocky_shape": (105, 105),
    "branch_shape": (105, 105),
    "flower_shape": (105, 105),
    "mushroom_shape": (112, 98),
}


def image_path(shape, frequency):
    filename = f"{shape}_{FREQUENCY_FILE_NAMES[frequency]}.png"
    return f"images/v6_clear_frequency_shapes/{filename}"


def gabor_patch_path(frequency):
    cycles = SETTINGS["frequencies"][frequency]["cycles"]
    return f"images/gabor_frequency_options/{frequency}_{cycles}cycles.png"


def create_gabor_patch_images():
    # These are the pure Gabor patches shown as choices during the trial.
    # They use a full-field grating so they match the texture inside the example shapes.
    GABOR_OPTION_FOLDER.mkdir(parents=True, exist_ok=True)

    size = 420
    center = (size - 1) / 2
    contrast = 0.90
    angle = math.radians(45)
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)

    for frequency, info in SETTINGS["frequencies"].items():
        cycles = info["cycles"]
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

        image.save(ROOT / gabor_patch_path(frequency))


def rounded_counts(total, proportions):
    raw = [(key, total * value) for key, value in proportions.items()]
    counts = {key: int(value) for key, value in raw}
    remaining = total - sum(counts.values())
    fractions = sorted(raw, key=lambda item: item[1] - int(item[1]), reverse=True)
    for key, _ in fractions[:remaining]:
        counts[key] += 1
    return counts


def make_frequency_list(n_examples, frequency_proportions):
    counts = rounded_counts(n_examples, frequency_proportions)
    frequencies = []
    for frequency, count in counts.items():
        frequencies.extend([frequency] * count)
    return frequencies


def check_design():
    for painter, category in CATEGORIES.items():
        test_shapes = [shape for shape in category["shapes"] if shape["role"] == "test"]
        if len(test_shapes) != 1:
            raise ValueError(f"{painter} must have exactly one test shape.")

        if len(category["shapes"]) != 3:
            raise ValueError(f"{painter} must have exactly three shapes.")

        total_examples = sum(shape["example_count"] for shape in category["shapes"])
        if total_examples != SETTINGS["examples_per_category"]:
            raise ValueError(f"{painter} must have exactly {SETTINGS['examples_per_category']} examples.")

        general = category["general_dominant"]
        test = test_shapes[0]
        if test["shape_dominant"] == general:
            raise ValueError(f"{painter}'s test shape dominant frequency must differ from the category dominant frequency.")

        test_dominant_count = test["frequency_list"].count(test["shape_dominant"])
        if test_dominant_count / test["example_count"] < 0.70:
            raise ValueError(f"{painter}'s test shape dominant frequency is not strong enough.")


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
                rows.append({
                    "painter": painter,
                    "shape": shape,
                    "shape_role": role,
                    "is_test_shape": "yes" if role == "test" else "no",
                    "general_dominant_frequency": general,
                    "shape_dominant_frequency": shape_dominant,
                    "actual_frequency": actual_frequency,
                    "actual_frequency_cycles": SETTINGS["frequencies"][actual_frequency]["cycles"],
                    "uses_general_dominant": "yes" if actual_frequency == general else "no",
                    "uses_shape_dominant": "yes" if actual_frequency == shape_dominant else "no",
                    "image": image_path(shape, actual_frequency),
                    "repeat_inside_shape": repeat,
                })

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
    image.thumbnail(MAX_IMAGE_SIZE[row["shape"]], Image.Resampling.LANCZOS)
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


def generate_trials():
    trial_rows = []
    rng = random.Random(SETTINGS["random_seed"] + 999)

    for painter, category in CATEGORIES.items():
        general = category["general_dominant"]
        test_shape = [shape for shape in category["shapes"] if shape["role"] == "test"][0]
        shape = test_shape["shape"]
        shape_dominant = test_shape["shape_dominant"]

        for trial_number in range(SETTINGS["trials_per_category"]):
            general_option = (gabor_patch_path(general), "general_category", general)
            shape_option = (gabor_patch_path(shape_dominant), "shape_specific", shape_dominant)
            options = [general_option, shape_option]
            rng.shuffle(options)

            trial_rows.append({
                "painter": painter,
                "shape": shape,
                "trial_repeat": trial_number + 1,
                "question_text": f"This new painting belongs to {painter}. What could the inside look like most likely?",
                "target_outline_image": OUTLINE_IMAGES[shape],
                "category_dominant_frequency": general,
                "category_dominant_cycles": SETTINGS["frequencies"][general]["cycles"],
                "shape_dominant_frequency": shape_dominant,
                "shape_dominant_cycles": SETTINGS["frequencies"][shape_dominant]["cycles"],
                "left_option_image": options[0][0],
                "left_option_strategy": options[0][1],
                "left_option_frequency": options[0][2],
                "right_option_image": options[1][0],
                "right_option_strategy": options[1][1],
                "right_option_frequency": options[1][2],
                "correct_response": "none",
                "what_to_record": "selected_strategy",
            })

    rng.shuffle(trial_rows)
    for index, row in enumerate(trial_rows, start=1):
        row["trial_id"] = f"trial_{index:03d}"
    return trial_rows


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
        third_count = sum(
            1 for row in rows
            if row["actual_frequency"] != general and row["actual_frequency"] != shape_dominant
        )
        summary.append({
            "painter": painter,
            "statistical_makeup": category["statistical_makeup"],
            "total_examples": len(rows),
            "general_dominant_frequency": general,
            "general_dominant_count": sum(1 for row in rows if row["actual_frequency"] == general),
            "test_shape": test_shape["shape"],
            "shape_dominant_frequency": shape_dominant,
            "test_shape_total_examples": sum(1 for row in rows if row["shape_role"] == "test"),
            "test_shape_dominant_count": sum(1 for row in rows if row["shape_role"] == "test" and row["actual_frequency"] == shape_dominant),
            "third_frequency": category["third_frequency"],
            "third_frequency_count": third_count,
        })
    return summary


def main():
    create_gabor_patch_images()
    check_design()
    example_rows = generate_examples()
    clean_board, placed_rows = draw_example_board(example_rows, annotated=False)
    annotated_board, _ = draw_example_board(example_rows, annotated=True)
    single_category_rows = draw_all_single_category_boards(example_rows)
    trial_rows = generate_trials()
    summary_rows = summarize_examples(example_rows)

    clean_board.save(ROOT / "proportion_example_board.png")
    annotated_board.save(ROOT / "proportion_example_board_annotated.png")
    write_csv(ROOT / "proportion_example_list.csv", placed_rows)
    write_csv(ROOT / "proportion_single_category_example_list.csv", single_category_rows)
    write_csv(ROOT / "proportion_trial_list.csv", trial_rows)
    write_csv(ROOT / "proportion_design_summary.csv", summary_rows)

    print("Generated:")
    print(ROOT / "proportion_example_board.png")
    print(ROOT / "proportion_example_board_annotated.png")
    print(ROOT / "proportion_example_list.csv")
    print(ROOT / "proportion_single_category_example_list.csv")
    print(ROOT / "proportion_trial_list.csv")
    print(ROOT / "proportion_design_summary.csv")


if __name__ == "__main__":
    main()

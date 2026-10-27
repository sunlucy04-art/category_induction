"""
One-time stimulus prep for the high/low nameability shape x color design.

Organizes the selected shape outlines and color swatches into the
outlines_dir / fill_dir / shapes_dir folder structure generate_trials.py
expects for each condition, and generates the composite "shape filled with
color" images by flood-filling each outline's interior — colors are solid
fills, so these can be built automatically instead of hand-made like the
old gabor-patch composites.

Re-run this only if the underlying shape/color source files change. It does
not touch generate_trials.py or master_trial_list.csv.
"""

from pathlib import Path
import shutil

import numpy as np
from PIL import Image
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parent

CONDITIONS = {
    "high_nameability": {
        "shape_source": ROOT / "images/shape_outines/high_shape_selected",
        "color_source": ROOT / "images/target_feature/high_color_selected",
        "outlines_dir": ROOT / "images/high_nameability/shape_outlines",
        "fill_dir": ROOT / "images/high_nameability/colors",
        "shapes_dir": ROOT / "images/high_nameability/all_shapes",
    },
    "low_nameability": {
        "shape_source": ROOT / "images/shape_outines/low_shape_selected",
        "color_source": ROOT / "images/target_feature/low_color_selected",
        "outlines_dir": ROOT / "images/low_nameability/shape_outlines",
        "fill_dir": ROOT / "images/low_nameability/colors",
        "shapes_dir": ROOT / "images/low_nameability/all_shapes",
    },
}


def sample_color(swatch_path):
    # Color swatches are solid squares, so the center pixel is the color.
    image = Image.open(swatch_path).convert("RGBA")
    width, height = image.size
    return image.getpixel((width // 2, height // 2))[:3]


def composite_shape_color(outline_path, color_rgb, out_path, line_alpha_threshold=128):
    # Flood-fills the shape's interior with color_rgb, keeps its outline
    # black, and gives it a white background — matching the composite style
    # the rest of the pipeline (and the example-board cropping) expects.
    outline = Image.open(outline_path).convert("RGBA")
    array = np.array(outline)
    is_line = array[:, :, 3] >= line_alpha_threshold

    # Connected components of the non-line region, 4-connectivity so a
    # diagonal gap in the line can't leak the fill through it. Whichever
    # component touches the top-left corner is the exterior; everything
    # else non-line is the shape's interior.
    structure = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    labels, _ = label(~is_line, structure=structure)
    exterior_label = labels[0, 0]
    is_interior = (~is_line) & (labels != exterior_label)

    out = np.full((*is_line.shape, 4), 255, dtype=np.uint8)
    out[is_interior] = (*color_rgb, 255)
    out[is_line] = (0, 0, 0, 255)

    Image.fromarray(out, "RGBA").convert("RGB").save(out_path)


def prepare_condition(name, config):
    print(f"--- {name} ---")

    config["outlines_dir"].mkdir(parents=True, exist_ok=True)
    config["fill_dir"].mkdir(parents=True, exist_ok=True)
    config["shapes_dir"].mkdir(parents=True, exist_ok=True)

    shape_files = sorted(config["shape_source"].glob("*.png"))
    color_files = sorted(config["color_source"].glob("*.png"))
    print(f"{len(shape_files)} shapes, {len(color_files)} colors -> {len(shape_files) * len(color_files)} composites")

    for shape_file in shape_files:
        shutil.copy(shape_file, config["outlines_dir"] / shape_file.name)
    for color_file in color_files:
        shutil.copy(color_file, config["fill_dir"] / color_file.name)

    for shape_file in shape_files:
        shape_id = shape_file.stem
        for color_file in color_files:
            fill_id = color_file.stem
            color_rgb = sample_color(color_file)
            out_path = config["shapes_dir"] / f"{shape_id}_{fill_id}.png"
            composite_shape_color(shape_file, color_rgb, out_path)

    print(f"wrote {len(shape_files) * len(color_files)} composite images to {config['shapes_dir']}")


def main():
    for name, config in CONDITIONS.items():
        prepare_condition(name, config)


if __name__ == "__main__":
    main()

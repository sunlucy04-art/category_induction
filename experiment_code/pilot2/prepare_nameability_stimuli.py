"""
One-time stimulus prep for the high/low nameability shape x color design.

Organizes the selected shape outlines and color swatches into the
outlines_dir / fill_dir / shapes_dir folder structure generate_trials.py
expects for each condition, and generates the composite "shape filled with
color" images by flood-filling each outline's interior — colors are solid
fills, so these can be built automatically instead of hand-made like the
old gabor-patch composites.

It also writes vector (SVG) versions of every outline and composite, which
the experiment shows instead of the PNGs: the source outlines are small,
barely anti-aliased bitmaps, so they look jagged when scaled and rotated.
Each outline is traced into a polygon (boundary trace, then straightened
with Douglas-Peucker so pixel stair-steps become clean straight edges) and
drawn with the same line thickness as the source.

Re-run this only if the underlying shape/color source files change. It does
not touch generate_design.py or the trial lists.
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


# Max distance (in source pixels) a traced edge may stray from the pixel
# boundary when straightened. Large enough to remove stair-steps, small
# enough to keep real details like legs and notches.
TRACE_TOLERANCE_PX = 2.0

FOUR_CONNECTED = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])


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


def outline_masks(outline_path, line_alpha_threshold=128):
    # Same line/interior split as composite_shape_color.
    array = np.array(Image.open(outline_path).convert("RGBA"))
    is_line = array[:, :, 3] >= line_alpha_threshold
    labels, _ = label(~is_line, structure=FOUR_CONNECTED)
    is_interior = (~is_line) & (labels != labels[0, 0])
    return is_line, is_interior


def trace_boundary(mask):
    # Moore-neighbour trace around the shape's outer boundary, returning the
    # boundary pixels' centers as (x, y) in order.
    ys, xs = np.nonzero(mask)
    first = np.lexsort((xs, ys))[0]
    start = current = (ys[first], xs[first])
    steps = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    direction = 6
    points = [start]
    while True:
        for k in range(8):
            d = (direction + k) % 8
            y, x = current[0] + steps[d][0], current[1] + steps[d][1]
            if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] and mask[y, x]:
                current, direction = (y, x), (d + 6) % 8
                break
        if current == start and len(points) > 2:
            break
        points.append(current)
    return np.array([(x + 0.5, y + 0.5) for y, x in points])


def douglas_peucker(points, tolerance):
    start, end = points[0], points[-1]
    dx, dy = end - start
    length = np.hypot(dx, dy)
    rel = points - start
    if length:
        distances = np.abs(dx * rel[:, 1] - dy * rel[:, 0]) / length
    else:
        distances = np.hypot(rel[:, 0], rel[:, 1])
    farthest = int(np.argmax(distances))
    if distances[farthest] <= tolerance:
        return np.array([start, end])
    return np.vstack([douglas_peucker(points[:farthest + 1], tolerance)[:-1],
                      douglas_peucker(points[farthest:], tolerance)])


def trace_polygon(outline_path):
    # Returns the straightened outline polygon and the source line thickness.
    is_line, is_interior = outline_masks(outline_path)
    boundary = trace_boundary(is_line | is_interior)
    # A closed loop: split it at the point farthest from the start and
    # straighten each half, so both split points are kept as corners.
    split = int(np.argmax(np.hypot(*(boundary - boundary[0]).T)))
    loop = np.vstack([boundary, boundary[:1]])
    polygon = np.vstack([douglas_peucker(loop[:split + 1], TRACE_TOLERANCE_PX)[:-1],
                         douglas_peucker(loop[split:], TRACE_TOLERANCE_PX)[:-1]])
    perimeter = np.hypot(*np.diff(np.vstack([polygon, polygon[:1]]), axis=0).T).sum()
    return polygon, is_line.sum() / perimeter


def write_svg(polygon, line_width, size, fill, out_path):
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in polygon) + " Z"
    width, height = size
    out_path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f'<path d="{path}" fill="{fill}" stroke="#000" stroke-width="{line_width:.2f}" stroke-linejoin="round"/>'
        f'</svg>\n'
    )


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
        polygon, line_width = trace_polygon(shape_file)
        size = Image.open(shape_file).size
        write_svg(polygon, line_width, size, "none", config["outlines_dir"] / f"{shape_id}.svg")
        for color_file in color_files:
            fill_id = color_file.stem
            color_rgb = sample_color(color_file)
            out_path = config["shapes_dir"] / f"{shape_id}_{fill_id}.png"
            composite_shape_color(shape_file, color_rgb, out_path)
            write_svg(polygon, line_width, size, "#%02X%02X%02X" % color_rgb, out_path.with_suffix(".svg"))

    print(f"wrote {len(shape_files) * len(color_files)} composite images (PNG + SVG) to {config['shapes_dir']}")


def main():
    for name, config in CONDITIONS.items():
        prepare_condition(name, config)


if __name__ == "__main__":
    main()

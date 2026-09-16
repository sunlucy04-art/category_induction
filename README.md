# GitHub Upload Instructions for the Current Experiment

Upload the contents of this folder to GitHub:

`outputs/github_upload_package/`

The easiest option is to upload the whole folder contents together. The main website file is `index.html`.

## What Each File Does

- `index.html`: the experiment page GitHub Pages will open automatically. Only loads the jsPsych/plugin libraries, the page styling, and `experiment.js`.
- `experiment.js`: all of the actual experiment logic — reads `master_trial_list.csv`, shuffles the trial order (a fresh order per participant), builds each trial's example board/probe/choices, randomizes which side each choice lands on, and records responses.
- `master_trial_list.csv`: the trial list. One row per trial (25 rows). Every image the trial needs is already spelled out on that row: the target outline, the two gabor choice images, and all 8 evidence item images (`item1_name`...`item8_name`) — nothing else needs to be cross-referenced at runtime.
- `generate_trials.py`: the code that generates `master_trial_list.csv` (and the debug/QA files below) from the category-design rules. Keep this so the design can be changed later.

## `experiment_design_reference/` (not read by the live experiment)

These are generated for sanity-checking the design by eye, but `index.html`/`experiment.js` do not read them — don't upload this folder as part of the experiment itself:

- `proportion_design_summary.csv`: a per-category summary of the statistical makeup (does the category-wide dominant fill and the critical shape's own dominant fill actually show up as often as intended) for checking and explaining the design.
- `proportion_example_board.png` / `proportion_example_board_annotated.png`: a rendered board showing every category's examples.
- `proportion_example_list.csv` / `proportion_single_category_example_list.csv`: item-level rows behind those boards.

## Required Image Folders

These folders must stay in the same structure. `generate_trials.py` discovers shapes and fills straight from what's in these folders (nothing is hard-coded), so a different stimulus set just needs its own files dropped into folders with this structure — point `SETTINGS["outlines_dir"]`/`"fill_dir"`/`"shapes_dir"` at them:

- `images/shape_outines/`: one outline image per shape, named `{shape_id}.png`.
- `images/gabor_frequencies/`: one image per fill (gabor pattern, color, etc.), named `{fill_id}.png`.
- `images/all_shapes/`: one composite image per shape x fill combination, named `{shape_id}_{fill_id}.png`.

The CSV points to these individual images by their exact filenames. The experiment combines them on the page.

## Important

Do not upload or rely on anything in `past_files/`. That folder holds earlier, superseded versions (old trial-list formats, an earlier draft experiment page, old placeholder SVGs) kept only for reference — nothing in the current pipeline reads from it.

## Quick Check

- 25 trials in `master_trial_list.csv`
- 200 individual example rows in `experiment_design_reference/proportion_single_category_example_list.csv` (debug only)
- 44 image files used by the CSVs (32 composite shape+fill images, 8 outlines, 4 fill patches)

If you change the design later, rerun `generate_trials.py`, then upload the new CSV files and any new image files.

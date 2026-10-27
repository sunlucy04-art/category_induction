# Pilot 2: Kids' Drawings Induction Task

Built from the advisor's one-block demo (`advisor_demo/`), using the pilot 1 shape and color stimuli. Pilot 1's code lives untouched in `../pilot1/`.

## Design

Nameability is **between-subject**: each participant is assigned to `high_nameability` or `low_nameability` at the setup screen (or with `?condition=high|low`).

Every participant learns exactly the demo's three categories (Lucy, Sam, Ana) with the demo's structure (`advisor_demo/training_trials_1block.csv`): 4 shapes (S1–S4), 5 colors (C1–C5), 24 drawings.

- **Training**: the 24 drawings, shown one at a time with "<kid> drew this." (2500 ms each, 500 ms gap), cycled through **4 training blocks**, each in a fresh random order (96 drawings).
- **One-back attention checks**: after 25% of training drawings (6 per block), one question about the drawing just shown: "Who drew the last drawing?", "What color was the last drawing?" or "What shape was the last drawing?", with 2 of each type per block. No feedback.
- **Test**: 26 trials, all shuffled together:
  - the advisor's 13 (agree, classic disagree, cross-category conflict, category only, kid not named, and Ana's 2 memory probes)
  - **who_drew** (6): a drawing from training (each kid's shape in the color that kid mostly used for it); choose Lucy/Sam/Ana
  - **memory_probe** (4 more, so every kid × shape is covered): "What color did Sam use for this shape?"
  - **most_frequent_shape** (3): "Which shape did Sam draw most often?", choosing from the 4 shape outlines
- Answer options (swatches, shapes, names) are shuffled on every trial. Every drawing shown gets a small random rotation (±8°) and scale change (0.88–1.09×).

**Design versions**: each condition's 8 shapes are split into 2 versions of 4, and the 5 colors are assigned to C1–C5 differently in each version. Each participant gets one version (picked by the seed). `design_versions.csv` lists which shape/color fills each role in each version.

The FIT and IRQ questionnaires, per-section DataPipe saving, and the Qualtrics redirect work the same as in pilot 1.

## Files

- `index.html` / `experiment.js`: the experiment. The number of training blocks, timing, one-back proportion, jitter ranges and the DataPipe ID are constants at the top of `experiment.js`.
- `training_trials.csv`, `test_trials.csv`: every design version's training drawings and test trials, with image paths spelled out. These are generated, so don't hand-edit them.
- `design_versions.csv`: role → stimulus mapping per version (for analysis; not read by the experiment).
- `generate_design.py`: builds the three CSVs above from the advisor's template. It runs `advisor_demo/make_test_trials.py` (unchanged) for the 13 core test trials and adds the memory trials itself.
- `prepare_nameability_stimuli.py`: makes the filled shape images from the selected outlines and colors (same as pilot 1, now with 5 colors per condition: yellow `high_color3` and slate `low_color10` were added).
- `advisor_demo/`: the advisor's demo page, template CSVs and test-trial script.

## Regenerating

1. If the selected shapes/colors change (`images/shape_outines/*_selected`, `images/target_feature/*_selected`), run `python3 prepare_nameability_stimuli.py`.
2. Run `python3 generate_design.py`.

## Saved data

`<subjCode>_induction.csv` has one row per training drawing (`phase = training`), one-back check (`phase = one_back`) and test trial (`phase = test`). Columns:

- `design`, `training_block`, `trial_num` (order within the training block or test phase), `one_back_type`
- the trial-list columns (for one-back rows, those of the drawing being asked about)
- `rotation`/`scale` of the drawing shown
- `response_type` (color/shape/kid) and `option_order` (codes, left to right)
- the choice: `response_position` (1–N), `response_code` (C1–C5, S1–S4 or kid name), `response_id` (actual color/shape file), `response_key` (what that choice means on this trial, e.g. "Lucy's usual (category answer)")
- `correct_answer` and `is_correct` (for one-back and memory trials), and `rt`

## Before running

- Set `DATA_PIPE_EXPERIMENT_ID` in `experiment.js` to a **new** pilot 2 pipe. Until then, data is saved as local downloads.
- Check `QUALTRICS_URL`; it still points at the pilot 1 survey.

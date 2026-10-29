# Pilot 2: Kids' Drawings Induction Task

Built from the advisor's one-block demo (`advisor_demo/`), using the pilot 1 shape and color stimuli. Pilot 1's code lives untouched in `../pilot1/`.

## Design

Nameability is **between-subject**: each participant is assigned to `high_nameability` or `low_nameability` at the setup screen (or with `?condition=high|low`).

Every participant learns exactly the demo's three categories (Lucy, Sam, Ana) with the demo's structure (`advisor_demo/training_trials_1block.csv`): 4 shapes (S1–S4), 5 colors (C1–C5), 24 drawings.

- **Training**: the 24 drawings, shown one at a time with "<kid> drew this." (2500 ms each, 500 ms gap), cycled through **4 training blocks**, each in a fresh random order (96 drawings).
- **One-back attention checks**: 8 per training block, each placed after a randomly chosen drawing (24 drawings + 8 checks = 32 trials, a quarter of them checks). Each asks about the drawing just shown: "Who drew the last drawing?", "What color was the last drawing?" or "What shape was the last drawing?". Types are split 3/3/2 within a block, rotating which type gets 2 (11/11/10 over the 4 blocks). No feedback.
- **Test**: 32 trials, all shuffled together:
  - the advisor's 13 (agree, classic disagree, cross-category conflict, category only, kid not named, and Ana's 2 memory probes), minus his Ana + S1 cross-category trial (T10): cross-category trials for Ana aren't meaningful, so only Lucy's and Sam's are kept
  - 7 more **prediction** trials for kid + shape pairings the advisor's set doesn't use, so every meaningful pairing is tested once (17 prediction trials) and no trial repeats: cross-category Lucy + S2, Sam + S1; classic disagree Ana + S4; agree Ana + S3; kid not named S1, S2, S3 (S3 is a control, since every kid draws it)
  - **who_drew** (6): a drawing from training (each kid's shape in the color that kid mostly used for it); choose Lucy/Sam/Ana
  - **memory_probe** (4 more, so every kid × shape is covered): "What color did Sam use for this shape?"
  - **most_frequent_shape** (3): "Which shape did Sam draw most often?", choosing from the 4 shape outlines
- Answer options (swatches, shapes, names) are shuffled on every trial. Every drawing has a fixed tilt from the advisor's demo formula, `((t*37) % 17) - 8` degrees, where t is the drawing's `token` number plus the length of the kid's name (training) or 20 (every test figure). So every participant sees exactly the same drawings; nothing about them depends on the seed. The demo's size change is left out (size stays the same).

**Shapes** are fixed (`SHAPE_ROLES` in `generate_design.py`), with the same shape numbers in both conditions:

| Role | Shape | Drawn by |
|---|---|---|
| S1 | shape 13 | Lucy only |
| S2 | shape 1 | Sam only |
| S3 | shape 10 | every kid |
| S4 | shape 7 | Ana only |

**Colors** are also fixed for everyone (`COLOR_ROLES` in `generate_design.py`), matched to the advisor's demo colors as closely as our sets allow. There is no counterbalancing of which shape or color plays which role (yet).

| Role | High nameability | Low nameability |
|---|---|---|
| C1 Lucy's usual | red (`high_color1`) | dusty pink (`low_color1`) |
| C2 Sam's usual | blue (`high_color4`) | slate (`low_color10`) |
| C3 Ana's usual | yellow (`high_color3`) | terracotta (`low_color2`) |
| C4 every S4 (Ana's shape) | orange (`high_color2`) | olive (`low_color3`) |
| C5 2 of 3 of Lucy's S1s and Sam's S2s | purple (`high_color5`) | pale lime (`low_color6`) |

**Instructions** tell participants their job is to learn which drawings belong to which kid, and outline the three parts: a learning phase (watch the drawings, with occasional quick checks on the last drawing), a question phase, and a questionnaire phase, after which the study is complete. One page shows an example learning-phase drawing, using a kid (Max), shape (4) and color that never appear in the real trials; `prepare_nameability_stimuli.py` makes it in `images/<condition>/instruction_examples/`, matched to the participant's condition. There is no practice and no example of the test questions. The real kids' names first appear on the start screen. A self-paced "Take a break!" page follows each training block except the last, and "Great job!" pages introduce the question phase and the questionnaire phase.

**Demo mode** (`?demo=true` or the setup checkbox): 10 learning trials (7 drawings + one check of each type), the pre-test instructions, then 15 test trials that always include at least one of every test type. The questionnaires still run in full.

The FIT and IRQ questionnaires, per-section DataPipe saving, and the Qualtrics redirect work the same as in pilot 1.

## Files

- `index.html` / `experiment.js`: the experiment. The number of training blocks, timing, one-back proportion and the DataPipe ID are constants at the top of `experiment.js`.
- `training_trials.csv`, `test_trials.csv`: each condition's training drawings and test trials, with image paths spelled out. These are generated, so don't hand-edit them.
- `design_roles.csv`: role → stimulus mapping per condition (for analysis; not read by the experiment).
- `make_overview.py` / `overview_template.html` → `kids_drawings_pilot2_demo.html`: a single-file walkthrough of the design in the style of the advisor's demo (legend, training stepper, attention checks, every test trial with its answer key, and trial counts by type), built from the files above. Open it in a browser or send it as an attachment. Re-run `python3 make_overview.py` after design changes.
- `generate_design.py`: builds the three CSVs above from the advisor's template. It runs `advisor_demo/make_test_trials.py` (unchanged) for the 13 core test trials and adds the memory trials itself.
- `prepare_nameability_stimuli.py`: makes the filled shape images from the selected outlines and colors (same as pilot 1, now with 5 colors per condition: yellow `high_color3` and slate `low_color10` were added). It also traces every outline into a vector SVG (outline and filled versions), and the experiment shows those SVGs instead of the PNGs so the drawings stay smooth when scaled and rotated. `TRACE_TOLERANCE_PX` controls how much pixel stair-stepping gets straightened out.
- `advisor_demo/`: the advisor's demo page, template CSVs and test-trial script.

## Regenerating

1. If the selected shapes/colors change (`images/shape_outines/*_selected`, `images/target_feature/*_selected`), run `python3 prepare_nameability_stimuli.py`.
2. Run `python3 generate_design.py`.

## Saved data

`<subjCode>_induction.csv` has one row per training drawing (`trial_type = training`, `phase = training`), attention check (`trial_type = attention_check`, `phase = training`) and test trial (`trial_type = test`, `phase = test`). Columns:

- `training_block`, `trial_num` (order within the training block or test phase; an attention check shares the number of the drawing it asks about), `attention_check_type` (kid/color/shape)
- `stimulus`: the trial-list ID (L01–L24 for drawings, T01–T32 for test trials); for attention-check rows, the drawing being asked about
- the other trial-list columns, except `design` (always the same as `condition`), `response_type` (follows from `test_type` / `attention_check_type`) and the image file paths (`shape_id`, `color_id` and `opt*_id` name the stimuli). `color` / `color_id` is the color of the drawing shown: training drawings and `who_drew` test trials (the other test figures are uncolored outlines)
- `rotation`/`scale` of the drawing shown
- `option_order`: the options' codes, left to right on screen
- the choice: `response` (what was chosen: C1–C5, S1–S4 or a kid's name), `response_id` (the chosen color/shape file, or the kid's name), `response_key` (what that choice means on this trial, e.g. "Lucy's usual (category answer)"), `strategy` (the same thing as a kid-agnostic code, identical across functionally equivalent trials: `category`, `conjunction`, `shape_based`, `shape_drawer_category`, `named_kid_other_color`, or else `other_kid_category` / `never_used`; memory trials use `correct` plus error codes. A choice that fits more than one strategy lists them all, joined with `-` (e.g. `conjunction-shape_based`, `correct-category`). The full list is in `option_strategy` in `generate_design.py`, and `strategy_opt1`–`strategy_opt5` give every option's code). Blank on attention checks
- `correct_answer` and `is_correct` (for attention checks and memory trials), and `rt`

## Before running

- `DATA_PIPE_EXPERIMENT_ID` is set to pilot 2's own pipe (`JRZFIrsm3u4n`). Make sure data collection is switched on for it in DataPipe.
- Check `QUALTRICS_URL`; it still points at the pilot 1 survey.

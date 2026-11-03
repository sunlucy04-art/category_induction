# Pilot 2: Kids' Drawings Induction Task

Built from the advisor's one-block demo (`advisor_demo/`), using the pilot 1 shape and color stimuli. Pilot 1's code lives untouched in `../pilot1/`.

## Design

Pilot 2 runs **only the high nameability stimuli**, so nameability isn't manipulated. The manipulation is the category design and the test trial types, both within-subject. The low nameability stimuli and trial-list rows are still generated (`generate_design.py`), but the experiment doesn't use them; `CONDITION` in `experiment.js` sets which rows run.

Every participant learns exactly the demo's three categories (Lucy, Sam, Ana) with the demo's structure (`advisor_demo/training_trials_1block.csv`): 4 shapes (S1–S4), 5 colors (C1–C5), 24 drawings.

- **Training**: the 24 drawings, shown one at a time with "<kid> drew this." (2500 ms each, 500 ms gap), cycled through **4 training blocks**, each in a fresh random order (96 drawings).
- **One-back attention checks**: 6 per training block, each placed after a randomly chosen drawing (one check for every 4 drawings; 30 trials per block). Each asks about the drawing just shown: "Who drew the last drawing?", "What color was the last drawing?" or "What shape was the last drawing?". Types are split 2/2/2 within a block (8 of each over the 4 blocks). No feedback.
- **Test**: 32 trials, all shuffled together:
  - the advisor's 13 (agree, classic disagree, cross-category conflict, category only, kid not named, and Ana's 2 memory probes), minus his Ana + S1 cross-category trial (T10): cross-category trials for Ana aren't meaningful, so only Lucy's and Sam's are kept
  - 7 more **prediction** trials for kid + shape pairings the advisor's set doesn't use, so every meaningful pairing is tested once (17 prediction trials) and no trial repeats: cross-category Lucy + S2, Sam + S1; classic disagree Ana + S4; agree Ana + S3; kid not named S1, S2, S3 (S3 is a control, since every kid draws it)
  - **who_drew** (6): a drawing from training (each kid's shape in the color that kid mostly used for it); choose Lucy/Sam/Ana
  - **memory_probe** (4 more, so every kid × shape is covered): "What color did Sam use for this shape?"
  - **most_frequent_shape** (3): "Which shape did Sam draw most often?", choosing from the 4 shape outlines
- Answer options (swatches, shapes, names) are shuffled on every trial. Every drawing has a fixed tilt from the advisor's demo formula, `((t*37) % 17) - 8` degrees, where t is the drawing's `token` number plus the length of the kid's name (training) or 20 (every test figure). So every participant sees exactly the same drawings; nothing about them depends on the seed. The demo's size change is left out (size stays the same).

**Shapes** are fixed (`SHAPE_ROLES` in `generate_design.py`), using these shape numbers:

| Role | Shape | Drawn by |
|---|---|---|
| S1 | shape 13 | Lucy only |
| S2 | shape 1 | Sam only |
| S3 | shape 10 | every kid |
| S4 | shape 7 | Ana only |

**Colors** are counterbalanced across **5 color versions**, so no result hinges on one kid having especially memorable colors (e.g. Sam's being blue and purple). Each version shuffles which real color plays each color role; across the versions, every color plays every role exactly once (a Latin square: version v shifts `COLOR_ROLES` in `generate_design.py` v − 1 places along C1–C5). The researcher picks the version at the setup screen (or `?colorVersion=1`–`5`) and cycles through them so counts stay balanced. Shapes are the same in every version.

| Role | v1 | v2 | v3 | v4 | v5 |
|---|---|---|---|---|---|
| C1 Lucy's usual | red | blue | yellow | orange | purple |
| C2 Sam's usual | blue | yellow | orange | purple | red |
| C3 Ana's usual | yellow | orange | purple | red | blue |
| C4 every S4 (Ana's shape) | orange | purple | red | blue | yellow |
| C5 2 of 3 of Lucy's S1s and Sam's S2s | purple | red | blue | yellow | orange |

File numbers: red `high_color1`, blue `high_color4`, yellow `high_color3`, orange `high_color2`, purple `high_color5`. Everything else about the design (trials, answer keys, strategy codes) is identical across versions; the trial lists hold every trial once per version (`color_version`).

**Instructions** tell participants their job is to learn which drawings belong to which kid, and outline the three parts: a learning phase (watch the drawings, with occasional quick checks on the last drawing), a question phase, and a questionnaire phase, after which the study is complete. One page shows an example learning-phase drawing, using a kid (Max), shape (4) and color that never appear in the real trials; `prepare_nameability_stimuli.py` makes it in `images/<condition>/instruction_examples/`, matched to the participant's condition. There is no practice and no example of the test questions. The real kids' names first appear on the start screen. A self-paced "Take a break!" page follows each training block except the last, and "Great job!" pages introduce the question phase and the questionnaire phase.

**Demo mode** (`?demo=true` or the setup checkbox): 10 learning trials (7 drawings + one check of each type), the pre-test instructions, then 15 test trials that always include at least one of every test type. The questionnaires still run in full.

The FIT and IRQ questionnaires, per-section DataPipe saving, and the Qualtrics redirect work the same as in pilot 1.

## Files

- `index.html` / `experiment.js`: the experiment. The number of training blocks, timing, one-back proportion and the DataPipe ID are constants at the top of `experiment.js`.
- `training_trials.csv`, `test_trials.csv`: each condition's training drawings and test trials. Stimuli are given as role codes (`shape_role` / `color_role`), file numbers (`shape` / `color`) and the file name shown (`shape_name`); the experiment builds the image paths from these. These are generated, so don't hand-edit them.
- `shape_color_roles.csv`: which shape/color file fills each role (S1–S4, C1–C5) per condition and color version, with the file number, color name and the role's job in the design (for analysis; not read by the experiment).
- `make_strategy_schematic.py` → `strategy_schematic.html`: a one-page map of every prediction and color-memory trial, grouped by category structure, showing each answer option's strategy code.
- `make_overview.py` / `overview_template.html` → `kids_drawings_pilot2_demo.html`: a single-file walkthrough of the design in the style of the advisor's demo (legend, training stepper, attention checks, every test trial with its answer key, and trial counts by type), built from the files above. Open it in a browser or send it as an attachment. Re-run `python3 make_overview.py` after design changes.
- `generate_design.py`: builds the three CSVs above from the advisor's template. It runs `advisor_demo/make_test_trials.py` (unchanged) for the 13 core test trials and adds the memory trials itself.
- `prepare_nameability_stimuli.py`: makes the filled shape images from the selected outlines and colors (same as pilot 1, now with 5 colors per condition: yellow `high_color3` and slate `low_color10` were added). It also traces every outline into a vector SVG (outline and filled versions), and the experiment shows those SVGs instead of the PNGs so the drawings stay smooth when scaled and rotated. `TRACE_TOLERANCE_PX` controls how much pixel stair-stepping gets straightened out.
- `advisor_demo/`: the advisor's demo page, template CSVs and test-trial script.

## Regenerating

1. If the selected shapes/colors change (`images/shape_outines/*_selected`, `images/target_feature/*_selected`), run `python3 prepare_nameability_stimuli.py`.
2. Run `python3 generate_design.py`.

## Saved data

`<subjCode>_induction.csv` has one row per training drawing (`trial_type = training`), attention check (`attention_check`) and test trial (`test`). It records what happened; everything fixed by the design (the prompt, every option with its answer key and strategy code, image files) is in `test_trials.csv` / `training_trials.csv`, joined by `trial_id`. Columns:

- **Session**: `subjCode`, `random_seed`, `color_version` (1–5), `questionnaire_order` (`fit_first` / `irq_first`)
- **Order**: `trial_type`; `training_block` (blank for test trials); `trial_num` (order within the training block or test phase; an attention check shares the number of the drawing it asks about); `trial_index` (order across the whole file); `time_elapsed` (ms since the session started, so break lengths can be worked out)
- **Trial**: `stimulus` (what was on screen: a kid's shape-color combination, `Lucy01`–`Lucy03`, `Sam01`–`Sam03`, `Ana01`–`Ana02`, for training drawings, attention checks (the drawing asked about) and "Who drew this?" trials; `O` plus the shape number for an uncolored outline, e.g. `O13`; `prompt_only` when no shape is shown); `trial_id` (test trials only: T01–T33, for joining to `test_trials.csv`); `test_type`; `trial_group` (functionally equivalent test trials, see `trial_group` in `generate_design.py`); `attention_check_type` (kid/color/shape); `kid`; `shape_role` (S1–S4) and `shape` (its file number, e.g. 13); `color_role` (C1–C5) and `color` (its file number, e.g. 5); `shape_name` (the file shown: `high_shape13_high_color5` for a drawing, `high_shape13` for an outline). Each is blank when it wasn't shown: no kid named, no shape, or an uncolored outline. See `shape_color_roles.csv` for what each role does. `rotation` of the drawing shown
- **Response**: `option_order` (option codes, left to right on screen); `response_role` (what was chosen, as a role: C1–C5, S1–S4 or a kid's name) and `response` (the same choice as the chosen color's or shape's file number, e.g. 5, or the kid's name); `strategy` (what the choice reflects, as a kid-agnostic code identical across functionally equivalent trials: `most_frequent_color_kid_match`, `conjunction_kid_match`, `conjunction_other_kid`, `most_frequent_color_other_kid`, `named_kid_other_color`, or else `most_frequent_unrelated_kid` / `never_used`; memory trials use `correct` plus error codes. A choice that fits more than one strategy lists them all, joined with `-`, e.g. `most_frequent_color_kid_match-conjunction_kid_match`. Blank on attention checks; see `option_strategy` in `generate_design.py`); `correct_answer` and `is_correct` (1/0; attention checks and memory trials only); `rt` (blank for the timed training drawings)

## Before running

- `DATA_PIPE_EXPERIMENT_ID` is set to pilot 2's own pipe (`JRZFIrsm3u4n`). Make sure data collection is switched on for it in DataPipe.
- `QUALTRICS_URL` is set to pilot 2's own final survey (`SV_cXTGxiv3CuC7KDk`); participants are sent there at the end with their subject code.

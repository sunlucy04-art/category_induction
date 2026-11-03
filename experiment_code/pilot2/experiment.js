/*
  PILOT 2: KIDS' DRAWINGS BLOCK VERSION

  What this file does:
  1. Shows a setup screen asking for the subject code, the random seed,
     the color version (1-5), whether to run in demo mode (a short
     single-block run), and the order of the two questionnaires at the end
     (0: IRQ then FIT, or 1: FIT then IRQ) — any of these can also be
     pre-filled via URL params.
  2. Reads training_trials.csv and test_trials.csv (made by
     generate_design.py) and keeps the high nameability rows for this
     participant's color version. All
     randomization (training and test order, one-back check placement,
     answer option order, questionnaire item order) is driven by the seed
     entered at setup, so the same seed reproduces the same session. Each
     drawing's tilt is NOT random: it is fixed per drawing, as in the
     advisor's demo, so every participant sees identical drawings.
  3. Runs the induction task: training shows the 24 drawings one at a time
     with the kid's name, cycled TRAINING_BLOCKS times, with one-back
     attention checks after some drawings. Then the test phase mixes
     prediction trials (choose the color of a new drawing) with memory
     questions (who drew this, what color a kid used for a shape, which
     shape a kid drew most often).
  4. Runs the FIT ("Forms of Inner Thinking") and IRQ questionnaires, in
     whichever order was set at setup — always in full, regardless of demo
     mode.
  5. Saves three separate files per participant — <subjCode>_induction.csv,
     <subjCode>_FIT.csv, <subjCode>_IRQ.csv — to OSF via DataPipe as soon as
     each section finishes (so a participant who doesn't complete the whole
     session still has their earlier sections saved), with an automatic
     local-download fallback if a DataPipe upload fails.
  6. At the very end, redirects to a Qualtrics survey (subject code passed
     through as a URL param) once QUALTRICS_URL is filled in below.
*/

const TRAINING_CSV = "training_trials.csv";
const TEST_CSV = "test_trials.csv";

// Pilot 2 only runs the high nameability stimuli. Nameability isn't being
// manipulated: the manipulation is the category design and the trial types.
const CONDITION = "high_nameability";

// Color counterbalancing: each version shuffles which real color plays each
// color role (see COLOR_VERSIONS in generate_design.py). Chosen at the setup
// screen and cycled through by the researcher so the counts stay balanced.
const COLOR_VERSIONS = 5;

// Training cycles through all 24 drawings this many times, in a fresh
// random order each time.
const TRAINING_BLOCKS = 4;

// How long each training drawing stays on screen, and the blank gap after it.
const TRAINING_DRAWING_MS = 2500;
const TRAINING_GAP_MS = 500;

// One-back attention checks (who drew / what color / what shape was the
// last drawing) per training block, each placed after a randomly chosen
// drawing. 6 checks per 24 drawings: one check for every 4 drawings. The
// three types are split as evenly as possible within a block (2/2/2).
const ONE_BACK_CHECKS_PER_BLOCK = 6;

// Token number the advisor's demo gives every test-phase figure.
const TEST_FIGURE_TOKEN = 20;

// Kid name used only in the instructions' example drawing, so the example
// never uses a real kid (or, via each condition's instruction_examples
// images, a real shape or color).
const INSTRUCTION_KID = "Max";

// From your pipe at https://pipe.jspsych.org — every participant's data
// gets uploaded to whatever OSF project that pipe is linked to. The same
// pipe is used for all three saved files (induction/FIT/IRQ); DataPipe
// just uploads whatever filename each save trial gives it. This is pilot 2's
// own pipe (pilot 1 used "xvMyuhu7p8BK").
const DATA_PIPE_EXPERIMENT_ID = "JRZFIrsm3u4n";

// Pilot 2's final Qualtrics survey: participants are redirected here at the
// end, with their subject code as ?subjCode=. Set it to
// "REPLACE_WITH_YOUR_QUALTRICS_LINK" to end with a thank-you message instead.
const QUALTRICS_URL = "https://uwmadison.co1.qualtrics.com/jfe/form/SV_cXTGxiv3CuC7KDk";

// ?demo=true (or the setup screen's "Demo mode" checkbox) runs a short
// version so the full pipeline — including every DataPipe upload and both
// questionnaires — can be tested fast: one training block cut down to
// DEMO_TRAINING_COUNT drawings with one check of each type (10 learning
// trials), then DEMO_TEST_COUNT test trials that include at least one of
// every test type. The questionnaires always run in full regardless.
const DEMO_TRAINING_COUNT = 7;
const DEMO_CHECKS = 3;
const DEMO_TEST_COUNT = 15;

let participantId;
let demoModeActive = false;

// Normal runs save as "<subjCode>_<baseName>.csv". Demo runs get a unique,
// clearly-labelled filename instead, so repeated test runs don't collide
// with DataPipe's "filename already exists" rejection.
function sessionFilename(baseName) {
  return demoModeActive
    ? `demo_${participantId}_${baseName}_${Date.now()}.csv`
    : `${participantId}_${baseName}.csv`;
}

// ---------------------------------------------------------------------------
// FIT ("Forms of Inner Thinking") questionnaire — Section 3 ("Specific Inner
// Speaking/Hearing") of the instrument.
// ---------------------------------------------------------------------------

const FIT_SHORT_DURATION_MS = 10000;

const FIT_BLOCKS = [
  {
    id: "practice",
    label: "Practice",
    duration: FIT_SHORT_DURATION_MS,
    prompts: ["Imagine hearing the sentence: My cat is cute"],
  },
  {
    id: "block3a",
    label: "Specific Inner Speaking",
    duration: FIT_SHORT_DURATION_MS,
    prompts: [
      "Imagine saying the sentence: English is a language",
      "Imagine saying the sentence: Mathematics is a major",
      "Imagine saying the sentence: Democracy is a system",
      "Imagine saying the sentence: Growth is a process",
      "Imagine saying the sentence: Time is a dimension",
    ],
  },
  {
    id: "block3b",
    label: "Specific Inner Hearing",
    duration: FIT_SHORT_DURATION_MS,
    prompts: [
      "Imagine hearing the sentence: Logic is a tool",
      "Imagine hearing the sentence: Gravity is a force",
      "Imagine hearing the sentence: Ideas are valuable",
      "Imagine hearing the sentence: Honesty is a quality",
      "Imagine hearing the sentence: Learning is a journey",
    ],
  },
];

const FIT_YES_NO = ["Yes", "No"];
const FIT_YES_NO_WORDS = ["Yes", "No", "I did not experience words"];

function buildFITFormsQuestions() {
  return [
    { prompt: "Were words in English part of your inner experience?", name: "lang_english", options: FIT_YES_NO, required: true },
    { prompt: "Were words in a language other than English part of your inner experience?", name: "lang_other", options: FIT_YES_NO, required: true },
    { prompt: "Were visual images part of your inner experience?", name: "visual", options: FIT_YES_NO, required: true },
    { prompt: "Were abstract thoughts and ideas (without words or images) part of your inner experience?", name: "concept", options: FIT_YES_NO, required: true },
    { prompt: "During the experience, were your eyes closed or open?", name: "eyes", options: ["Closed", "Open", "Sometimes open, sometimes closed"], required: true },
    { prompt: "Did you experience the words as having sound in your mind?", name: "auditory", options: FIT_YES_NO_WORDS, required: true },
    { prompt: "Did you experience the words as having a written form in your mind?", name: "orthographic", options: FIT_YES_NO_WORDS, required: true },
    { prompt: "Did you say any words out loud?", name: "artic_outloud", options: FIT_YES_NO_WORDS, required: true },
    { prompt: "While experiencing words, did you physically move your mouth, lips, tongue, or throat?", name: "artic_real", options: FIT_YES_NO_WORDS, required: true },
    { prompt: "While experiencing words, did you imagine moving your mouth, lips, tongue, or throat?", name: "artic_imagined", options: FIT_YES_NO_WORDS, required: true },
    { prompt: "Did you experience the words without any imagined sound, visual form, or movement?", name: "pure_lexical", options: FIT_YES_NO_WORDS, required: true },
  ];
}

const FIT_OTHER_EXPERIENCE_OPTIONS = [
  "Imagined sounds (not of words)",
  "Imagined voice (not of words)",
  "Imagined voice without sounds",
  "Imagined smells",
  "Imagined tastes",
  "Emotions",
  "Imagined bodily sensations",
  "Real bodily sensations",
  "Imagined movements of your body",
  "Real bodily movement",
  "Other",
  "None of the above",
];

// Fixed column order for the tidy FIT CSV, one row per prompt. trial_type is
// required for OSF to accept the data (same fix as in Amelia's code).
const FIT_CSV_COLUMNS = [
  "subjCode", "trial_type", "block", "block_label", "prompt_index", "prompt",
  "lang_english", "lang_other", "visual", "concept", "eyes",
  "auditory", "orthographic", "artic_outloud", "artic_real", "artic_imagined", "pure_lexical",
  "other_experiences", "other_experiences_text",
];

// The 8 example infographics shown during the FIT instructions.
const FIT_EXAMPLE_IMAGES = [
  "images/fit_infographics/infographics-01-cropped.jpg",
  "images/fit_infographics/infographics-02-cropped.jpg",
  "images/fit_infographics/infographics-03-cropped.jpg",
  "images/fit_infographics/infographics-04-cropped.jpg",
  "images/fit_infographics/infographics-05-cropped.jpg",
  "images/fit_infographics/infographics-06-cropped.jpg",
  "images/fit_infographics/infographics-07-cropped.jpg",
  "images/fit_infographics/infographics-08-cropped.jpg",
];

function buildFITPromptTrials(promptText, durationMs, blockId, blockLabel, globalPromptIndex) {
  const displayTrial = {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `<div class="fit-prompt-display">${promptText}</div>`,
    choices: "NO_KEYS",
    trial_duration: durationMs,
    data: {
      screen: "fit_prompt",
      fit_block: blockId,
      fit_block_label: blockLabel,
      fit_prompt: promptText,
      fit_prompt_index: globalPromptIndex,
    },
  };

  const formsTrial = {
    type: jsPsychSurveyMultiChoice,
    preamble: `<p>Please answer the following questions about what you just experienced.</p>`,
    questions: buildFITFormsQuestions(),
    data: {
      fitsave: true,
      screen: "fit_forms_survey",
      fit_block: blockId,
      fit_block_label: blockLabel,
      fit_prompt: promptText,
      fit_prompt_index: globalPromptIndex,
      subjCode: participantId,
    },
  };

  const otherTrial = {
    type: jsPsychSurveyMultiSelect,
    preamble: `<p>In addition to the experiences you already reported, did you experience any of the following? (Select all that apply)</p>`,
    questions: [
      { prompt: "", name: "other_experiences", options: FIT_OTHER_EXPERIENCE_OPTIONS },
    ],
    data: {
      fitsave: true,
      screen: "fit_other_survey",
      fit_block: blockId,
      fit_block_label: blockLabel,
      fit_prompt: promptText,
      fit_prompt_index: globalPromptIndex,
      subjCode: participantId,
    },
  };

  // conditional_function only takes effect on a timeline NODE (one wrapping
  // the trial in its own `timeline: [...]` array) — placing it directly on
  // the trial object, as a plugin parameter, is silently ignored, so the
  // trial would run unconditionally every time.
  const otherTextTrial = {
    timeline: [
      {
        type: jsPsychSurveyText,
        questions: [
          { prompt: 'You selected "Other" — please briefly describe:', name: "other_experiences_text" },
        ],
        data: {
          fitsave: true,
          screen: "fit_other_text",
          fit_block: blockId,
          fit_block_label: blockLabel,
          fit_prompt: promptText,
          fit_prompt_index: globalPromptIndex,
          subjCode: participantId,
        },
      },
    ],
    conditional_function: function() {
      const last = jsPsych.data.get().filter({ screen: "fit_other_survey" }).last(1).trials[0];
      return Boolean(
        last && last.response && last.response.other_experiences &&
        last.response.other_experiences.includes("Other")
      );
    },
  };

  return [displayTrial, formsTrial, otherTrial, otherTextTrial];
}

// One tidy row per prompt (forms + other-experiences answers).
function buildFITCleanCSV() {
  const byIndex = {};

  jsPsych.data.get().filter({ fitsave: true }).trials.forEach(function(t) {
    if (!byIndex[t.fit_prompt_index]) {
      byIndex[t.fit_prompt_index] = {
        subjCode: t.subjCode,
        trial_type: "FIT",
        block: t.fit_block,
        block_label: t.fit_block_label,
        prompt_index: t.fit_prompt_index,
        prompt: t.fit_prompt,
      };
    }
    const row = byIndex[t.fit_prompt_index];
    if (t.screen === "fit_forms_survey") {
      Object.assign(row, t.response);
    } else if (t.screen === "fit_other_survey") {
      row.other_experiences = (t.response.other_experiences || []).join(";");
    } else if (t.screen === "fit_other_text") {
      row.other_experiences_text = t.response.other_experiences_text;
    }
  });

  const orderedRows = Object.values(byIndex).map(function(r) {
    const row = {};
    FIT_CSV_COLUMNS.forEach(function(c) { row[c] = r[c] !== undefined ? r[c] : ""; });
    return row;
  });
  return Papa.unparse(orderedRows);
}

// Builds the full FIT questionnaire timeline: instructions with the example
// images, the prompt/survey loop for every block, and the closing "other
// experiences" follow-up. Always runs in full, regardless of demo mode.
function buildFITTimeline() {
  const timeline = [];

  timeline.push({
    type: jsPsychInstructions,
    pages: [
      `
        <div class="instructions-block">
          <p>You will be asked to imagine saying or hearing a sentence, and then you will be asked some follow-up questions about that experience.</p>
          <p>Click "Next" to see examples of the different kinds of questions you will be asked about your experience.</p>
        </div>
      `,
      ...FIT_EXAMPLE_IMAGES.map(function(src) {
        return `
          <div class="instructions-block">
            <p class="fit-example-caption">Imagine saying the phrase: My cat is cute</p>
            <img class="fit-example-image" src="${src}" alt="Example of a form of inner experience">
          </div>
        `;
      }),
      `
        <div class="instructions-block">
          <p>Keep these examples in mind as you answer. Press "Next" to begin with a practice prompt.</p>
        </div>
      `,
    ],
    show_clickable_nav: true,
    key_forward: "ArrowRight",
    key_backward: "ArrowLeft",
    data: { screen: "fit_instructions" },
  });

  let globalPromptIndex = 0;
  FIT_BLOCKS.forEach(function(block) {
    const prompts = jsPsych.randomization.shuffle(block.prompts);
    prompts.forEach(function(promptText) {
      globalPromptIndex += 1;
      timeline.push(...buildFITPromptTrials(promptText, block.duration, block.id, block.label, globalPromptIndex));
    });
  });

  pushSaveTimeline(timeline, sessionFilename("FIT"), buildFITCleanCSV);

  return timeline;
}

// ---------------------------------------------------------------------------
// IRQ questionnaire — 38 items (plus 2 catch items) on a 5-point Likert scale.
// ---------------------------------------------------------------------------

const IRQ_LIKERT_LABELS = [
  "Strongly disagree",
  "Somewhat disagree",
  "Neither agree nor disagree",
  "Somewhat agree",
  "Strongly agree",
];

const IRQ_ITEMS = [
  { name: "Factor1_1", text: "I often enjoy the use of mental pictures to reminisce" },
  { name: "Factor1_2", text: "I can close my eyes and easily picture a scene I have experienced" },
  { name: "Factor1_3", text: "My mental images are very vivid and photographic" },
  { name: "Factor1_4", text: "The old saying 'A picture is worth a thousand words' is certainly true for me" },
  { name: "Factor1_5", text: "When I think about someone I know well, I instantly see their face in my mind" },
  { name: "Factor1_6", text: "I rarely use mental images or pictures to help me remember things" },
  { name: "Factor1_7", text: "My memories are mainly visual in nature" },
  { name: "Factor1_8", text: "When traveling to get to somewhere I tend to think more verbally than visually" },
  { name: "Factor1_9", text: "If I talk to myself in my head it is rarely accompanied by visual imagery" },
  { name: "Factor1_10", text: "If I imagine my memories visually they are more often static than moving" },
  { name: "Factor2_1", text: "I think about problems in my mind in the form of a conversation with myself" },
  { name: "Factor2_2", text: "If I am walking somewhere by myself, I rarely have a silent conversation with myself" },
  { name: "Factor2_3", text: "If I am walking somewhere by myself, I frequently think of conversations that I've recently had" },
  { name: "Factor2_4", text: "My inner speech helps my imagination" },
  { name: "Factor2_5", text: "I tend to think things through verbally when I am relaxing" },
  { name: "Factor2_6", text: "When thinking about a personal problem, I rarely talk it through in my head" },
  { name: "Factor2_7", text: "I like to give myself some down time to talk through thoughts in my mind" },
  { name: "Factor2_8", text: "I don't hear words in my 'mind's ear' when I think" },
  { name: "Factor2_9", text: "I rarely vocalize thoughts in my mind" },
  { name: "Factor2_10", text: "I often talk to myself internally while watching TV" },
  { name: "Factor2_11", text: "My memories rarely involve conversations I've had" },
  { name: "Factor2_12", text: "When I read, I tend to hear a voice in my 'mind's ear'" },
  { name: "Factor3_1", text: "When I hear someone talking, I see words written down in my mind" },
  { name: "Factor3_2", text: "I don't see words in my 'mind's eye' when I think" },
  { name: "Factor3_3", text: "When I am introduced to someone for the first time, I imagine what their name would look like when written down" },
  { name: "Factor3_4", text: "A strategy I use to help me remember written material is imagining what the writing looks like" },
  { name: "Factor3_5", text: "I hear a running summary of everything I am doing in my head" },
  { name: "Factor3_6", text: "I rehearse in my mind how someone might respond to a text message before I send it" },
  { name: "Factor4_1", text: "I can easily imagine and mentally rotate three-dimensional geometric figures" },
  { name: "Factor4_2", text: "It is hard for me to imagine this sentence in my mind pronounced unnaturally slowly" },
  { name: "Factor4_3", text: "In school, I had no problems with geometry" },
  { name: "Factor4_4", text: "It is easy for me to imagine the sensation of licking a brick" },
  { name: "Factor4_5", text: "I find it difficult to imagine how a three-dimensional geometric figure would exactly look like when rotated" },
  { name: "Factor4_6", text: "I can easily imagine someone clearly talking, and then imagine the same voice with a heavy cold" },
  { name: "Factor4_7", text: "I think I have a large vocabulary in my native language compared to other people" },
  { name: "Factor4_8", text: "I can easily imagine the sound of a trumpet getting louder" },
  { name: "catch1", text: "Select the middle option for this item" },
  { name: "catch2", text: "Five minus two is three" },
];

// Fixed CSV column order: subjCode + trial_type + one column per IRQ item,
// in the item's canonical (non-randomized) order, regardless of the order
// it was presented in. trial_type is required for OSF to accept the data
// (same fix as in Amelia's code).
const IRQ_CSV_COLUMNS = ["subjCode", "trial_type", ...IRQ_ITEMS.map(function(q) { return q.name; })];

function buildIRQCleanCSV() {
  const trial = jsPsych.data.get().filter({ irqsave: true }).last(1).trials[0];
  const row = {};
  IRQ_CSV_COLUMNS.forEach(function(c) {
    if (c === "subjCode") {
      row[c] = trial ? trial.subjCode : participantId;
    } else if (c === "trial_type") {
      row[c] = "IRQ";
    } else {
      row[c] = trial && trial.response && trial.response[c] !== undefined ? trial.response[c] : "";
    }
  });
  return Papa.unparse([row]);
}

// Builds the IRQ questionnaire timeline: a short intro and the 38-item
// Likert matrix (item order randomized per participant). Always runs in
// full, regardless of demo mode.
function buildIRQTimeline() {
  const timeline = [];

  timeline.push({
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
      <div class="instructions-block">
        <p>Please select a response for each statement. Make sure to read each question carefully.</p>
        <p>Press any key to continue.</p>
      </div>
    `,
    data: { screen: "irq_instructions" },
  });

  timeline.push({
    type: jsPsychSurveyLikert,
    preamble: `<p>Please select a response for each statement. Make sure to read each question carefully.</p>`,
    questions: jsPsych.randomization.shuffle(IRQ_ITEMS).map(function(item) {
      return { prompt: item.text, name: item.name, labels: IRQ_LIKERT_LABELS, required: true };
    }),
    data: { irqsave: true, screen: "irq_survey", subjCode: participantId },
  });

  pushSaveTimeline(timeline, sessionFilename("IRQ"), buildIRQCleanCSV);

  return timeline;
}

// ---------------------------------------------------------------------------
// Data saving — shared by the induction task and both questionnaires. Each
// section saves itself to DataPipe as soon as it finishes, with a local CSV
// download as a fallback if the upload doesn't look like it succeeded.
// ---------------------------------------------------------------------------

function downloadCSVBackup(filename, csvString) {
  const blob = new Blob([csvString], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Pushes a DataPipe save trial (or a local-only download, if DataPipe isn't
// configured) for whatever buildCSV() returns at the time the trial runs,
// plus a message shown only if the upload failed.
function pushSaveTimeline(timeline, filename, buildCSV) {
  const datapipeConfigured = DATA_PIPE_EXPERIMENT_ID !== "REPLACE_WITH_YOUR_DATAPIPE_ID";

  if (!datapipeConfigured) {
    timeline.push({
      type: jsPsychHtmlKeyboardResponse,
      stimulus: `<div class="instructions-block"><p>(Saving a local copy of the data to your downloads folder.)</p></div>`,
      choices: "NO_KEYS",
      trial_duration: 1500,
      on_start: function() {
        try {
          downloadCSVBackup(filename, buildCSV());
        } catch (e) {
          console.error(`Local save failed for ${filename}:`, e);
        }
      },
    });
    return;
  }

  timeline.push({
    type: jsPsychPipe,
    action: "save",
    experiment_id: DATA_PIPE_EXPERIMENT_ID,
    filename: filename,
    data_string: buildCSV,
    on_finish: function(data) {
      // The DataPipe plugin never throws on a rejected upload, so inspect
      // the server response and fall back to a local download if it failed.
      console.log(`[DataPipe] save response for ${filename}:`, JSON.stringify(data));
      const msg = String((data && (data.message || data.error || data.result)) || "").toLowerCase();
      const looksOk =
        data &&
        !data.error &&
        data.success !== false &&
        (data.message !== undefined || data.result !== undefined) &&
        !/error|fail|not accepting|exceed|invalid|denied|missing/.test(msg);
      if (!looksOk) {
        console.error(`[DataPipe] upload did NOT succeed for ${filename} — downloading a local backup instead.`);
        data.datapipe_failed = true;
        try {
          downloadCSVBackup(`BACKUP_${filename}`, buildCSV());
        } catch (e) {
          console.error(`[DataPipe] local backup also failed for ${filename}:`, e);
        }
      }
    },
  });

  timeline.push({
    timeline: [
      {
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `<div class="instructions-block"><p>We could not upload your data automatically. A copy has been saved to this computer's downloads folder. Please let the researcher know.</p></div>`,
        choices: "NO_KEYS",
        trial_duration: 5000,
      },
    ],
    conditional_function: function() {
      const last = jsPsych.data.get().last(1).trials[0];
      return Boolean(last && last.datapipe_failed);
    },
  });
}

// ---------------------------------------------------------------------------
// Induction task — training (the 24 drawings, cycled through
// TRAINING_BLOCKS times, with one-back attention checks), then the test
// phase (prediction and memory questions, interleaved).
// ---------------------------------------------------------------------------

function readCSV(fileName) {
  return new Promise(function(resolve) {
    Papa.parse(fileName, {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: function(results) {
        resolve(results.data);
      }
    });
  });
}

// opt1, opt2, ... — however many response options this test trial has
// (5 colors, 4 shapes or 3 kids; unused columns are blank).
function getOptionNumbers(row) {
  return Object.keys(row)
    .filter(function(key) { return /^opt\d+$/.test(key) && row[key]; })
    .map(function(key) { return Number(key.slice(3)); })
    .sort(function(a, b) { return a - b; });
}

// Image files, from the stimulus file numbers (shape 13, color 5) and
// shape_name in the trial lists. Drawings are the traced SVGs: filled
// (all_shapes/high_shape13_high_color5) or the outline alone
// (shape_outlines/high_shape13).
const IMAGE_DIR = `images/${CONDITION}`;
const FILE_PREFIX = CONDITION.split("_")[0];
function swatchImage(color) { return `${IMAGE_DIR}/colors/${FILE_PREFIX}_color${color}.png`; }
function outlineImage(shape) { return `${IMAGE_DIR}/shape_outlines/${FILE_PREFIX}_shape${shape}.svg`; }
function drawingImage(row) {
  return `${IMAGE_DIR}/${row.color ? "all_shapes" : "shape_outlines"}/${row.shape_name}.svg`;
}

// Role code (S1-S4, C1-C5) -> file number, from the training drawings,
// which use every role.
function roleNumbers(training) {
  const numbers = {};
  training.forEach(function(row) {
    numbers[row.shape_role] = row.shape;
    numbers[row.color_role] = row.color;
  });
  return numbers;
}

// A choice option: its role code, the stimulus it stands for (file number,
// or the kid's name), and the image on its button.
function makeOption(responseType, code, numbers) {
  if (responseType === "color") return { code: code, id: numbers[code], image: swatchImage(numbers[code]) };
  if (responseType === "shape") return { code: code, id: numbers[code], image: outlineImage(numbers[code]) };
  return { code: code, id: code, image: "" };
}

function testOptions(row, numbers) {
  return getOptionNumbers(row).map(function(i) {
    return Object.assign(makeOption(row.response_type, row[`opt${i}`], numbers), {
      key: row[`key_opt${i}`],
      strategy: row[`strategy_opt${i}`],
    });
  });
}

// The answer options for one-back checks, built from the training rows:
// every kid, every color (swatch) and every shape (outline) in the design.
function designOptions(training) {
  const numbers = roleNumbers(training);
  function unique(type, values) {
    return [...new Set(values)].sort().map(function(code) { return makeOption(type, code, numbers); });
  }
  return {
    kid: unique("kid", training.map(function(row) { return row.kid; })),
    color: unique("color", training.map(function(row) { return row.color_role; })),
    shape: unique("shape", training.map(function(row) { return row.shape_role; })),
  };
}

// Fixed tilt for a drawing, using the advisor's demo formula: t is the
// drawing's token number plus the length of the kid's name for training
// drawings, and TEST_FIGURE_TOKEN for test figures, giving a rotation from
// -8 to 8 degrees. Every participant sees the same tilt on the same drawing.
// The demo's size change (scale 0.88-1.09) is left out: it made drawings of
// the same shape look like different sizes.
function drawingTilt(t) {
  return { rotation: ((t * 37) % 17) - 8, scale: 1 };
}

function trainingTilt(row) {
  return drawingTilt(Number(row.token.slice(1)) + row.kid.length);
}

function drawingHTML(src, jitter) {
  return `<img class="drawing" src="${src}" style="transform: rotate(${jitter.rotation}deg) scale(${jitter.scale});">`;
}

function listNames(names) {
  return names.length > 1
    ? `${names.slice(0, -1).join(", ")}${names.length > 2 ? "," : ""} and ${names[names.length - 1]}`
    : names.join("");
}

// A trial answered by clicking one of `options` ({ code, id, image, key }),
// shown in an order shuffled independently per trial: color swatches, shape
// outlines, or kid names, depending on responseType.
function buildChoiceTrial(stimulus, responseType, options, correctCode, data) {
  const shuffled = jsPsych.randomization.shuffle(options);
  return {
    type: jsPsychHtmlButtonResponse,
    stimulus: stimulus,
    choices: shuffled.map(function(option) { return responseType === "kid" ? option.id : option.image; }),
    button_html: function(choice) {
      if (responseType === "kid") {
        return `<button class="jspsych-btn name-btn">${choice}</button>`;
      }
      const imgClass = responseType === "color" ? "swatch-img" : "shape-option-img";
      return `<button class="jspsych-btn option-btn"><img class="${imgClass}" src="${choice}"></button>`;
    },
    button_layout: "grid",
    grid_rows: 1,
    grid_columns: shuffled.length,
    data: Object.assign({}, data, {
      response_type: responseType,
      option_order: shuffled.map(function(option) { return option.code; }).join(";"),
      correct_answer: correctCode || "",
    }),
    on_finish: function(d) {
      const selected = shuffled[d.response];
      d.response_position = d.response + 1;
      d.response_code = selected.code;
      d.response_id = selected.id;
      d.strategy = selected.strategy || "";
      d.is_correct = correctCode ? selected.code === correctCode : "";
    },
  };
}

function buildTrainingTrial(row, trainingBlock, trialNum) {
  const jitter = trainingTilt(row);
  return {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
      <div class="page drawing-page">
        ${drawingHTML(drawingImage(row), jitter)}
        <p class="drawing-caption"><b>${row.kid}</b> drew this.</p>
      </div>
    `,
    choices: "NO_KEYS",
    trial_duration: TRAINING_DRAWING_MS,
    post_trial_gap: TRAINING_GAP_MS,
    data: Object.assign({}, row, {
      inductionsave: true,
      subjCode: participantId,
      phase: "training",
      training_block: trainingBlock,
      trial_num: trialNum,
      rotation: jitter.rotation,
      scale: jitter.scale,
    }),
  };
}

const ONE_BACK_QUESTIONS = {
  kid: "Who drew the last drawing?",
  color: "What color was the last drawing?",
  shape: "What shape was the last drawing?",
};

// The trial-list column holding each attention check's correct answer.
const ONE_BACK_ANSWER = { kid: "kid", color: "color_role", shape: "shape_role" };

// Attention check right after a training drawing, asking about that drawing.
function buildOneBackTrial(prevRow, checkType, options, trainingBlock, trialNum) {
  return buildChoiceTrial(
    `
      <div class="page drawing-page">
        <p class="drawing-caption">${ONE_BACK_QUESTIONS[checkType]}</p>
      </div>
    `,
    checkType,
    options[checkType],
    prevRow[ONE_BACK_ANSWER[checkType]],
    Object.assign({}, prevRow, {
      inductionsave: true,
      subjCode: participantId,
      phase: "training",
      attention_check_type: checkType,
      training_block: trainingBlock,
      trial_num: trialNum,
    })
  );
}

// Which drawings in a training block get a one-back check after them:
// `count` randomly chosen drawings, with check types taken in turn from
// typeOrder (so they're split as evenly as possible) and then shuffled.
function oneBackSchedule(nDrawings, count, typeOrder) {
  const checkTypes = jsPsych.randomization.shuffle(
    Array.from({ length: count }, function(_, i) { return typeOrder[i % typeOrder.length]; })
  );
  const positions = jsPsych.randomization.sampleWithoutReplacement([...Array(nDrawings).keys()], count);
  const schedule = {};
  positions.forEach(function(position, i) { schedule[position] = checkTypes[i]; });
  return schedule;
}

function buildTestTrial(row, numbers, trialNum) {
  const jitter = drawingTilt(TEST_FIGURE_TOKEN);
  // category_only trials name the kid but show only a blank space where
  // the drawing would be; most_frequent_shape trials show no drawing at all.
  let figure = "";
  if (row.shape_name) {
    figure = drawingHTML(drawingImage(row), jitter);
  } else if (row.test_type === "category_only") {
    figure = `<div class="hidden-shape"></div>`;
  }

  return buildChoiceTrial(
    `
      <div class="page drawing-page">
        ${row.prompt ? `<p class="drawing-caption">${row.prompt}</p>` : ""}
        ${figure}
        <p class="drawing-caption">${row.question}</p>
      </div>
    `,
    row.response_type,
    testOptions(row, numbers),
    row.correct_answer,
    Object.assign({}, row, {
      inductionsave: true,
      subjCode: participantId,
      phase: "test",
      trial_num: trialNum,
      rotation: row.shape_name ? jitter.rotation : "",
      scale: row.shape_name ? jitter.scale : "",
    })
  );
}

// The tidy induction CSV: one row per training drawing, attention check and
// test trial, recording what happened. Everything fixed by the design (the
// prompt, the options and their answer keys and strategy codes, image files)
// is in test_trials.csv / training_trials.csv, joined by `stimulus`.
function buildInductionCleanCSV() {
  const blank = function(v) { return v === undefined || v === null || v === "none" ? "" : v; };
  const rows = jsPsych.data.get().filter({ inductionsave: true }).trials.map(function(t, i) {
    return {
      subjCode: t.subjCode,
      random_seed: t.random_seed,
      color_version: t.color_version,
      questionnaire_order: t.questionnaire_order,
      // trial_type is required for OSF to accept the data (same fix as FIT/IRQ)
      trial_type: t.attention_check_type ? "attention_check" : t.phase,
      training_block: blank(t.training_block),
      trial_num: t.trial_num,
      trial_index: i + 1,
      time_elapsed: blank(t.time_elapsed),
      stimulus: t.stimulus,
      trial_id: t.phase === "test" ? t.id : "",
      test_type: blank(t.test_type),
      trial_group: blank(t.trial_group),
      attention_check_type: blank(t.attention_check_type),
      kid: blank(t.kid),
      shape_role: blank(t.shape_role),
      shape: blank(t.shape),
      color_role: blank(t.color_role),
      color: blank(t.color),
      shape_name: blank(t.shape_name),
      rotation: blank(t.rotation),
      option_order: blank(t.option_order),
      // what was chosen, as its role code (or the kid's name) and as the
      // chosen color's or shape's file number (or the kid's name), like
      // shape_role/shape and color_role/color
      response_role: blank(t.response_code),
      response: blank(t.response_id),
      strategy: blank(t.strategy),
      correct_answer: blank(t.correct_answer),
      is_correct: t.is_correct === true ? 1 : t.is_correct === false ? 0 : "",
      rt: blank(t.rt),
    };
  });
  return Papa.unparse(rows);
}

// Overview of the study's three phases, with one example of a learning-phase
// drawing. The example uses a kid, shape and color that never appear in the
// real trials (INSTRUCTION_KID and the condition's instruction_examples
// images).
function buildInstructions(kids, exampleDrawing) {
  const introPages = {
    type: jsPsychInstructions,
    pages: [
      `
        <div class="instructions-block">
          <h2>Welcome</h2>
          <p>In this study, you will look at drawings made by three kids. Each drawing is a simple shape colored in with one color.</p>
          <p><strong>Your job is to learn which drawings belong to which kid.</strong></p>
          <p>Click "Next" to continue.</p>
        </div>
      `,
      `
        <div class="instructions-block">
          <h3>The study has three main parts:</h3>
          <p><b>1. Learning phase.</b> You will view a series of differently colored shapes along with a name. These represent drawings made by different children. Your goal is to learn which drawings are drawn by which child. <strong>Pay close attention.</strong> Every once in a while you will be asked about the shape, color, or name that goes with the drawing you just saw. There will be several short breaks along the way.</p>
          <p><b>2. Question phase.</b> You will answer additional questions about the drawings that help us understand what you've learned in the learning phase.</p>
          <p><b>3. Questionnaire phase.</b> You will fill out a few short questionnaires. When you finish these, the study is complete.</p>
          <p>Click "Next" to continue.</p>
        </div>
      `,
      `
        <div class="instructions-block">
          <h2>Learning Phase</h2>
          <p>In the learning phase, each drawing will look something like this:</p>
          ${drawingHTML(exampleDrawing, { rotation: 0, scale: 1 })}
          <p class="drawing-caption"><b>${INSTRUCTION_KID}</b> drew this.</p>
          <p>Your job is to watch and see who draws what! Sometimes you might be asked a surprise question about the drawing you just saw.</p>
          <p>Each drawing is only on the screen for a few seconds, so <b>pay close attention</b>.</p>
          <p>Click "Next" to continue.</p>
        </div>
      `,
    ],
    show_clickable_nav: true,
    key_forward: "ArrowRight",
    key_backward: "ArrowLeft",
    data: { screen: "induction_instructions" },
  };

  // Researcher gate: participants can't advance past this page on their own.
  // Only the researcher's "q" key moves on (not shown to participants).
  const closingPage = {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
      <div class="instructions-block">
        <h2>Let the researcher know you are ready to begin</h2>
        <p>Pay close attention and learn who draws what!</p>
      </div>
    `,
    choices: ["q"],
    data: { screen: "induction_instructions" },
  };

  const startPage = {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
      <div class="instructions-block">
        <p>Wait until the experimenter is out of the room.</p>
        <p>Press any key to begin the learning phase.</p>
      </div>
    `,
    choices: "ALL_KEYS",
    data: { screen: "induction_start" },
  };

  return [introPages, closingPage, startPage];
}

// trainingBlocks: one shuffled array of training rows per training block.
// checksPerBlock: one-back checks in each training block.
// test: the shuffled test rows.
// design: all 24 training drawings (in demo mode the blocks show only some,
//   but the answer options and role numbers come from the full design).
// exampleDrawing: this condition's instructions example drawing.
function buildInductionTimeline(trainingBlocks, checksPerBlock, test, design, exampleDrawing) {
  const timeline = [];
  const allTraining = trainingBlocks.flat();
  const options = designOptions(design);
  const kids = options.kid.map(function(option) { return option.id; });

  const numbers = roleNumbers(design);
  const images = [exampleDrawing];
  allTraining.forEach(function(row) { images.push(drawingImage(row)); });
  Object.values(options).flat().forEach(function(option) { if (option.image) images.push(option.image); });
  test.forEach(function(row) {
    if (row.shape_name) images.push(drawingImage(row));
    testOptions(row, numbers).forEach(function(option) { if (option.image) images.push(option.image); });
  });
  timeline.push({
    type: jsPsychPreload,
    images: [...new Set(images)],
  });

  timeline.push(...buildInstructions(kids, exampleDrawing));

  // trial_num is the presentation order within each training block, or
  // within the test phase; id stays the trial list's ID for that row.
  // Rotating the type order each block changes which type gets one fewer
  // check when checksPerBlock isn't a multiple of 3.
  const typeOrder = jsPsych.randomization.shuffle(Object.keys(ONE_BACK_QUESTIONS));
  trainingBlocks.forEach(function(block, b) {
    const shift = b % typeOrder.length;
    const blockTypeOrder = typeOrder.slice(shift).concat(typeOrder.slice(0, shift));
    const schedule = oneBackSchedule(block.length, checksPerBlock, blockTypeOrder);
    block.forEach(function(row, i) {
      timeline.push(buildTrainingTrial(row, b + 1, i + 1));
      if (schedule[i]) {
        timeline.push(buildOneBackTrial(row, schedule[i], options, b + 1, i + 1));
      }
    });
    if (b < trainingBlocks.length - 1) {
      timeline.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `
          <div class="instructions-block">
            <h2>Take a break!</h2>
            <p>Rest your eyes and stretch if needed.</p>
            <p>Press any key when you're ready to keep going.</p>
          </div>
        `,
        data: { screen: "training_break", training_block: b + 1 },
      });
    }
  });

  timeline.push({
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
      <div class="instructions-block">
        <h2>Question Phase</h2>
        <p>Great job! You are done with the learning phase.</p>
        <p>Next is the <b>question phase</b>. You will answer various questions about the drawings.</p>
        <p>Sometimes you will be asked to <strong>predict</strong> something about a <strong>new</strong> drawing and sometimes you will be asked to <strong>remember</strong> something about drawings you have already seen.</p>
        <p>Take as much time as you need to answer each question.</p>
        <p>Press any key to start the question phase.</p>
      </div>
    `,
    data: { screen: "test_intro" },
  });

  test.forEach(function(row, i) {
    timeline.push(buildTestTrial(row, numbers, i + 1));
  });

  pushSaveTimeline(timeline, sessionFilename("induction"), function() {
    return buildInductionCleanCSV();
  });

  return timeline;
}

// ---------------------------------------------------------------------------
// Setup screen: subject code, random seed, color version, demo mode,
// questionnaire order. Any of these can be pre-filled via URL params
// (?subjCode=..., ?seed=..., ?colorVersion=1-5, ?demo=true,
// ?questionnaireOrder=0|1, where 0 = IRQ then FIT and 1 = FIT then IRQ) but
// the researcher/participant still has to confirm by pressing "Start".
// ---------------------------------------------------------------------------

function promptForParameters(urlParams) {
  return new Promise(function(resolve) {
    const prefillSubj = urlParams.get("subjCode") || urlParams.get("subject") || urlParams.get("subj") || "";
    const prefillDemo = /^(1|true|yes)$/i.test((urlParams.get("demo") || "").trim());
    const prefillSeed = (urlParams.get("seed") || "").trim();
    const orderParam = (urlParams.get("questionnaireOrder") || "").trim().toLowerCase();
    const prefillOrder = { "0": "irq_first", "irq_first": "irq_first", "1": "fit_first", "fit_first": "fit_first" }[orderParam] || "";
    const versionParam = (urlParams.get("colorVersion") || "").trim();
    const versions = Array.from({ length: COLOR_VERSIONS }, function(_, i) { return String(i + 1); });

    const overlay = document.createElement("div");
    overlay.id = "param-overlay";
    overlay.innerHTML = `
      <form class="param-box" autocomplete="off">
        <h2>Experiment setup</h2>
        <label>Subject code
          <input type="text" name="subjCode" required>
        </label>
        <label>Random seed
          <input type="text" name="seed" required>
        </label>
        <label>Color version
          <select name="colorVersion" required>
            <option value="" disabled selected hidden></option>
            ${versions.map(function(v) { return `<option value="${v}">${v}</option>`; }).join("")}
          </select>
        </label>
        <label>Questionnaire order
          <select name="questionnaireOrder" required>
            <option value="" disabled selected hidden></option>
            <option value="irq_first">0: IRQ then FIT</option>
            <option value="fit_first">1: FIT then IRQ</option>
          </select>
        </label>
        <label class="param-check">
          <input type="checkbox" name="demo">
          Demo mode (short single-block induction run)
        </label>
        <div class="param-error"></div>
        <button type="submit">Start</button>
      </form>
    `;
    document.body.appendChild(overlay);

    const form = overlay.querySelector("form");
    const errorEl = overlay.querySelector(".param-error");
    form.subjCode.value = prefillSubj;
    form.seed.value = prefillSeed;
    form.demo.checked = prefillDemo;
    if (prefillOrder) form.questionnaireOrder.value = prefillOrder;
    if (versions.includes(versionParam)) form.colorVersion.value = versionParam;
    form.subjCode.focus();

    form.addEventListener("submit", function(event) {
      event.preventDefault();
      const subjCode = form.subjCode.value.trim();
      const seed = form.seed.value.trim();
      const colorVersion = form.colorVersion.value;
      const questionnaireOrder = form.questionnaireOrder.value;
      if (!subjCode || !seed || !colorVersion || !questionnaireOrder) {
        errorEl.textContent = "Please fill in all fields.";
        (!subjCode ? form.subjCode : !seed ? form.seed : !colorVersion ? form.colorVersion : form.questionnaireOrder).focus();
        return;
      }

      overlay.remove();
      resolve({
        subjectID: subjCode,
        seed: seed,
        colorVersion: colorVersion, // "1" to "5"
        demoMode: form.demo.checked,
        questionnaireOrder: questionnaireOrder, // "fit_first" | "irq_first"
      });
    });
  });
}

const jsPsych = initJsPsych({
  on_finish: function() {
    const qualtricsConfigured = QUALTRICS_URL !== "REPLACE_WITH_YOUR_QUALTRICS_LINK";
    if (qualtricsConfigured) {
      const redirectURL = new URL(QUALTRICS_URL);
      redirectURL.searchParams.set("subjCode", participantId);
      window.location = redirectURL.toString();
    }
  }
});

async function runExperiment() {
  const urlParams = new URLSearchParams(window.location.search);
  const { subjectID, seed, colorVersion, demoMode, questionnaireOrder } = await promptForParameters(urlParams);

  // Seed every jsPsych.randomization call and Math.random (trial order,
  // option order, drawing jitter, questionnaire item order) so
  // the same seed reproduces the same session.
  jsPsych.randomization.setSeed(seed);

  participantId = subjectID;
  demoModeActive = demoMode;
  jsPsych.data.addProperties({
    participant_id: participantId,
    random_seed: seed,
    condition: CONDITION,
    color_version: colorVersion,
    questionnaire_order: questionnaireOrder,
  });

  if (demoMode) {
    const banner = document.createElement("div");
    banner.id = "demo-mode-banner";
    banner.textContent = `DEMO MODE — ${DEMO_TRAINING_COUNT + DEMO_CHECKS} learning trials, ${DEMO_TEST_COUNT} test trials`;
    document.body.appendChild(banner);
  }

  const [trainingList, testList] = await Promise.all([
    readCSV(TRAINING_CSV),
    readCSV(TEST_CSV),
  ]);

  // This participant's color version: the same design, with its own
  // mapping of real colors to color roles.
  const inVersion = function(row) { return row.condition === CONDITION && row.color_version === colorVersion; };
  const training = trainingList.filter(inVersion);
  let trainingBlocks = Array.from({ length: TRAINING_BLOCKS }, function() {
    return jsPsych.randomization.shuffle(training);
  });
  let checksPerBlock = ONE_BACK_CHECKS_PER_BLOCK;
  let test = jsPsych.randomization.shuffle(testList.filter(inVersion));
  if (demoMode) {
    trainingBlocks = [trainingBlocks[0].slice(0, DEMO_TRAINING_COUNT)];
    checksPerBlock = DEMO_CHECKS;
    // One trial of every test type first, then fill up to DEMO_TEST_COUNT
    // from the rest; reshuffled so the types don't come in a fixed order.
    const firstOfEachType = [...new Set(test.map(function(row) { return row.test_type; }))].map(function(type) {
      return test.find(function(row) { return row.test_type === type; });
    });
    const rest = test.filter(function(row) { return !firstOfEachType.includes(row); });
    test = jsPsych.randomization.shuffle(
      firstOfEachType.concat(rest.slice(0, Math.max(0, DEMO_TEST_COUNT - firstOfEachType.length)))
    );
  }

  const timeline = [];
  timeline.push(...buildInductionTimeline(
    trainingBlocks, checksPerBlock, test, training,
    `images/${CONDITION}/instruction_examples/shapeA_ex1.svg`
  ));

  timeline.push({
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
      <div class="instructions-block">
        <h2>Questionnaire Phase</h2>
        <p>Great job! You are done with the question phase.</p>
        <p>Next is the <b>questionnaire phase</b>. You will fill out a few short questionnaires and be redirected to a final one in another window. When you finish the last one, the study is complete.</p>
        <p>Press any key to start the questionnaire phase.</p>
      </div>
    `,
    data: { screen: "questionnaire_intro" },
  });

  // FIT and IRQ questionnaires: always run in full, whether or not demo mode
  // is on, each saving to its own "<subjCode>_FIT.csv" / "<subjCode>_IRQ.csv"
  // file. Their order is set at the setup screen (manually counterbalanced
  // across participants, not randomized by the code).
  const fitTimeline = buildFITTimeline();
  const irqTimeline = buildIRQTimeline();
  if (questionnaireOrder === "irq_first") {
    timeline.push(...irqTimeline, ...fitTimeline);
  } else {
    timeline.push(...fitTimeline, ...irqTimeline);
  }

  // End page.
  const qualtricsConfigured = QUALTRICS_URL !== "REPLACE_WITH_YOUR_QUALTRICS_LINK";
  timeline.push({
    type: jsPsychHtmlKeyboardResponse,
    stimulus: qualtricsConfigured
      ? `<div class="page"><p>You are finished. Thank you! You will now be redirected to a final survey.</p></div>`
      : `<div class="page"><p>You are finished. Thank you.</p></div>`,
    choices: "NO_KEYS",
    trial_duration: qualtricsConfigured ? 2000 : null,
  });

  jsPsych.run(timeline);
}

/*
  PILOT 2: KIDS' DRAWINGS BLOCK VERSION

  What this file does:
  1. Shows a setup screen asking for the subject code, the random seed,
     the nameability condition (high or low; between-subject), whether to
     run in demo mode (a short single-block run), and the order of the two
     questionnaires at the end (0: IRQ then FIT, or 1: FIT then IRQ) — any
     of these can also be pre-filled via URL params.
  2. Reads training_trials.csv and test_trials.csv (made by
     generate_design.py) and picks one design version of this participant's
     condition. All randomization (design version, training and test order,
     one-back check placement, answer option order, drawing jitter,
     questionnaire item order) is driven by the seed entered at setup, so
     the same seed reproduces the same session.
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

const CONDITIONS = {
  high_nameability: "High nameability",
  low_nameability: "Low nameability",
};

// Training cycles through all 24 drawings this many times, in a fresh
// random order each time.
const TRAINING_BLOCKS = 4;

// How long each training drawing stays on screen, and the blank gap after it.
const TRAINING_DRAWING_MS = 2500;
const TRAINING_GAP_MS = 500;

// Share of training drawings followed by a one-back attention check (who
// drew / what color / what shape was the last drawing), split evenly
// across the three check types within each training block.
const ONE_BACK_PROPORTION = 0.25;

// Range of the random rotation/scale applied to every drawing shown. Scale
// is fixed at 1 (no size change): size variation made drawings of the same
// shape look like different sizes.
const JITTER_MAX_ROTATION_DEG = 8;
const JITTER_MIN_SCALE = 1;
const JITTER_MAX_SCALE = 1;

// From your pipe at https://pipe.jspsych.org — every participant's data
// gets uploaded to whatever OSF project that pipe is linked to. The same
// pipe is used for all three saved files (induction/FIT/IRQ); DataPipe
// just uploads whatever filename each save trial gives it. Pilot 2 needs
// its own pipe (pilot 1 used "xvMyuhu7p8BK"); until one is filled in, each
// section saves a local download instead.
const DATA_PIPE_EXPERIMENT_ID = "REPLACE_WITH_YOUR_DATAPIPE_ID";

// Fill this in once you have the Qualtrics link for the final survey. Until
// then, the experiment just ends with a thank-you message instead of
// redirecting.
const QUALTRICS_URL = "https://uwmadison.co1.qualtrics.com/jfe/form/SV_24r43gqIML2igfk";

// ?demo=true (or the setup screen's "Demo mode" checkbox) runs one training
// block cut down to this many drawings, and this many test trials, so the
// full pipeline — including every DataPipe upload and both questionnaires —
// can be tested fast. The questionnaires always run in full regardless.
const DEMO_TRAINING_COUNT = 8;
const DEMO_TEST_COUNT = 4;

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

function testOptions(row) {
  return getOptionNumbers(row).map(function(i) {
    return {
      code: row[`opt${i}`],
      id: row[`opt${i}_id`],
      image: row[`opt${i}_image`],
      key: row[`key_opt${i}`],
    };
  });
}

// The answer options for one-back checks, built from the training rows:
// every kid, every color (swatch) and every shape (outline) in the design.
function designOptions(training) {
  function unique(codeKey, make) {
    return [...new Map(training.map(function(row) { return [row[codeKey], make(row)]; })).values()]
      .sort(function(a, b) { return a.code.localeCompare(b.code); });
  }
  return {
    kid: [...new Set(training.map(function(row) { return row.kid; }))].map(function(kid) {
      return { code: kid, id: kid, image: "" };
    }),
    color: unique("color", function(row) { return { code: row.color, id: row.color_id, image: row.color_image }; }),
    shape: unique("shape", function(row) { return { code: row.shape, id: row.shape_id, image: row.shape_image }; }),
  };
}

// Small random rotation/scale for every drawing shown, so repeated drawings
// of a shape aren't pixel-identical (same ranges as the advisor's demo).
// Math.random is seeded by jsPsych.randomization.setSeed, so the same seed
// reproduces the same jitter.
function randomJitter() {
  return {
    rotation: Math.round((Math.random() * 2 - 1) * JITTER_MAX_ROTATION_DEG),
    scale: Number((JITTER_MIN_SCALE + Math.random() * (JITTER_MAX_SCALE - JITTER_MIN_SCALE)).toFixed(3)),
  };
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
      d.response_key = selected.key || "";
      d.is_correct = correctCode ? selected.code === correctCode : "";
    },
  };
}

function buildTrainingTrial(row, trainingBlock, trialNum) {
  const jitter = randomJitter();
  return {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
      <div class="page drawing-page">
        ${drawingHTML(row.image, jitter)}
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
    prevRow[checkType],
    Object.assign({}, prevRow, {
      inductionsave: true,
      subjCode: participantId,
      phase: "one_back",
      one_back_type: checkType,
      training_block: trainingBlock,
      trial_num: trialNum,
    })
  );
}

// Which drawings in a training block get a one-back check after them:
// ONE_BACK_PROPORTION of them, split evenly across the three check types.
function oneBackSchedule(nDrawings) {
  const count = Math.round(nDrawings * ONE_BACK_PROPORTION);
  const types = Object.keys(ONE_BACK_QUESTIONS);
  const checkTypes = jsPsych.randomization.shuffle(
    Array.from({ length: count }, function(_, i) { return types[i % types.length]; })
  );
  const positions = jsPsych.randomization.sampleWithoutReplacement([...Array(nDrawings).keys()], count);
  const schedule = {};
  positions.forEach(function(position, i) { schedule[position] = checkTypes[i]; });
  return schedule;
}

function buildTestTrial(row, trialNum) {
  const jitter = randomJitter();
  // category_only trials name the kid but don't show a shape;
  // most_frequent_shape trials show no drawing at all.
  let figure = "";
  if (row.figure_image) {
    figure = drawingHTML(row.figure_image, jitter);
  } else if (row.test_type === "category_only") {
    figure = `<div class="hidden-shape">Shape not shown</div>`;
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
    testOptions(row),
    row.correct_answer,
    Object.assign({}, row, {
      inductionsave: true,
      subjCode: participantId,
      phase: "test",
      trial_num: trialNum,
      rotation: row.figure_image ? jitter.rotation : "",
      scale: row.figure_image ? jitter.scale : "",
    })
  );
}

// Fixed column order for the tidy induction CSV: one row per training
// drawing, one-back check and test trial, with every column from both trial
// lists plus what happened on the trial. Columns that don't apply to a
// row's phase are left blank.
function inductionCSVColumns(trainingRows, testRows) {
  return [...new Set([
    "subjCode", "random_seed", "trial_type", "phase", "training_block", "trial_num", "one_back_type",
    ...Object.keys(trainingRows[0] || {}),
    ...Object.keys(testRows[0] || {}),
    "rotation", "scale", "response_type", "option_order",
    "response_position", "response_code", "response_id", "response_key",
    "correct_answer", "is_correct", "rt",
  ])];
}

function buildInductionCleanCSV(columns) {
  const rows = jsPsych.data.get().filter({ inductionsave: true }).trials.map(function(t) {
    const row = {};
    columns.forEach(function(c) { row[c] = t[c] !== undefined ? t[c] : ""; });
    // trial_type is required for OSF to accept the data (same fix as FIT/IRQ).
    row.trial_type = "induction";
    return row;
  });
  return Papa.unparse(rows);
}

function buildInstructions(kids) {
  const introPages = {
    type: jsPsychInstructions,
    pages: [
      `
        <div class="instructions-block">
          <h2>Welcome</h2>
          <p>In this experiment, you will see drawings made by three kids: ${listNames(kids)}. Each drawing is a simple shape colored in with one color.</p>
          <p>Click "Next" to continue.</p>
        </div>
      `,
      `
        <div class="instructions-block">
          <p>First, you will see the kids' drawings, one at a time, along with the name of the kid who drew it.</p>
          <p>Pay close attention to each drawing. Every so often, you will be asked a quick question about the drawing you just saw.</p>
          <p>Click "Next" to continue.</p>
        </div>
      `,
      `
        <div class="instructions-block">
          <p>After that, you will answer questions about the kids' drawings.</p>
          <p>Some questions are about drawings you saw. Others are about new drawings the kids made, where you will choose the color you think the new drawing is.</p>
          <p>Sometimes you won't be shown the shape, or won't be told who made the drawing. Just make your best guess.</p>
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
        <h2>Ready to begin</h2>
        <p>Take as much time as you need to answer each question.</p>
      </div>
    `,
    choices: ["q"],
    data: { screen: "induction_instructions" },
  };

  const startPage = {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
      <div class="instructions-block">
        <p>Press any key to begin the study.</p>
      </div>
    `,
    choices: "ALL_KEYS",
    data: { screen: "induction_start" },
  };

  return [introPages, closingPage, startPage];
}

// trainingBlocks: one shuffled array of training rows per training block.
// test: the shuffled test rows.
function buildInductionTimeline(trainingBlocks, test, columns) {
  const timeline = [];
  const allTraining = trainingBlocks.flat();
  const options = designOptions(allTraining);
  const kids = options.kid.map(function(option) { return option.id; });

  const images = [];
  allTraining.forEach(function(row) { images.push(row.image, row.color_image, row.shape_image); });
  test.forEach(function(row) {
    if (row.figure_image) images.push(row.figure_image);
    testOptions(row).forEach(function(option) { if (option.image) images.push(option.image); });
  });
  timeline.push({
    type: jsPsychPreload,
    images: [...new Set(images)],
  });

  timeline.push(...buildInstructions(kids));

  // trial_num is the presentation order within each training block, or
  // within the test phase; id stays the trial list's ID for that row.
  trainingBlocks.forEach(function(block, b) {
    const schedule = oneBackSchedule(block.length);
    block.forEach(function(row, i) {
      timeline.push(buildTrainingTrial(row, b + 1, i + 1));
      if (schedule[i]) {
        timeline.push(buildOneBackTrial(row, schedule[i], options, b + 1, i + 1));
      }
    });
  });

  timeline.push({
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
      <div class="instructions-block">
        <p>Now you will answer some questions about the drawings by ${listNames(kids)}.</p>
        <p>Press any key to start.</p>
      </div>
    `,
    data: { screen: "test_intro" },
  });

  test.forEach(function(row, i) {
    timeline.push(buildTestTrial(row, i + 1));
  });

  pushSaveTimeline(timeline, sessionFilename("induction"), function() {
    return buildInductionCleanCSV(columns);
  });

  return timeline;
}

// ---------------------------------------------------------------------------
// Setup screen: subject code, random seed, condition, demo mode,
// questionnaire order. Any of these can be pre-filled via URL params
// (?subjCode=..., ?seed=..., ?condition=high|low, ?demo=true,
// ?questionnaireOrder=0|1, where 0 = IRQ then FIT and 1 = FIT then IRQ) but
// the researcher/participant still has to confirm by pressing "Start".
// ---------------------------------------------------------------------------

function promptForParameters(urlParams) {
  return new Promise(function(resolve) {
    const prefillSubj = urlParams.get("subjCode") || urlParams.get("subject") || urlParams.get("subj") || "";
    const prefillDemo = /^(1|true|yes)$/i.test((urlParams.get("demo") || "").trim());
    const prefillSeed = (urlParams.get("seed") || "").trim();
    const conditionParam = (urlParams.get("condition") || "").trim().toLowerCase();
    const prefillCondition = { "high": "high_nameability", "high_nameability": "high_nameability", "low": "low_nameability", "low_nameability": "low_nameability" }[conditionParam] || "";
    const orderParam = (urlParams.get("questionnaireOrder") || "").trim().toLowerCase();
    const prefillOrder = { "0": "irq_first", "irq_first": "irq_first", "1": "fit_first", "fit_first": "fit_first" }[orderParam] || "";

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
        <label>Condition
          <select name="condition" required>
            <option value="" disabled selected hidden></option>
            ${Object.entries(CONDITIONS).map(function([value, label]) {
              return `<option value="${value}">${label}</option>`;
            }).join("")}
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
    if (prefillCondition) form.condition.value = prefillCondition;
    if (prefillOrder) form.questionnaireOrder.value = prefillOrder;
    form.subjCode.focus();

    form.addEventListener("submit", function(event) {
      event.preventDefault();
      const subjCode = form.subjCode.value.trim();
      const seed = form.seed.value.trim();
      const condition = form.condition.value;
      const questionnaireOrder = form.questionnaireOrder.value;
      if (!subjCode || !seed || !condition || !questionnaireOrder) {
        errorEl.textContent = "Please fill in all fields.";
        (!subjCode ? form.subjCode : !seed ? form.seed : !condition ? form.condition : form.questionnaireOrder).focus();
        return;
      }

      overlay.remove();
      resolve({
        subjectID: subjCode,
        seed: seed,
        condition: condition, // "high_nameability" | "low_nameability"
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
  const { subjectID, seed, condition, demoMode, questionnaireOrder } = await promptForParameters(urlParams);

  // Seed every jsPsych.randomization call and Math.random (design version,
  // trial order, option order, drawing jitter, questionnaire item order) so
  // the same seed reproduces the same session.
  jsPsych.randomization.setSeed(seed);

  participantId = subjectID;
  demoModeActive = demoMode;
  jsPsych.data.addProperties({
    participant_id: participantId,
    random_seed: seed,
    condition: condition,
    questionnaire_order: questionnaireOrder,
  });

  if (demoMode) {
    const banner = document.createElement("div");
    banner.id = "demo-mode-banner";
    banner.textContent = `DEMO MODE — ${DEMO_TRAINING_COUNT} training drawings, ${DEMO_TEST_COUNT} test trials`;
    document.body.appendChild(banner);
  }

  const [trainingList, testList] = await Promise.all([
    readCSV(TRAINING_CSV),
    readCSV(TEST_CSV),
  ]);

  // One design version of this condition (which shapes/colors fill the
  // demo's roles), picked by the setup seed.
  const designs = [...new Set(trainingList
    .filter(function(row) { return row.condition === condition; })
    .map(function(row) { return row.design; }))];
  const design = jsPsych.randomization.sampleWithoutReplacement(designs, 1)[0];
  jsPsych.data.addProperties({ design: design });

  const training = trainingList.filter(function(row) { return row.design === design; });
  let trainingBlocks = Array.from({ length: TRAINING_BLOCKS }, function() {
    return jsPsych.randomization.shuffle(training);
  });
  let test = jsPsych.randomization.shuffle(testList.filter(function(row) { return row.design === design; }));
  if (demoMode) {
    trainingBlocks = [trainingBlocks[0].slice(0, DEMO_TRAINING_COUNT)];
    test = test.slice(0, DEMO_TEST_COUNT);
  }

  const timeline = [];
  timeline.push(...buildInductionTimeline(trainingBlocks, test, inductionCSVColumns(trainingList, testList)));

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

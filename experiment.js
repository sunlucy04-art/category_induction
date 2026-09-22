/*
  SIMPLE EXPERIMENT PROPORTION VERSION

  What this file does:
  1. Shows a setup screen asking for the subject code, whether to run in
     demo mode (2 induction trials instead of the full set), and the order
     of the two questionnaires at the end (FIT then IRQ, or IRQ then FIT) —
     any of these can also be pre-filled via URL params.
  2. Reads the master trial list (one row per trial; every image filename
     it needs is already spelled out on that row, including its 8 evidence
     items) and shuffles the trial order (a fresh, independent order per
     participant/page load).
  3. Runs the induction task: on every trial, shows that painter's evidence
     items, then the new painting's outline, then asks the participant to
     choose which gabor pattern completes it. Which side (left/right) each
     of the two choices (feature-feature vs category strategy) lands on is
     randomized independently for every trial.
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

const csvFile = "master_trial_list.csv";

// From your pipe at https://pipe.jspsych.org — every participant's data
// gets uploaded to whatever OSF project that pipe is linked to. The same
// pipe is used for all three saved files (induction/FIT/IRQ); DataPipe
// just uploads whatever filename each save trial gives it.
const DATA_PIPE_EXPERIMENT_ID = "NFFZ5L6ZlvsN";

// Fill this in once you have the Qualtrics link for the final survey. Until
// then, the experiment just ends with a thank-you message instead of
// redirecting.
const QUALTRICS_URL = "REPLACE_WITH_YOUR_QUALTRICS_LINK";

// ?demo=true (or the setup screen's "Demo mode" checkbox) runs only this
// many induction trials, so the full pipeline — including every DataPipe
// upload and both questionnaires — can be tested fast. The questionnaires
// always run in full regardless.
const DEMO_TRIAL_COUNT = 2;

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
// Induction task
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

// item1_name, item2_name, ... — however many there are (this is not
// hard-coded to 8, so it stays correct even if examples_per_category
// changes in generate_trials.py).
function getItemImageKeys(row) {
  return Object.keys(row)
    .filter(function(key) { return /^item\d+_name$/.test(key); })
    .sort(function(a, b) {
      return Number(a.match(/\d+/)[0]) - Number(b.match(/\d+/)[0]);
    });
}

function getItemImages(row) {
  return getItemImageKeys(row)
    .map(function(key) { return row[key]; })
    .filter(function(value) { return value; });
}

function createExampleBoard(row) {
  const imagesHTML = getItemImages(row)
    .map(function(image) {
      return `<img class="example-item" src="${image}">`;
    })
    .join("");

  return `
    <div class="example-board-title">${row.painter} has created the following paintings:</div>
    <div class="example-board">${imagesHTML}</div>
  `;
}

// Fixed column order for the tidy induction CSV — every column from the
// master trial list, plus the participant's actual choice.
function inductionCSVColumns(itemKeys) {
  return [
    "subjCode", "trial_id", "painter", "critical_shape",
    "category_dominant_gabor", "critical_shape_dominant_gabor",
    "target_probe_outline", "category_induction_gabor", "feature_feature_gabor",
    ...itemKeys,
    "left_option_image", "left_option_strategy",
    "right_option_image", "right_option_strategy",
    "participant_choice", "choice_strategy", "selected_side", "rt",
  ];
}

function buildInductionCleanCSV(itemKeys) {
  const columns = inductionCSVColumns(itemKeys);
  const rows = jsPsych.data.get().filter({ inductionsave: true }).trials.map(function(t) {
    const row = {};
    columns.forEach(function(c) { row[c] = t[c] !== undefined ? t[c] : ""; });
    return row;
  });
  return Papa.unparse(rows);
}

// Builds the multi-page, click-through instructions, illustrated with the
// real images from instructions_example.csv (one worked example, walked
// through piece by piece). Editing that CSV to point at a different trial
// changes the example without touching this code.
function buildIllustratedInstructions(exampleRow) {
  return {
    type: jsPsychInstructions,
    pages: [
      `
        <div class="instructions-block">
          <h2>Welcome</h2>
          <p>Welcome!</p>
          <p>In this experiment, you will explore paintings created by different painters.</p>
          <p>You will see examples of their previous artwork and will be asked to infer something about a brand new painting created by each painter.</p>
          <p>Click "Next" to see exactly what that will look like.</p>
        </div>
      `,
      `
        <div class="instructions-block">
          <p>Each painter has created many paintings in the past.</p>
          <p>At the start of each question, you will see a sample of one painter's previous paintings — for example:</p>
          ${createExampleBoard(exampleRow)}
          <p>These are only a small sample of that painter's work, and a different random sample is shown for every question.</p>
          <p>Click "Next" to continue.</p>
        </div>
      `,
      `
        <div class="instructions-block">
          <p>Next, you'll be told that the painter has created a brand new painting, and shown its outline — for example:</p>
          <p>Now <b>${exampleRow.painter}</b> has created a NEW painting:</p>
          <img class="new-painting" src="${exampleRow.target_probe_outline}">
          <p>The inside of this new painting is left blank — that's what you'll be asked to fill in.</p>
          <p>Click "Next" to continue.</p>
        </div>
      `,
      `
        <div class="instructions-block">
          <p>You will then choose which pattern you think best completes the painting, from two options like these:</p>
          <div style="display:flex; justify-content:center; gap:24px; margin:16px 0;">
            <img class="choice-img" src="${exampleRow.category_induction_gabor}">
            <img class="choice-img" src="${exampleRow.feature_feature_gabor}">
          </div>
          <p>Which option appears on the left or right changes randomly each time — just pick whichever pattern you think fits best.</p>
          <p>Click "Next" to continue.</p>
        </div>
      `,
      `
        <div class="instructions-block">
          <h2>Ready to begin</h2>
          <p>That's the whole task: look at a painter's previous paintings, see the outline of their newest painting, and choose the pattern you think fits best.</p>
          <p>Click "Next" to start.</p>
        </div>
      `,
    ],
    show_clickable_nav: true,
    key_forward: "ArrowRight",
    key_backward: "ArrowLeft",
    data: { screen: "induction_instructions" },
  };
}

function buildInductionTimeline(shuffledTrials, exampleRow) {
  const timeline = [];
  const itemKeys = shuffledTrials.length ? getItemImageKeys(shuffledTrials[0]) : [];

  // Preload every image referenced anywhere in the trial list, plus the
  // illustrated-instructions example (which may not otherwise appear in
  // this participant's shuffled trials).
  const images = [];
  shuffledTrials.forEach(function(row) {
    images.push(row.target_probe_outline);
    images.push(row.category_induction_gabor);
    images.push(row.feature_feature_gabor);
    getItemImages(row).forEach(function(image) { images.push(image); });
  });
  if (exampleRow) {
    images.push(exampleRow.target_probe_outline);
    images.push(exampleRow.category_induction_gabor);
    images.push(exampleRow.feature_feature_gabor);
    getItemImages(exampleRow).forEach(function(image) { images.push(image); });
  }

  timeline.push({
    type: jsPsychPreload,
    images: images
  });

  timeline.push(buildIllustratedInstructions(exampleRow));

  // Make one clickable trial from each row in the shuffled trial list.
  shuffledTrials.forEach(function(row) {
    // Which side (left/right) each strategy's image lands on is
    // randomized independently per trial.
    const options = jsPsych.randomization.shuffle([
      { image: row.category_induction_gabor, strategy: "category", gabor: row.category_dominant_gabor },
      { image: row.feature_feature_gabor, strategy: "feature-feature", gabor: row.critical_shape_dominant_gabor }
    ]);

    const choices = options.map(function(option) { return option.image; });

    timeline.push({
      type: jsPsychHtmlButtonResponse,

      stimulus: `
        <div class="page trial-page">
          ${createExampleBoard(row)}

          <p>Now <b>${row.painter}</b> has created a NEW painting:</p>
          <img class="new-painting" src="${row.target_probe_outline}">

          <p>What do you think the inside of this painting will look like?</p>
        </div>
      `,

      choices: choices,

      button_html: function(choice) {
        return `<button class="jspsych-btn"><img class="choice-img" src="${choice}"></button>`;
      },

      button_layout: "grid",
      grid_rows: 1,
      grid_columns: 2,

      data: Object.assign({}, row, {
        inductionsave: true,
        subjCode: participantId,
        left_option_image: options[0].image,
        left_option_strategy: options[0].strategy,
        right_option_image: options[1].image,
        right_option_strategy: options[1].strategy
      }),

      on_finish: function(data) {
        const selected = options[data.response];
        data.selected_side = data.response === 0 ? "left" : "right";
        data.participant_choice = selected.gabor;
        data.choice_strategy = selected.strategy;
      }
    });
  });

  pushSaveTimeline(timeline, sessionFilename("induction"), function() {
    return buildInductionCleanCSV(itemKeys);
  });

  return timeline;
}

// ---------------------------------------------------------------------------
// Setup screen: subject code, demo mode, questionnaire order. Any of these
// can be pre-filled via URL params (?subjCode=..., ?demo=true,
// ?questionnaireOrder=fit_first|irq_first) but the researcher/participant
// still has to confirm by pressing "Start".
// ---------------------------------------------------------------------------

function promptForParameters(urlParams) {
  return new Promise(function(resolve) {
    const prefillSubj = urlParams.get("subjCode") || urlParams.get("subject") || urlParams.get("subj") || "";
    const prefillDemo = /^(1|true|yes)$/i.test((urlParams.get("demo") || "").trim());
    const prefillOrder = /^(fit_first|irq_first)$/i.test((urlParams.get("questionnaireOrder") || "").trim())
      ? urlParams.get("questionnaireOrder").trim().toLowerCase()
      : "";

    const overlay = document.createElement("div");
    overlay.id = "param-overlay";
    overlay.innerHTML = `
      <form class="param-box" autocomplete="off">
        <h2>Experiment setup</h2>
        <label>Subject code
          <input type="text" name="subjCode" required>
        </label>
        <label>Questionnaire order
          <select name="questionnaireOrder" required>
            <option value="" disabled selected hidden></option>
            <option value="fit_first">FIT then IRQ</option>
            <option value="irq_first">IRQ then FIT</option>
          </select>
        </label>
        <label class="param-check">
          <input type="checkbox" name="demo">
          Demo mode (short ${DEMO_TRIAL_COUNT}-trial induction run)
        </label>
        <div class="param-error"></div>
        <button type="submit">Start</button>
      </form>
    `;
    document.body.appendChild(overlay);

    const form = overlay.querySelector("form");
    const errorEl = overlay.querySelector(".param-error");
    form.subjCode.value = prefillSubj;
    form.demo.checked = prefillDemo;
    if (prefillOrder) form.questionnaireOrder.value = prefillOrder;
    form.subjCode.focus();

    form.addEventListener("submit", function(event) {
      event.preventDefault();
      const subjCode = form.subjCode.value.trim();
      const questionnaireOrder = form.questionnaireOrder.value;
      if (!subjCode || !questionnaireOrder) {
        errorEl.textContent = "Please fill in all fields.";
        (!subjCode ? form.subjCode : form.questionnaireOrder).focus();
        return;
      }

      overlay.remove();
      resolve({
        subjectID: subjCode,
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
  const { subjectID, demoMode, questionnaireOrder } = await promptForParameters(urlParams);

  participantId = subjectID;
  demoModeActive = demoMode;
  jsPsych.data.addProperties({
    participant_id: participantId,
    questionnaire_order: questionnaireOrder,
  });

  if (demoMode) {
    const banner = document.createElement("div");
    banner.id = "demo-mode-banner";
    banner.textContent = `DEMO MODE — ${DEMO_TRIAL_COUNT}-trial induction run`;
    document.body.appendChild(banner);
  }

  const [trialList, exampleRows] = await Promise.all([
    readCSV(csvFile),
    readCSV("instructions_example.csv"),
  ]);
  const exampleRow = exampleRows[0];

  // A fresh, independent trial order for this participant.
  let shuffledTrials = jsPsych.randomization.shuffle(trialList);
  if (demoMode) {
    shuffledTrials = shuffledTrials.slice(0, DEMO_TRIAL_COUNT);
  }

  const timeline = [];
  timeline.push(...buildInductionTimeline(shuffledTrials, exampleRow));

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

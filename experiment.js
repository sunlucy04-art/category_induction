/*
  SIMPLE EXPERIMENT PROPORTION VERSION

  What this file does:
  1. Shows the instruction pages.
  2. Reads the master trial list (one row per trial; every image filename
     it needs is already spelled out on that row, including its 8 evidence
     items).
  3. Shuffles the trial order (a fresh, independent order per
     participant/page load).
  4. On every trial, shows that painter's evidence items, then the new
     painting's outline, then asks the participant to choose which gabor
     pattern completes it.
  5. Randomizes which side (left/right) each of the two choices lands on
     for every trial.
  6. Records which strategy the participant selected and the reaction
     time.

  The participant will NOT see the data at the end.
  For now, you can see the data in the browser console.
*/

const csvFile = "master_trial_list.csv";

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
function getItemImages(row) {
  return Object.keys(row)
    .filter(function(key) { return /^item\d+_name$/.test(key); })
    .sort(function(a, b) {
      return Number(a.match(/\d+/)[0]) - Number(b.match(/\d+/)[0]);
    })
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
    <div class="example-board-title">${row.painter}</div>
    <div class="example-board">${imagesHTML}</div>
  `;
}

const jsPsych = initJsPsych({
  on_finish: function() {
    const dataAsCSV = jsPsych.data.get().csv();

    // This prints the data in the browser console for now.
    console.log(dataAsCSV);
  }
});

function runExperiment() {
  readCSV(csvFile).then(function(trialList) {
      // A fresh, independent trial order for this participant.
      const shuffledTrials = jsPsych.randomization.shuffle(trialList);

      const timeline = [];

      // Preload every image referenced anywhere in the trial list.
      const images = [];
      shuffledTrials.forEach(function(row) {
        images.push(row.target_probe_outline);
        images.push(row.category_induction_gabor);
        images.push(row.feature_feature_gabor);
        getItemImages(row).forEach(function(image) { images.push(image); });
      });

      timeline.push({
        type: jsPsychPreload,
        images: images
      });

      // Page 1: Welcome.
      timeline.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `
          <div class="page">
            <h2>Welcome</h2>
            <p>Welcome!</p>
            <p>In this experiment, you will explore paintings created by different painters.</p>
            <p>You will see examples of their previous artwork and will be asked to infer something about a brand new paintings created by each painter.</p>
            <p>Press any key to begin.</p>
          </div>
        `
      });

      // Page 2: Examples.
      timeline.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `
          <div class="page">
            <h2>Examples</h2>
            <p>Each painter has created many paintings in the past.</p>
            <p>You will see some randomly selected examples from that painter's previous artwork.</p>
            <p>These examples are only a small sample of each painter's work.</p>
            <p>You may refer to these examples at any time during the experiment.</p>
            <p>Press any key to continue.</p>
          </div>
        `
      });

      // Page 3: Task.
      timeline.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `
          <div class="page">
            <h2>Task</h2>
            <p>You will now see a new paintings created by these artist.</p>
            <p>Each painting will have one missing part.</p>
            <p>Your task is to choose the option that best completes the painting. Remember, you are filling in a NEW painting the artist is creating.</p>
            <p>Press any key to start.</p>
          </div>
        `
      });

      // Make one clickable trial from each row in the shuffled trial list.
      shuffledTrials.forEach(function(row) {
        // Which side (left/right) each strategy's image lands on is
        // randomized independently per trial.
        const options = jsPsych.randomization.shuffle([
          { image: row.category_induction_gabor, strategy: "general_category", gabor: row.category_dominant_gabor },
          { image: row.feature_feature_gabor, strategy: "feature_feature_strategy", gabor: row.critical_shape_dominant_gabor }
        ]);

        const choices = options.map(function(option) { return option.image; });

        timeline.push({
          type: jsPsychHtmlButtonResponse,

          stimulus: `
            <div class="page trial-page">
              ${createExampleBoard(row)}

              <p>This new painting belongs to <b>${row.painter}</b>.</p>
              <img class="new-painting" src="${row.target_probe_outline}">

              <p>What could the inside look like most likely?</p>
            </div>
          `,

          choices: choices,

          button_html: function(choice) {
            return `<button class="jspsych-btn"><img class="choice-img" src="${choice}"></button>`;
          },

          button_layout: "grid",
          grid_rows: 1,
          grid_columns: 2,

          data: {
            trial_id: row.trial_id,
            painter: row.painter,
            critical_shape: row.critical_shape,
            target_probe_outline: row.target_probe_outline,
            category_dominant_gabor: row.category_dominant_gabor,
            critical_shape_dominant_gabor: row.critical_shape_dominant_gabor,
            left_option_image: options[0].image,
            left_option_strategy: options[0].strategy,
            right_option_image: options[1].image,
            right_option_strategy: options[1].strategy
          },

          on_finish: function(data) {
            const selected = options[data.response];
            data.selected_side = data.response === 0 ? "left" : "right";
            data.selected_choice_image = selected.image;
            data.selected_strategy = selected.strategy;
            data.selected_gabor = selected.gabor;
            data.reaction_time_ms = data.rt;
          }
        });
      });

      // End page. The participant does not see the data.
      timeline.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `
          <div class="page">
            <p>You are finished. Thank you.</p>
          </div>
        `,
        choices: "NO_KEYS",
        trial_duration: 2000
      });

      jsPsych.run(timeline);
  });
}

const state = {
  expectedLabels: [],
  password: ".tie5Roanl",
  captureIndex: 0,
  pressTimes: {},
  releaseTimes: {},
  activeLabel: null,
  typed: "",
  resultsRows: [],
  charts: {
    eer: null,
    rates: null,
  },
  custom: {
    mode: "idle",
    password: "",
    targetSamples: 0,
    samples: [],
    captureIndex: 0,
    currentSample: [],
    activeIndex: null,
    activeKey: null,
    typed: "",
    profiles: [],
  },
};

const els = {
  datasetStatus: document.querySelector("#datasetStatus"),
  metricSubjects: document.querySelector("#metricSubjects"),
  metricEer: document.querySelector("#metricEer"),
  metricFar: document.querySelector("#metricFar"),
  metricFrr: document.querySelector("#metricFrr"),
  metricOpFar: document.querySelector("#metricOpFar"),
  metricOpFrr: document.querySelector("#metricOpFrr"),
  subjectSelect: document.querySelector("#subjectSelect"),
  featureSet: document.querySelector("#featureSet"),
  thresholdSource: document.querySelector("#thresholdSource"),
  kValue: document.querySelector("#kValue"),
  quantileValue: document.querySelector("#quantileValue"),
  runEvaluationButton: document.querySelector("#runEvaluationButton"),
  simulateButton: document.querySelector("#simulateButton"),
  resetCaptureButton: document.querySelector("#resetCaptureButton"),
  captureZone: document.querySelector("#captureZone"),
  typedText: document.querySelector("#typedText"),
  passwordLabel: document.querySelector("#passwordLabel"),
  expectedText: document.querySelector("#expectedText"),
  captureStatus: document.querySelector("#captureStatus"),
  decisionValue: document.querySelector("#decisionValue"),
  scoreValue: document.querySelector("#scoreValue"),
  thresholdValue: document.querySelector("#thresholdValue"),
  featureRows: document.querySelector("#featureRows"),
  resultsPath: document.querySelector("#resultsPath"),
  simulationSummary: document.querySelector("#simulationSummary"),
  tableSummary: document.querySelector("#tableSummary"),
  resultsRows: document.querySelector("#resultsRows"),
  researchMode: document.querySelector("#researchMode"),
  customProfileName: document.querySelector("#customProfileName"),
  customPassword: document.querySelector("#customPassword"),
  customTargetSamples: document.querySelector("#customTargetSamples"),
  customKValue: document.querySelector("#customKValue"),
  startEnrollButton: document.querySelector("#startEnrollButton"),
  saveProfileButton: document.querySelector("#saveProfileButton"),
  customProfileSelect: document.querySelector("#customProfileSelect"),
  startVerifyButton: document.querySelector("#startVerifyButton"),
  deleteProfileButton: document.querySelector("#deleteProfileButton"),
  resetCustomCaptureButton: document.querySelector("#resetCustomCaptureButton"),
  customPasswordLabel: document.querySelector("#customPasswordLabel"),
  customCaptureZone: document.querySelector("#customCaptureZone"),
  customTypedText: document.querySelector("#customTypedText"),
  customExpectedText: document.querySelector("#customExpectedText"),
  customCaptureStatus: document.querySelector("#customCaptureStatus"),
  customModeValue: document.querySelector("#customModeValue"),
  customSamplesValue: document.querySelector("#customSamplesValue"),
  customDecisionValue: document.querySelector("#customDecisionValue"),
  customScoreValue: document.querySelector("#customScoreValue"),
  customThresholdValue: document.querySelector("#customThresholdValue"),
  customFeatureRows: document.querySelector("#customFeatureRows"),
};

function percent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function fixed(value, digits = 4) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toFixed(digits);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || response.statusText);
  }
  return payload;
}

function settingsPayload() {
  return {
    subject: els.subjectSelect.value,
    feature_set: els.featureSet.value,
    k: Number(els.kValue.value),
    threshold_source: els.thresholdSource.value,
    operating_quantile: Number(els.quantileValue.value),
  };
}

function evaluationPayload() {
  return {
    feature_set: els.featureSet.value,
    k: Number(els.kValue.value),
    train_count: 200,
    impostor_count: 5,
    operating_quantile: Number(els.quantileValue.value),
  };
}

function setStatus(message, kind = "") {
  els.captureStatus.textContent = message;
  els.captureStatus.className = `capture-status ${kind}`.trim();
}

function setCustomStatus(message, kind = "") {
  els.customCaptureStatus.textContent = message;
  els.customCaptureStatus.className = `capture-status ${kind}`.trim();
}

function resetCapture(message = "Focus here and type the password") {
  state.captureIndex = 0;
  state.pressTimes = {};
  state.releaseTimes = {};
  state.activeLabel = null;
  state.typed = "";
  els.typedText.textContent = "";
  setStatus(message);
}

function clearCustomAttempt(message = "Type the selected password and press Enter") {
  state.custom.captureIndex = 0;
  state.custom.currentSample = [];
  state.custom.activeIndex = null;
  state.custom.activeKey = null;
  state.custom.typed = "";
  els.customTypedText.textContent = "";
  setCustomStatus(message);
}

function keyLabel(event) {
  if (event.key === "Shift") return null;
  if (event.key === "Enter" || event.key === "Return") return "Return";
  if (event.key === ".") return "period";
  if (event.key === "5") return "five";
  if (event.key === "R") return "Shift.r";
  if (["t", "i", "e", "o", "a", "n", "l"].includes(event.key)) return event.key;
  return null;
}

function displayCharacter(label) {
  const map = {
    period: ".",
    five: "5",
    "Shift.r": "R",
    Return: "",
  };
  return map[label] ?? label;
}

async function submitAttempt() {
  setStatus("Scoring attempt");
  const payload = {
    ...settingsPayload(),
    press_times: state.pressTimes,
    release_times: state.releaseTimes,
  };
  try {
    const result = await api("/api/authenticate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderDecision(result);
    renderFeatures(result.features);
    setStatus(result.verdict, result.accepted ? "ok" : "error");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    state.captureIndex = 0;
    state.pressTimes = {};
    state.releaseTimes = {};
    state.activeLabel = null;
    state.typed = "";
  }
}

function onCaptureKeyDown(event) {
  const label = keyLabel(event);
  if (!label || event.repeat) return;
  event.preventDefault();

  const expected = state.expectedLabels[state.captureIndex];
  if (label !== expected) {
    resetCapture(`Expected ${expected}, got ${label}`);
    return;
  }

  if (state.captureIndex === 0) {
    els.typedText.textContent = "";
  }

  state.activeLabel = label;
  state.pressTimes[label] = performance.now() / 1000;
}

function onCaptureKeyUp(event) {
  const label = keyLabel(event);
  if (!label) return;
  event.preventDefault();

  if (label !== state.activeLabel) {
    resetCapture(`Release mismatch for ${label}`);
    return;
  }

  state.releaseTimes[label] = performance.now() / 1000;
  state.captureIndex += 1;
  state.typed += displayCharacter(label);
  els.typedText.textContent = state.typed;
  state.activeLabel = null;

  if (label === "Return") {
    submitAttempt();
  } else {
    setStatus(`${state.captureIndex}/${state.expectedLabels.length}`);
  }
}

function renderDecision(result) {
  els.decisionValue.textContent = result.verdict;
  els.decisionValue.className = result.accepted ? "accept" : "reject";
  els.scoreValue.textContent = fixed(result.score);
  els.thresholdValue.textContent = fixed(result.threshold);
}

function renderFeatures(features) {
  els.featureRows.innerHTML = "";
  const visibleFeatures = features.slice(0, 40);
  for (const feature of visibleFeatures) {
    const row = document.createElement("tr");
    row.innerHTML = `<td>${feature.name}</td><td>${fixed(feature.value, 5)}</td>`;
    els.featureRows.append(row);
  }
}

function renderCustomFeatures(features) {
  els.customFeatureRows.innerHTML = "";
  const visibleFeatures = features.slice(0, 60);
  if (!visibleFeatures.length) {
    els.customFeatureRows.innerHTML = '<tr><td colspan="2">No custom attempt scored yet</td></tr>';
    return;
  }
  for (const feature of visibleFeatures) {
    const row = document.createElement("tr");
    row.innerHTML = `<td>${feature.name}</td><td>${fixed(feature.value, 5)}</td>`;
    els.customFeatureRows.append(row);
  }
}

function renderSummary(summary) {
  els.metricSubjects.textContent = summary.subjects ?? "-";
  els.metricEer.textContent = percent(summary.eer_mean);
  els.metricFar.textContent = percent(summary.far_at_eer_mean);
  els.metricFrr.textContent = percent(summary.frr_at_eer_mean);
  els.metricOpFar.textContent = percent(summary.operating_far_mean);
  els.metricOpFrr.textContent = percent(summary.operating_frr_mean);
}

function renderSubjects(subjects) {
  els.subjectSelect.innerHTML = "";
  for (const subject of subjects) {
    const option = document.createElement("option");
    option.value = subject;
    option.textContent = subject;
    els.subjectSelect.append(option);
  }
}

function renderCustomProfiles(profiles) {
  state.custom.profiles = profiles;
  els.customProfileSelect.innerHTML = "";

  if (!profiles.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No saved profiles";
    els.customProfileSelect.append(option);
    els.startVerifyButton.disabled = true;
    els.deleteProfileButton.disabled = true;
    return;
  }

  for (const profile of profiles) {
    const option = document.createElement("option");
    option.value = profile.name;
    option.textContent = `${profile.name} (${profile.sample_count} samples)`;
    els.customProfileSelect.append(option);
  }
  els.startVerifyButton.disabled = false;
  els.deleteProfileButton.disabled = false;
}

function selectedCustomProfile() {
  return state.custom.profiles.find(
    (profile) => profile.name === els.customProfileSelect.value,
  );
}

function renderCustomProgress() {
  const target = state.custom.targetSamples || 0;
  els.customModeValue.textContent =
    state.custom.mode === "enroll"
      ? "Enroll"
      : state.custom.mode === "verify"
        ? "Verify"
        : "Idle";
  els.customSamplesValue.textContent = `${state.custom.samples.length}/${target}`;
  els.saveProfileButton.disabled = state.custom.samples.length < 3;
}

function renderResultsTable(rows) {
  els.resultsRows.innerHTML = "";
  if (!rows.length) {
    els.resultsRows.innerHTML = '<tr><td colspan="6">No results available</td></tr>';
    els.tableSummary.textContent = "";
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.subject}</td>
      <td>${percent(row.eer)}</td>
      <td>${percent(row.far_at_eer)}</td>
      <td>${percent(row.frr_at_eer)}</td>
      <td>${percent(row.operating_far)}</td>
      <td>${percent(row.operating_frr)}</td>
    `;
    els.resultsRows.append(tr);
  }
  els.tableSummary.textContent = `${rows.length} rows`;
}

function upsertChart(existing, canvas, config) {
  if (existing) existing.destroy();
  return new Chart(canvas, config);
}

function renderCharts(rows) {
  const labels = rows.map((row) => row.subject);
  const eerData = rows.map((row) => Number(row.eer) * 100);
  const farData = rows.map((row) => Number(row.far_at_eer) * 100);
  const frrData = rows.map((row) => Number(row.frr_at_eer) * 100);

  state.charts.eer = upsertChart(state.charts.eer, document.querySelector("#eerChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "EER %", data: eerData, backgroundColor: "#2563eb" }],
    },
    options: chartOptions("Error rate (%)"),
  });

  state.charts.rates = upsertChart(state.charts.rates, document.querySelector("#ratesChart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "FAR@EER %",
          data: farData,
          borderColor: "#b42318",
          backgroundColor: "rgba(180, 35, 24, 0.1)",
          tension: 0.2,
        },
        {
          label: "FRR@EER %",
          data: frrData,
          borderColor: "#15803d",
          backgroundColor: "rgba(21, 128, 61, 0.1)",
          tension: 0.2,
        },
      ],
    },
    options: chartOptions("Error rate (%)"),
  });
}

function chartOptions(yTitle) {
  return {
    responsive: true,
    maintainAspectRatio: true,
    interaction: { mode: "index", intersect: false },
    scales: {
      x: { ticks: { maxRotation: 90, minRotation: 70, autoSkip: true, maxTicksLimit: 28 } },
      y: { beginAtZero: true, title: { display: true, text: yTitle } },
    },
    plugins: {
      legend: { labels: { boxWidth: 12 } },
    },
  };
}

function applyResults(rows, summary, path = "") {
  state.resultsRows = rows;
  renderSummary(summary);
  renderResultsTable(rows);
  renderCharts(rows);
  els.resultsPath.textContent = path ? path.split(/[\\/]/).slice(-2).join("/") : "";
}

async function loadStatus() {
  try {
    const data = await api("/api/status");
    state.expectedLabels = data.dataset.expected_labels;
    state.password = data.dataset.password;
    els.expectedText.textContent = state.password;
    els.passwordLabel.textContent = `${state.password} + Enter`;
    els.datasetStatus.textContent = `${data.dataset.subjects} subjects, ${data.dataset.rows} rows`;
    els.datasetStatus.className = "status-pill ok";
    renderSubjects(data.subjects);
    renderCustomProfiles(data.custom_profiles.profiles);
    applyResults(data.results.rows, data.results.summary, data.results.path);
    resetCapture();
    renderCustomProgress();
  } catch (error) {
    els.datasetStatus.textContent = error.message;
    els.datasetStatus.className = "status-pill error";
    setStatus(error.message, "error");
  }
}

async function runEvaluation() {
  els.runEvaluationButton.disabled = true;
  els.runEvaluationButton.textContent = "Running";
  try {
    const data = await api("/api/evaluate", {
      method: "POST",
      body: JSON.stringify(evaluationPayload()),
    });
    applyResults(data.rows, data.summary, data.path);
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    els.runEvaluationButton.disabled = false;
    els.runEvaluationButton.textContent = "Run Evaluation";
  }
}

async function simulate() {
  els.simulateButton.disabled = true;
  els.simulateButton.textContent = "Running";
  try {
    const data = await api("/api/simulate", {
      method: "POST",
      body: JSON.stringify({
        ...settingsPayload(),
        attempts: 8,
        include_impostors: true,
      }),
    });
    const accepted = data.decisions.filter((decision) => decision.accepted).length;
    els.simulationSummary.textContent = `${accepted}/${data.decisions.length} accepted`;
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    els.simulateButton.disabled = false;
    els.simulateButton.textContent = "Simulate";
  }
}

function customInputKey(event) {
  if (event.key === "Enter") return "Enter";
  if (event.ctrlKey || event.altKey || event.metaKey) return null;
  if (["Shift", "CapsLock", "AltGraph"].includes(event.key)) return null;
  if (event.key.length === 1) return event.key;
  return null;
}

function startCustomEnrollment() {
  const password = els.customPassword.value.trim();
  const targetSamples = Number(els.customTargetSamples.value);
  if (!password) {
    setCustomStatus("Enter a custom password first", "error");
    return;
  }
  if (targetSamples < 3) {
    setCustomStatus("Use at least 3 enrollment samples", "error");
    return;
  }

  state.custom.mode = "enroll";
  state.custom.password = password;
  state.custom.targetSamples = targetSamples;
  state.custom.samples = [];
  els.customPasswordLabel.textContent = `${password} + Enter`;
  els.customExpectedText.textContent = password;
  els.customDecisionValue.textContent = "-";
  els.customDecisionValue.className = "";
  els.customScoreValue.textContent = "-";
  els.customThresholdValue.textContent = "-";
  renderCustomFeatures([]);
  renderCustomProgress();
  clearCustomAttempt(`Enrollment sample 1/${targetSamples}`);
  els.customCaptureZone.focus();
}

function startCustomVerification() {
  const profile = selectedCustomProfile();
  if (!profile) {
    setCustomStatus("No saved custom profile selected", "error");
    return;
  }

  state.custom.mode = "verify";
  state.custom.password = profile.password;
  state.custom.targetSamples = 1;
  state.custom.samples = [];
  els.customProfileName.value = profile.name;
  els.customPassword.value = profile.password;
  els.customPasswordLabel.textContent = `${profile.name}: ${profile.password} + Enter`;
  els.customExpectedText.textContent = profile.password;
  els.customDecisionValue.textContent = "-";
  els.customDecisionValue.className = "";
  els.customScoreValue.textContent = "-";
  els.customThresholdValue.textContent = "-";
  renderCustomFeatures([]);
  renderCustomProgress();
  clearCustomAttempt("Verification attempt 1/1");
  els.customCaptureZone.focus();
}

function onCustomKeyDown(event) {
  if (state.custom.mode === "idle") return;

  const key = customInputKey(event);
  if (!key || event.repeat) return;
  event.preventDefault();

  if (key === "Enter") {
    finalizeCustomAttempt();
    return;
  }

  const expected = state.custom.password[state.custom.captureIndex];
  if (!expected) {
    setCustomStatus("Press Enter to submit this attempt", "error");
    return;
  }
  if (key !== expected) {
    clearCustomAttempt(`Expected ${expected}, got ${key}`);
    return;
  }

  if (state.custom.captureIndex === 0) {
    els.customTypedText.textContent = "";
  }

  state.custom.activeIndex = state.custom.captureIndex;
  state.custom.activeKey = key;
  state.custom.currentSample[state.custom.captureIndex] = {
    key,
    press: performance.now() / 1000,
  };
}

function onCustomKeyUp(event) {
  if (state.custom.mode === "idle") return;

  const key = customInputKey(event);
  if (!key || key === "Enter") return;
  event.preventDefault();

  if (state.custom.activeKey !== key || state.custom.activeIndex === null) {
    clearCustomAttempt(`Release mismatch for ${key}`);
    return;
  }

  const eventIndex = state.custom.activeIndex;
  state.custom.currentSample[eventIndex].release = performance.now() / 1000;
  state.custom.captureIndex += 1;
  state.custom.typed += key;
  els.customTypedText.textContent = state.custom.typed;
  state.custom.activeIndex = null;
  state.custom.activeKey = null;

  if (state.custom.captureIndex === state.custom.password.length) {
    setCustomStatus("Press Enter to submit");
  } else {
    setCustomStatus(`${state.custom.captureIndex}/${state.custom.password.length}`);
  }
}

function completeCustomSample() {
  if (state.custom.captureIndex !== state.custom.password.length) {
    throw new Error("Finish typing the password before pressing Enter");
  }

  return state.custom.currentSample.map((event, index) => {
    if (!event || event.release === undefined) {
      throw new Error(`Missing release timing for key ${index + 1}`);
    }
    return {
      key: event.key,
      press: event.press,
      release: event.release,
    };
  });
}

async function finalizeCustomAttempt() {
  let sample;
  try {
    sample = completeCustomSample();
  } catch (error) {
    setCustomStatus(error.message, "error");
    return;
  }

  if (state.custom.mode === "enroll") {
    state.custom.samples.push(sample);
    renderCustomProgress();

    if (state.custom.samples.length >= state.custom.targetSamples) {
      clearCustomAttempt("Enough samples captured. Save the profile.");
      els.saveProfileButton.disabled = false;
      return;
    }

    clearCustomAttempt(
      `Enrollment sample ${state.custom.samples.length + 1}/${state.custom.targetSamples}`,
    );
    return;
  }

  if (state.custom.mode === "verify") {
    await verifyCustomAttempt(sample);
  }
}

async function saveCustomProfile() {
  if (state.custom.samples.length < 3) {
    setCustomStatus("Capture at least 3 enrollment samples first", "error");
    return;
  }

  els.saveProfileButton.disabled = true;
  els.saveProfileButton.textContent = "Saving";
  try {
    const result = await api("/api/custom/enroll", {
      method: "POST",
      body: JSON.stringify({
        name: els.customProfileName.value,
        password: state.custom.password,
        samples: state.custom.samples,
        k: Number(els.customKValue.value),
        operating_quantile: Number(els.quantileValue.value),
      }),
    });
    els.customThresholdValue.textContent = fixed(result.threshold);
    setCustomStatus(`Saved ${result.profile.name}`, "ok");
    await loadCustomProfiles();
    els.customProfileSelect.value = result.profile.name;
  } catch (error) {
    setCustomStatus(error.message, "error");
  } finally {
    els.saveProfileButton.textContent = "Save Profile";
    renderCustomProgress();
  }
}

async function verifyCustomAttempt(sample) {
  setCustomStatus("Scoring custom attempt");
  try {
    const result = await api("/api/custom/verify", {
      method: "POST",
      body: JSON.stringify({
        name: els.customProfileSelect.value,
        sample,
        k: Number(els.customKValue.value),
        operating_quantile: Number(els.quantileValue.value),
      }),
    });
    els.customDecisionValue.textContent = result.verdict;
    els.customDecisionValue.className = result.accepted ? "accept" : "reject";
    els.customScoreValue.textContent = fixed(result.score);
    els.customThresholdValue.textContent = fixed(result.threshold);
    renderCustomFeatures(result.features);
    setCustomStatus(result.verdict, result.accepted ? "ok" : "error");
  } catch (error) {
    setCustomStatus(error.message, "error");
  } finally {
    state.custom.captureIndex = 0;
    state.custom.currentSample = [];
    state.custom.activeIndex = null;
    state.custom.activeKey = null;
    state.custom.typed = "";
    els.customTypedText.textContent = "";
  }
}

async function loadCustomProfiles() {
  try {
    const data = await api("/api/custom/profiles");
    renderCustomProfiles(data.profiles);
  } catch (error) {
    setCustomStatus(error.message, "error");
  }
}

async function deleteCustomProfile() {
  const profile = selectedCustomProfile();
  if (!profile) {
    setCustomStatus("No saved custom profile selected", "error");
    return;
  }

  try {
    const data = await api(`/api/custom/profiles/${encodeURIComponent(profile.name)}`, {
      method: "DELETE",
    });
    renderCustomProfiles(data.profiles);
    setCustomStatus(`Deleted ${profile.name}`, "ok");
  } catch (error) {
    setCustomStatus(error.message, "error");
  }
}

function syncSelectedCustomProfile() {
  const profile = selectedCustomProfile();
  if (!profile) return;
  els.customProfileName.value = profile.name;
  els.customPassword.value = profile.password;
}

els.captureZone.addEventListener("keydown", onCaptureKeyDown);
els.captureZone.addEventListener("keyup", onCaptureKeyUp);
els.resetCaptureButton.addEventListener("click", () => {
  resetCapture();
  els.captureZone.focus();
});
els.runEvaluationButton.addEventListener("click", runEvaluation);
els.simulateButton.addEventListener("click", simulate);
els.customCaptureZone.addEventListener("keydown", onCustomKeyDown);
els.customCaptureZone.addEventListener("keyup", onCustomKeyUp);
els.resetCustomCaptureButton.addEventListener("click", () => {
  clearCustomAttempt();
  els.customCaptureZone.focus();
});
els.startEnrollButton.addEventListener("click", startCustomEnrollment);
els.saveProfileButton.addEventListener("click", saveCustomProfile);
els.startVerifyButton.addEventListener("click", startCustomVerification);
els.deleteProfileButton.addEventListener("click", deleteCustomProfile);
els.customProfileSelect.addEventListener("change", syncSelectedCustomProfile);
els.researchMode.addEventListener("toggle", () => {
  if (!els.researchMode.open) return;
  for (const chart of Object.values(state.charts)) {
    if (chart) chart.resize();
  }
});

loadStatus();

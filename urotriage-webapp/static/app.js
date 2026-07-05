const ZONE_LABELS = { red: "КРАСНЫЙ", yellow: "ЖЁЛТЫЙ", green: "ЗЕЛЁНЫЙ", none: "—" };
const ZONE_HINTS = {
  red: "Тяжёлое течение — приоритетный осмотр",
  yellow: "Настороженность — дообследовать",
  green: "Признаков тяжёлого течения не выявлено",
  none: "Зона не рассчитана",
};
const ONSET_LABELS = { lt6: "менее 6 часов", "6to24": "6–24 часа", gt24: "более 24 часов", unknown: "не установлено" };
const DRAINAGE_LABELS = { urethral: "уретральный катетер", cystostomy: "цистостомия", trocar: "троакарная эпицистостомия", none: "не потребовалось" };
const ATTEMPT_LABELS = { first_try: "с первой попытки", difficult: "с трудностями", failed: "не удалась" };
const HYDRO_LABELS = { none: "нет", pyeloectasia: "пиелоэктазия", unilateral: "односторонний", bilateral: "двусторонний" };
const COMPLAINT_LABELS = {
  no_voiding: "не мочится", suprapubic_pain: "боль над лоном", severe_pain: "выраженная боль",
  urge: "императивные позывы", fever_chills: "лихорадка/озноб", gross_hematuria: "макрогематурия",
  blood_clots: "сгустки крови", weakness: "слабость",
};
const OUTCOME_OPTIONS = ["Выписан с улучшением", "Выписан без изменений", "Переведён", "Умер"];

const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

let editId = null;
let listFilter = "all";
let triageTimer = null;

function toast(msg, ms) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add("hidden"), ms || 2600);
}

function setupSegments(root) {
  $$(".seg", root || document).forEach((seg) => {
    if (seg._wired) return;
    seg._wired = true;
    seg.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      const wasOn = btn.classList.contains("on");
      $$("button", seg).forEach((b) => b.classList.remove("on"));
      const holder = seg.dataset.name ? seg : seg.closest("[data-name]") || seg;
      if (wasOn) {
        delete holder.dataset.value;
      } else {
        btn.classList.add("on");
        holder.dataset.value = btn.dataset.value;
      }
      onFormChanged();
    });
  });
}

function setupChips() {
  const box = $('.chips[data-name="complaints_flags"]');
  box.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    btn.classList.toggle("on");
    onFormChanged();
  });
}

function segValue(name) {
  const holder = $(`#patient-form [data-name="${name}"]`);
  if (!holder) return null;
  const v = holder.dataset.value;
  if (v === undefined) return null;
  if (v === "true") return true;
  if (v === "false") return false;
  return v;
}

function setSegValue(name, value) {
  const holder = $(`#patient-form [data-name="${name}"]`);
  if (!holder) return;
  const seg = holder.classList.contains("seg") ? holder : $(".seg", holder);
  $$("button", seg).forEach((b) => b.classList.remove("on"));
  delete holder.dataset.value;
  if (value === null || value === undefined || value === "") return;
  const target = $$("button", seg).find((b) => b.dataset.value === String(value));
  if (target) {
    target.classList.add("on");
    holder.dataset.value = String(value);
  }
}

function inputValue(name) {
  const el = $(`#patient-form [name="${name}"]`);
  const v = (el && el.value || "").trim();
  return v === "" ? null : v;
}

function collectPayload() {
  const flags = $$('.chips[data-name="complaints_flags"] button.on').map((b) => b.dataset.value);
  const payload = {
    case_id: inputValue("case_id"),
    admitted_at: inputValue("admitted_at"),
    age: inputValue("age"),
    onset_category: segValue("onset_category"),
    complaints_flags: flags,
    complaints_text: inputValue("complaints_text"),
    diagnosis_text: inputValue("diagnosis_text"),
    disease_duration_years: inputValue("disease_duration_years"),
    psa: inputValue("psa"),
    prior_ozm_count: segValue("prior_ozm_count"),
    prior_residual: segValue("prior_residual"),
    bladder_stones: segValue("bladder_stones"),
    prior_prostate_surgery: segValue("prior_prostate_surgery"),
    alpha_blockers: segValue("alpha_blockers"),
    reductase_inhibitors: segValue("reductase_inhibitors"),
    temp: inputValue("temp"),
    pulse: inputValue("pulse"),
    bp_sys: inputValue("bp_sys"),
    bp_dia: inputValue("bp_dia"),
    wbc: inputValue("wbc"),
    hemoglobin: inputValue("hemoglobin"),
    creatinine: inputValue("creatinine"),
    urea: inputValue("urea"),
    crp: inputValue("crp"),
    pct: inputValue("pct"),
    prostate_vol: inputValue("prostate_vol"),
    residual_urine_ml: inputValue("residual_urine_ml"),
    median_lobe: segValue("median_lobe"),
    median_lobe_size: inputValue("median_lobe_size"),
    hydronephrosis: segValue("hydronephrosis"),
    imaging_text: inputValue("imaging_text"),
    drainage_method: segValue("drainage_method"),
    catheter_attempt: segValue("catheter_attempt"),
    doctor: localStorage.getItem("doctor") || null,
  };
  return payload;
}

function fillForm(payload) {
  $$("#patient-form input, #patient-form textarea").forEach((el) => {
    if (payload[el.name] !== undefined && payload[el.name] !== null) el.value = payload[el.name];
    else el.value = "";
  });
  ["onset_category", "prior_ozm_count", "prior_residual", "bladder_stones", "prior_prostate_surgery",
   "alpha_blockers", "reductase_inhibitors", "median_lobe", "hydronephrosis", "drainage_method", "catheter_attempt"]
    .forEach((n) => setSegValue(n, payload[n]));
  $$('.chips[data-name="complaints_flags"] button').forEach((b) => {
    b.classList.toggle("on", (payload.complaints_flags || []).includes(b.dataset.value));
  });
  toggleMedianLobeSize();
}

function resetForm() {
  editId = null;
  $("#patient-form").reset();
  $$("#patient-form .seg button").forEach((b) => b.classList.remove("on"));
  $$("#patient-form [data-name]").forEach((h) => delete h.dataset.value);
  $$('.chips[data-name="complaints_flags"] button').forEach((b) => b.classList.remove("on"));
  toggleMedianLobeSize();
  localStorage.removeItem("draft");
  $("#save-btn").textContent = "Сохранить пациента";
  setLiveZone(null);
}

function toggleMedianLobeSize() {
  const on = segValue("median_lobe") === true;
  $("#median-lobe-size-field").style.display = on ? "block" : "none";
}

function setLiveZone(zone) {
  const chip = $("#live-zone");
  chip.className = "zone-chip zone-" + (zone || "none");
  chip.textContent = ZONE_LABELS[zone || "none"];
}

function onFormChanged() {
  toggleMedianLobeSize();
  const payload = collectPayload();
  if (!editId) localStorage.setItem("draft", JSON.stringify(payload));
  clearTimeout(triageTimer);
  triageTimer = setTimeout(async () => {
    try {
      const r = await fetch("/api/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload }),
      });
      const data = await r.json();
      setLiveZone(data.triage ? data.triage.final_zone : null);
    } catch (e) {
      setLiveZone(null);
    }
  }, 600);
}

function getOutbox() {
  try { return JSON.parse(localStorage.getItem("outbox") || "[]"); } catch (e) { return []; }
}

function setOutbox(items) {
  localStorage.setItem("outbox", JSON.stringify(items));
  updateOfflineBanner();
}

function updateOfflineBanner() {
  const banner = $("#offline-banner");
  const n = getOutbox().length;
  if (!navigator.onLine) {
    banner.textContent = n ? `Нет сети — ${n} запись(ей) ждёт отправки` : "Нет сети — записи будут сохранены локально и отправлены позже";
    banner.classList.remove("hidden");
  } else if (n) {
    banner.textContent = `Отправка отложенных записей: ${n}…`;
    banner.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }
}

async function flushOutbox() {
  const items = getOutbox();
  if (!items.length || !navigator.onLine) return;
  const remaining = [];
  for (const item of items) {
    try {
      const r = await fetch("/api/records", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload: item }),
      });
      if (!r.ok) throw new Error("server");
    } catch (e) {
      remaining.push(item);
    }
  }
  setOutbox(remaining);
  if (!remaining.length && items.length) toast("Отложенные записи отправлены");
}

async function saveRecord() {
  const payload = collectPayload();
  if (!payload.case_id) {
    toast("Укажите № истории болезни");
    $('#patient-form [name="case_id"]').focus();
    return;
  }
  const btn = $("#save-btn");
  btn.disabled = true;
  btn.textContent = "Сохранение…";
  try {
    const url = editId ? `/api/records/${editId}` : "/api/records";
    const r = await fetch(url, {
      method: editId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || "Ошибка сервера");
    }
    const data = await r.json();
    showResult(payload.case_id, data.triage, data.triage_error);
    resetForm();
  } catch (e) {
    if (!navigator.onLine || e instanceof TypeError) {
      setOutbox([...getOutbox(), payload]);
      toast("Нет сети: запись сохранена локально и уйдёт автоматически");
      resetForm();
    } else {
      toast(e.message || "Не удалось сохранить");
    }
  } finally {
    btn.disabled = false;
    btn.textContent = editId ? "Сохранить изменения" : "Сохранить пациента";
  }
}

function renderTriage(triage, triageError) {
  if (!triage) {
    return `<div class="zone-banner none"><b>Зона не рассчитана</b><span>${triageError ? "Светофор недоступен, запись сохранена" : ""}</span></div>`;
  }
  const zone = triage.final_zone;
  let html = `<div class="zone-banner ${zone}"><b>${ZONE_LABELS[zone]}</b><span>${ZONE_HINTS[zone]}</span></div>`;
  const items = triage.rule.fired_criteria
    .map((c) => `<li class="${c.zone}">${c.message}</li>`)
    .join("");
  if (items) html += `<ul class="criteria">${items}</ul>`;
  if (triage.ml && triage.ml.action === "upgrade_to_yellow") {
    html += `<ul class="criteria"><li class="info">${triage.ml.message}</li></ul>`;
  }
  if (triage.rule.missing_fields.length) {
    html += `<p class="muted">Не заполнено: ${triage.rule.missing_fields.join(", ")} — зона может быть неполной.</p>`;
  }
  html += `<p class="muted">Светофор — подсказка, решение остаётся за врачом.</p>`;
  return html;
}

function showResult(caseId, triage, triageError) {
  const body = $("#result-body");
  body.innerHTML = `
    <div class="card">
      <h2>Пациент ${caseId} сохранён</h2>
      ${renderTriage(triage, triageError)}
    </div>
    <div class="modal-actions">
      <button type="button" class="btn secondary" id="result-to-list">К списку</button>
      <button type="button" class="btn primary" id="result-new">Новый пациент</button>
    </div>`;
  $("#result-modal").classList.remove("hidden");
  $("#result-new").addEventListener("click", () => {
    $("#result-modal").classList.add("hidden");
    switchView("new");
    window.scrollTo(0, 0);
  });
  $("#result-to-list").addEventListener("click", () => {
    $("#result-modal").classList.add("hidden");
    switchView("list");
  });
}

function switchView(name) {
  $$(".view").forEach((v) => v.classList.add("hidden"));
  $(`#view-${name === "detail" ? "detail" : name}`).classList.remove("hidden");
  $$(".nav-btn").forEach((b) => b.classList.toggle("on", b.dataset.view === (name === "detail" ? "list" : name)));
  $("#save-bar").classList.toggle("hidden", name !== "new");
  if (name === "list") loadRecords();
  if (name === "stats") loadStats();
}

async function loadRecords() {
  const q = $("#search-input").value.trim();
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (listFilter === "no-outcome") params.set("missing_outcome", "true");
  if (["red", "yellow", "green"].includes(listFilter)) params.set("zone", listFilter);
  const box = $("#records-list");
  try {
    const r = await fetch("/api/records?" + params.toString());
    const data = await r.json();
    if (!data.records.length) {
      box.innerHTML = `<div class="empty">Записей пока нет.<br>Добавьте первого пациента во вкладке «Новый».</div>`;
      return;
    }
    box.innerHTML = data.records
      .map((rec) => {
        const d = new Date(rec.created_at);
        const date = isNaN(d) ? "" : d.toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
        return `<button type="button" class="record-row" data-id="${rec.id}">
          <span class="zone-dot ${rec.zone || "none"}"></span>
          <span class="record-main"><b>${rec.case_id}</b><small>${date}${rec.doctor ? " · " + rec.doctor : ""}</small></span>
          ${rec.outcome_filled ? "" : '<span class="badge">без исхода</span>'}
        </button>`;
      })
      .join("");
    $$(".record-row", box).forEach((row) => row.addEventListener("click", () => openDetail(row.dataset.id)));
  } catch (e) {
    box.innerHTML = `<div class="empty">Не удалось загрузить список (нет сети?)</div>`;
  }
}

function kvRow(label, value) {
  if (value === null || value === undefined || value === "" || (Array.isArray(value) && !value.length)) return "";
  return `<tr><td>${label}</td><td>${value}</td></tr>`;
}

function boolRu(v) {
  return v === true ? "Да" : v === false ? "Нет" : null;
}

async function openDetail(id) {
  const r = await fetch(`/api/records/${id}`);
  if (!r.ok) { toast("Запись не найдена"); return; }
  const rec = await r.json();
  const p = rec.payload;
  const content = $("#detail-content");
  const flags = (p.complaints_flags || []).map((f) => COMPLAINT_LABELS[f] || f).join(", ");
  content.innerHTML = `
    <div class="card">
      <h2>Пациент ${rec.case_id}</h2>
      ${renderTriage(rec.triage, null)}
    </div>
    <div class="card">
      <h2>Данные</h2>
      <table class="kv">
        ${kvRow("Поступление", p.admitted_at ? p.admitted_at.replace("T", " ") : null)}
        ${kvRow("Возраст", p.age)}
        ${kvRow("Время от начала задержки", ONSET_LABELS[p.onset_category])}
        ${kvRow("Жалобы", [flags, p.complaints_text].filter(Boolean).join("; "))}
        ${kvRow("Диагноз", p.diagnosis_text)}
        ${kvRow("ДГПЖ, лет", p.disease_duration_years)}
        ${kvRow("ПСА, нг/мл", p.psa)}
        ${kvRow("ОЗМ ранее", p.prior_ozm_count === "2" ? "2 и более" : p.prior_ozm_count === "0" ? "впервые" : p.prior_ozm_count)}
        ${kvRow("Остаточная моча ранее", boolRu(p.prior_residual))}
        ${kvRow("Камни мочевого пузыря", boolRu(p.bladder_stones))}
        ${kvRow("Операции на простате", boolRu(p.prior_prostate_surgery))}
        ${kvRow("Альфа-адреноблокаторы", boolRu(p.alpha_blockers))}
        ${kvRow("Ингибиторы 5-АР", boolRu(p.reductase_inhibitors))}
        ${kvRow("Температура, °C", p.temp)}
        ${kvRow("АД", p.bp_sys && p.bp_dia ? `${p.bp_sys}/${p.bp_dia}` : p.bp_sys || p.bp_dia)}
        ${kvRow("Пульс", p.pulse)}
        ${kvRow("Лейкоциты", p.wbc)}
        ${kvRow("Гемоглобин", p.hemoglobin)}
        ${kvRow("Креатинин", p.creatinine)}
        ${kvRow("Мочевина", p.urea)}
        ${kvRow("СРБ", p.crp)}
        ${kvRow("ПКТ", p.pct)}
        ${kvRow("Объём простаты, см³", p.prostate_vol)}
        ${kvRow("Средняя доля", boolRu(p.median_lobe))}
        ${kvRow("Размер средней доли, мм", p.median_lobe_size)}
        ${kvRow("Остаточная моча, мл", p.residual_urine_ml)}
        ${kvRow("Гидронефроз", HYDRO_LABELS[p.hydronephrosis])}
        ${kvRow("УЗИ/КТ", p.imaging_text)}
        ${kvRow("Дренирование", DRAINAGE_LABELS[p.drainage_method])}
        ${kvRow("Катетеризация", ATTEMPT_LABELS[p.catheter_attempt])}
        ${kvRow("Врач", rec.doctor)}
      </table>
    </div>
    <div class="card" id="outcome-card">
      <h2>Исход госпитализации</h2>
      ${rec.outcome_filled ? `
        <table class="kv">
          ${kvRow("Операция", boolRu(p.had_operation))}
          ${kvRow("Вид операции", p.operation_txt)}
          ${kvRow("Часов до операции", p.hours_to_oper)}
          ${kvRow("Исход", p.outcome_txt)}
          ${kvRow("Осложнения", p.complications_txt)}
          ${kvRow("Повторная госпитализация", boolRu(p.readmission))}
        </table>
        <button type="button" class="btn ghost" id="outcome-edit-btn" style="margin-top:10px">Изменить исход</button>
      ` : `<button type="button" class="btn primary" id="outcome-edit-btn">Дозаполнить исход</button>`}
    </div>
    <button type="button" class="btn secondary" id="edit-record-btn">Редактировать данные пациента</button>
  `;
  $("#outcome-edit-btn").addEventListener("click", () => renderOutcomeForm(rec));
  $("#edit-record-btn").addEventListener("click", () => {
    editId = rec.id;
    fillForm(p);
    $("#save-btn").textContent = "Сохранить изменения";
    switchView("new");
    window.scrollTo(0, 0);
  });
  switchView("detail");
}

function renderOutcomeForm(rec) {
  const p = rec.payload;
  const card = $("#outcome-card");
  card.innerHTML = `
    <h2>Исход госпитализации</h2>
    <div class="field"><span>Операция за госпитализацию</span>
      <div class="seg" id="oc-had-op">
        <button type="button" data-value="false">Нет</button>
        <button type="button" data-value="true">Да</button>
      </div>
    </div>
    <label class="field"><span>Вид операции / вмешательства</span>
      <input type="text" id="oc-operation" value="${p.operation_txt || ""}" placeholder="ТУР, цистостомия…"></label>
    <label class="field"><span>Часов от поступления до операции</span>
      <input type="text" inputmode="numeric" id="oc-hours" value="${p.hours_to_oper || ""}" placeholder="—"></label>
    <div class="field"><span>Исход</span>
      <div class="seg wrap" id="oc-outcome">
        ${OUTCOME_OPTIONS.map((o) => `<button type="button" data-value="${o}">${o}</button>`).join("")}
      </div>
    </div>
    <label class="field"><span>Осложнения</span>
      <input type="text" id="oc-compl" value="${p.complications_txt || ""}" placeholder="Нет"></label>
    <div class="field"><span>Повторная госпитализация по ОЗМ</span>
      <div class="seg" id="oc-readm">
        <button type="button" data-value="false">Нет</button>
        <button type="button" data-value="true">Да</button>
      </div>
    </div>
    <button type="button" class="btn primary" id="oc-save">Сохранить исход</button>
  `;
  const wireSeg = (id, current) => {
    const seg = $(`#${id}`);
    $$("button", seg).forEach((b) => {
      if (String(current) === b.dataset.value) b.classList.add("on");
      b.addEventListener("click", () => {
        const was = b.classList.contains("on");
        $$("button", seg).forEach((x) => x.classList.remove("on"));
        if (!was) b.classList.add("on");
      });
    });
  };
  wireSeg("oc-had-op", p.had_operation);
  wireSeg("oc-outcome", p.outcome_txt);
  wireSeg("oc-readm", p.readmission);
  const segVal = (id) => {
    const on = $(`#${id} button.on`);
    if (!on) return null;
    if (on.dataset.value === "true") return true;
    if (on.dataset.value === "false") return false;
    return on.dataset.value;
  };
  $("#oc-save").addEventListener("click", async () => {
    const outcome = {
      had_operation: segVal("oc-had-op"),
      operation_txt: $("#oc-operation").value.trim() || null,
      hours_to_oper: $("#oc-hours").value.trim() || null,
      outcome_txt: segVal("oc-outcome"),
      complications_txt: $("#oc-compl").value.trim() || null,
      readmission: segVal("oc-readm"),
    };
    try {
      const r = await fetch(`/api/records/${rec.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload: outcome }),
      });
      if (!r.ok) throw new Error();
      toast("Исход сохранён");
      openDetail(rec.id);
    } catch (e) {
      toast("Не удалось сохранить исход — проверьте сеть");
    }
  });
}

async function loadStats() {
  const grid = $("#stats-cards");
  try {
    const [statsR, healthR] = await Promise.all([fetch("/api/stats"), fetch("/api/health")]);
    const s = await statsR.json();
    const h = await healthR.json();
    grid.innerHTML = `
      <div class="stat-card"><b>${s.total}</b><span>всего записей</span></div>
      <div class="stat-card"><b>${s.last7}</b><span>за 7 дней</span></div>
      <div class="stat-card red"><b>${s.by_zone.red}</b><span>красных</span></div>
      <div class="stat-card yellow"><b>${s.by_zone.yellow}</b><span>жёлтых</span></div>
      <div class="stat-card green"><b>${s.by_zone.green}</b><span>зелёных</span></div>
      <div class="stat-card"><b>${s.missing_outcome}</b><span>без исхода</span></div>`;
    const t = h.triage_api;
    $("#health-info").innerHTML = t.reachable
      ? `Светофор: работает${t.info && t.info.model_loaded ? ", модель загружена" : ", модель не загружена (только правило)"}`
      : `Светофор: недоступен (${t.url}). Записи сохраняются, зона рассчитается позже.`;
  } catch (e) {
    grid.innerHTML = `<div class="empty">Нет связи с сервером</div>`;
  }
}

function init() {
  setupSegments();
  setupChips();
  $("#patient-form").addEventListener("input", onFormChanged);
  $("#dx-quick").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    const field = $('#patient-form [name="diagnosis_text"]');
    const current = field.value.trim();
    field.value = current ? current + ". " + btn.dataset.text : btn.dataset.text;
    onFormChanged();
  });
  $("#save-btn").addEventListener("click", saveRecord);
  $$(".nav-btn").forEach((b) => b.addEventListener("click", () => switchView(b.dataset.view)));
  $("#back-to-list").addEventListener("click", () => switchView("list"));
  $("#search-input").addEventListener("input", () => {
    clearTimeout(window._searchTimer);
    window._searchTimer = setTimeout(loadRecords, 300);
  });
  $("#list-filters").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    $$("#list-filters button").forEach((b) => b.classList.remove("on"));
    btn.classList.add("on");
    listFilter = btn.dataset.filter;
    loadRecords();
  });
  const doctorInput = $("#doctor-name");
  doctorInput.value = localStorage.getItem("doctor") || "";
  doctorInput.addEventListener("change", () => {
    localStorage.setItem("doctor", doctorInput.value.trim());
    toast("Подпись врача сохранена");
  });
  $("#result-modal").addEventListener("click", (e) => {
    if (e.target.id === "result-modal") $("#result-modal").classList.add("hidden");
  });

  const draft = localStorage.getItem("draft");
  if (draft) {
    try {
      const p = JSON.parse(draft);
      if (Object.values(p).some((v) => v !== null && v !== "" && !(Array.isArray(v) && !v.length))) {
        fillForm(p);
        toast("Восстановлен черновик");
      }
    } catch (e) {}
  }

  window.addEventListener("online", () => { updateOfflineBanner(); flushOutbox(); });
  window.addEventListener("offline", updateOfflineBanner);
  updateOfflineBanner();
  flushOutbox();

  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js");
}

init();

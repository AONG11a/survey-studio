/* Survey Studio — builder.js
   Loads questions, renders the list, handles add/edit/delete, drag-reorder,
   per-option inputs with an "add option" button, and a LIVE PREVIEW of how the
   question will look to respondents. Talks to the JSON API in builder.py.
*/
(function () {
  "use strict";

  var FORM_ID = window.FORM_ID;
  var CSRF = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";

  var OPTION_TYPES = ["multiple", "checkbox", "dropdown"];
  var TYPE_LABELS = {
    short: "คำตอบสั้น", paragraph: "ย่อหน้า", multiple: "ปรนัย (เลือก 1)",
    checkbox: "เลือกได้หลายข้อ", dropdown: "ดรอปดาวน์", scale: "แบบประมาณค่า",
    date: "วันที่", time: "เวลา", section: "แบ่งส่วน (Section)"
  };

  var listEl = document.getElementById("questionList");
  var panel = document.getElementById("editPanel");
  var form = document.getElementById("questionForm");
  var panelTitle = document.getElementById("editPanelTitle");
  var typeSel = document.getElementById("qType");
  var optionsGroup = document.getElementById("optionsGroup");
  var optionsList = document.getElementById("optionsList");
  var scaleGroup = document.getElementById("scaleGroup");
  var previewBox = document.getElementById("previewBox");

  var questions = [];
  var editingId = null;

  // ---- API helper ---------------------------------------------------------
  function api(method, url, body) {
    return fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
      credentials: "same-origin",
      body: body ? JSON.stringify(body) : undefined
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
        return data;
      });
    });
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ---- Question list render ----------------------------------------------
  function render() {
    if (!questions.length) {
      listEl.innerHTML = '<div class="loading-skeleton">ยังไม่มีคำถาม — กด “เพิ่มคำถาม” เพื่อเริ่ม</div>';
      return;
    }
    listEl.innerHTML = "";
    questions.forEach(function (q) { listEl.appendChild(renderItem(q)); });
  }

  function renderItem(q) {
    var el = document.createElement("div");
    el.className = "q-item" + (q.type === "section" ? " section-item" : "");
    if (q.id === editingId) el.className += " editing";
    el.setAttribute("draggable", "true");
    el.dataset.qid = q.id;

    var sub = q.type === "section"
      ? '<span class="q-type-tag">Section</span>'
      : '<span class="q-type-tag">' + esc(TYPE_LABELS[q.type] || q.type) + "</span>" +
        (q.required ? '<span style="color:var(--red)">บังคับตอบ</span>' : "");

    var opts = "";
    if (OPTION_TYPES.indexOf(q.type) > -1 && q.options && q.options.length) {
      opts = '<div class="q-opts-preview">ตัวเลือก: ' +
        q.options.slice(0, 6).map(esc).join(" · ") +
        (q.options.length > 6 ? " …" : "") + "</div>";
    } else if (q.type === "scale") {
      opts = '<div class="q-opts-preview">ช่วง ' + q.scale_min + "–" + q.scale_max + "</div>";
    }

    el.innerHTML =
      '<div class="q-handle" title="ลากเพื่อจัดลำดับ">⋮⋮</div>' +
      '<div class="q-body">' +
        '<div class="q-text">' + esc(q.text) +
          (q.required && q.type !== "section" ? '<span class="req-star">*</span>' : "") + "</div>" +
        '<div class="q-sub">' + sub + "</div>" +
        (q.help_text ? '<div class="q-opts-preview">' + esc(q.help_text) + "</div>" : "") +
        opts +
      "</div>" +
      '<div class="q-actions">' +
        '<button class="icon-btn" data-act="edit" title="แก้ไข">✎</button>' +
        '<button class="icon-btn" data-act="dup" title="ทำซ้ำ">⧉</button>' +
        '<button class="icon-btn danger" data-act="del" title="ลบ">🗑</button>' +
      "</div>";

    el.querySelector('[data-act="edit"]').addEventListener("click", function () { openEdit(q); });
    el.querySelector('[data-act="del"]').addEventListener("click", function () { removeQuestion(q); });
    el.querySelector('[data-act="dup"]').addEventListener("click", function () { duplicate(q); });

    el.addEventListener("dragstart", onDragStart);
    el.addEventListener("dragover", onDragOver);
    el.addEventListener("dragleave", onDragLeave);
    el.addEventListener("drop", onDrop);
    el.addEventListener("dragend", onDragEnd);
    return el;
  }

  // ---- Drag & drop reorder ------------------------------------------------
  var dragEl = null;
  function onDragStart(e) { dragEl = this; this.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; try { e.dataTransfer.setData("text/plain", this.dataset.qid); } catch (_) {} }
  function onDragOver(e) { e.preventDefault(); if (this !== dragEl) this.classList.add("drag-over"); e.dataTransfer.dropEffect = "move"; }
  function onDragLeave() { this.classList.remove("drag-over"); }
  function onDrop(e) {
    e.preventDefault(); this.classList.remove("drag-over");
    if (!dragEl || this === dragEl) return;
    var nodes = Array.prototype.slice.call(listEl.children);
    var from = nodes.indexOf(dragEl), to = nodes.indexOf(this);
    if (from < 0 || to < 0) return;
    if (from < to) listEl.insertBefore(dragEl, this.nextSibling);
    else listEl.insertBefore(dragEl, this);
    persistOrder();
  }
  function onDragEnd() { this.classList.remove("dragging"); dragEl = null; }
  function persistOrder() {
    var order = Array.prototype.map.call(listEl.children, function (n) { return +n.dataset.qid; });
    questions.sort(function (a, b) { return order.indexOf(a.id) - order.indexOf(b.id); });
    api("POST", "/api/forms/" + FORM_ID + "/reorder", { order: order })
      .catch(function (err) { alert("จัดลำดับไม่สำเร็จ: " + err.message); load(); });
  }

  // ---- Options: one input per option + add/remove -------------------------
  function optionBullet() {
    var t = typeSel.value;
    return t === "checkbox" ? "▢" : (t === "dropdown" ? "▾" : "◯");
  }

  function addOptionRow(value, focusIt) {
    var row = document.createElement("div");
    row.className = "opt-row";
    row.innerHTML =
      '<span class="opt-bullet">' + optionBullet() + "</span>" +
      '<input type="text" class="opt-input" value="' + esc(value || "") + '" placeholder="พิมพ์ตัวเลือก">' +
      '<button type="button" class="opt-del" title="ลบตัวเลือก">×</button>';
    row.querySelector(".opt-del").addEventListener("click", function () {
      row.remove();
      if (!optionsList.children.length) addOptionRow("");
      renderPreview();
    });
    optionsList.appendChild(row);
    if (focusIt) row.querySelector(".opt-input").focus();
  }

  function renderOptionInputs(options) {
    optionsList.innerHTML = "";
    var arr = (options && options.length) ? options : ["", ""]; // seed 2 for new
    arr.forEach(function (o) { addOptionRow(o); });
  }

  function collectOptions() {
    return Array.prototype.map.call(
      optionsList.querySelectorAll(".opt-input"),
      function (i) { return i.value.trim(); }
    ).filter(Boolean);
  }

  function updateBullets() {
    var b = optionBullet();
    optionsList.querySelectorAll(".opt-bullet").forEach(function (e) { e.textContent = b; });
  }

  // ---- Live preview (how respondents will see it) -------------------------
  function renderPreview() {
    var t = typeSel.value;
    var text = form.text.value.trim();
    var required = form.required.checked;

    if (t === "section") {
      previewBox.innerHTML = '<div class="section-divider"><span>' +
        esc(text || "ชื่อส่วน") + "</span></div>";
      return;
    }

    var html = '<div class="respond-q">';
    html += '<div class="respond-q-label">' + esc(text || "(คำถามของคุณ)") +
      (required ? ' <span class="req-star">*</span>' : "") + "</div>";
    var help = form.help_text.value.trim();
    if (help) html += '<p class="respond-q-help">' + esc(help) + "</p>";

    if (t === "short") {
      html += '<input type="text" disabled placeholder="ข้อความคำตอบสั้น">';
    } else if (t === "paragraph") {
      html += '<textarea rows="2" disabled placeholder="ข้อความคำตอบแบบยาว"></textarea>';
    } else if (t === "multiple" || t === "checkbox") {
      var opts = collectOptions();
      if (!opts.length) html += '<p class="muted small">— ยังไม่ได้ใส่ตัวเลือก —</p>';
      var inp = t === "checkbox" ? "checkbox" : "radio";
      opts.forEach(function (o) {
        html += '<label class="respond-option"><input type="' + inp + '" disabled> <span>' + esc(o) + "</span></label>";
      });
    } else if (t === "dropdown") {
      var dopts = collectOptions();
      html += '<select disabled><option>— เลือก —</option>' +
        dopts.map(function (o) { return "<option>" + esc(o) + "</option>"; }).join("") + "</select>";
    } else if (t === "scale") {
      var mn = parseInt(form.scale_min.value, 10); if (isNaN(mn)) mn = 1;
      var mx = parseInt(form.scale_max.value, 10); if (isNaN(mx)) mx = 5;
      if (mx <= mn) mx = mn + 1;
      if (mx - mn > 20) mx = mn + 20; // keep preview compact
      html += '<div class="respond-scale">';
      var lo = form.scale_label_low.value.trim(), hi = form.scale_label_high.value.trim();
      if (lo) html += '<span class="scale-label">' + esc(lo) + "</span>";
      for (var i = mn; i <= mx; i++) {
        html += '<label class="scale-cell"><input type="radio" disabled><span>' + i + "</span></label>";
      }
      if (hi) html += '<span class="scale-label">' + esc(hi) + "</span>";
      html += "</div>";
    } else if (t === "date") {
      html += '<input type="date" disabled>';
    } else if (t === "time") {
      html += '<input type="time" disabled>';
    }
    html += "</div>";
    previewBox.innerHTML = html;
  }

  // ---- Edit panel ---------------------------------------------------------
  function syncTypeUI() {
    var t = typeSel.value;
    var isOpt = OPTION_TYPES.indexOf(t) > -1;
    optionsGroup.hidden = !isOpt;
    scaleGroup.hidden = t !== "scale";

    var reqRow = form.querySelector(".checkbox-row");
    if (reqRow) reqRow.style.display = (t === "section") ? "none" : "";
    var textInput = form.querySelector('input[name="text"]');
    if (textInput) textInput.placeholder = (t === "section") ? "ชื่อส่วน (Section)" : "พิมพ์คำถามที่นี่";

    if (isOpt) {
      if (!optionsList.children.length) renderOptionInputs(null); // seed 2 empty
      updateBullets();
    }
    renderPreview();
  }

  function openEdit(q) {
    editingId = q ? q.id : null;
    panelTitle.textContent = q ? "แก้ไขคำถาม" : "เพิ่มคำถาม";
    form.qid.value = q ? q.id : "";
    form.text.value = q ? q.text : "";
    typeSel.value = q ? q.type : "multiple";
    form.help_text.value = q ? (q.help_text || "") : "";
    form.scale_min.value = q ? (q.scale_min || 1) : 1;
    form.scale_max.value = q ? (q.scale_max || 5) : 5;
    form.scale_label_low.value = q ? (q.scale_label_low || "") : "";
    form.scale_label_high.value = q ? (q.scale_label_high || "") : "";
    form.required.checked = q ? !!q.required : false;

    // options
    if (q && OPTION_TYPES.indexOf(q.type) > -1) renderOptionInputs(q.options);
    else optionsList.innerHTML = "";

    syncTypeUI();
    panel.hidden = false;
    render();
    form.text.focus();
  }

  function closeEdit() { panel.hidden = true; editingId = null; render(); }

  function collect() {
    var t = typeSel.value;
    var payload = {
      type: t,
      text: form.text.value.trim(),
      help_text: form.help_text.value.trim(),
      required: form.required.checked
    };
    if (OPTION_TYPES.indexOf(t) > -1) payload.options = collectOptions();
    if (t === "scale") {
      payload.scale_min = parseInt(form.scale_min.value, 10);
      payload.scale_max = parseInt(form.scale_max.value, 10);
      payload.scale_label_low = form.scale_label_low.value.trim();
      payload.scale_label_high = form.scale_label_high.value.trim();
    }
    return payload;
  }

  function validateLocal(p) {
    if (p.type !== "section" && !p.text) return "กรุณากรอกข้อความคำถาม";
    if (OPTION_TYPES.indexOf(p.type) > -1 && (!p.options || p.options.length < 2))
      return "ต้องมีตัวเลือกอย่างน้อย 2 ตัว (กด “+ เพิ่มตัวเลือก” หรือกรอกช่องที่ว่างให้ครบ)";
    if (p.type === "scale") {
      if (isNaN(p.scale_min) || isNaN(p.scale_max)) return "ค่า scale ต้องเป็นตัวเลข";
      if (p.scale_min >= p.scale_max) return "ค่าต่ำสุดต้องน้อยกว่าค่าสูงสุด";
    }
    return null;
  }

  function save(e) {
    e.preventDefault();
    var payload = collect();
    var localErr = validateLocal(payload);
    if (localErr) { alert(localErr); return; }

    var saveBtn = document.getElementById("btnSaveQuestion");
    saveBtn.disabled = true;
    var p = editingId
      ? api("PUT", "/api/forms/" + FORM_ID + "/questions/" + editingId, payload)
      : api("POST", "/api/forms/" + FORM_ID + "/questions", payload);
    p.then(function () { return load(); })
      .then(function () { closeEdit(); })
      .catch(function (err) { alert("บันทึกไม่สำเร็จ: " + err.message); })
      .then(function () { saveBtn.disabled = false; });
  }

  function removeQuestion(q) {
    if (!confirm("ลบคำถามนี้? คำตอบเดิมที่เกี่ยวข้องจะถูกลบด้วย")) return;
    api("DELETE", "/api/forms/" + FORM_ID + "/questions/" + q.id)
      .then(load).catch(function (err) { alert("ลบไม่สำเร็จ: " + err.message); });
  }

  function duplicate(q) {
    api("POST", "/api/forms/" + FORM_ID + "/questions", {
      type: q.type, text: q.text, help_text: q.help_text, required: q.required,
      options: q.options, scale_min: q.scale_min, scale_max: q.scale_max,
      scale_label_low: q.scale_label_low, scale_label_high: q.scale_label_high
    }).then(load).catch(function (err) { alert("ทำซ้ำไม่สำเร็จ: " + err.message); });
  }

  // ---- Toggle open/closed -------------------------------------------------
  function initToggle() {
    var btn = document.getElementById("btnToggleActive");
    if (!btn) return;
    btn.addEventListener("click", function () {
      btn.disabled = true;
      fetch("/forms/" + FORM_ID + "/toggle-active", {
        method: "POST", headers: { "X-CSRFToken": CSRF }, credentials: "same-origin"
      }).then(function (r) { return r.json(); })
        .then(function (d) { btn.textContent = d.is_active ? "ปิดรับคำตอบ" : "เปิดรับคำตอบ"; })
        .catch(function () { alert("เปลี่ยนสถานะไม่สำเร็จ"); })
        .then(function () { btn.disabled = false; });
    });
  }

  // ---- Load ---------------------------------------------------------------
  function load() {
    return api("GET", "/api/forms/" + FORM_ID + "/questions")
      .then(function (d) { questions = d.questions || []; render(); })
      .catch(function (err) {
        listEl.innerHTML = '<div class="loading-skeleton">โหลดคำถามไม่สำเร็จ: ' + esc(err.message) + "</div>";
      });
  }

  // ---- Wire up ------------------------------------------------------------
  document.getElementById("btnAddQuestion").addEventListener("click", function () { openEdit(null); });
  document.getElementById("btnCloseEdit").addEventListener("click", closeEdit);
  document.getElementById("btnCancelEdit").addEventListener("click", closeEdit);
  document.getElementById("btnAddOption").addEventListener("click", function () { addOptionRow("", true); renderPreview(); });

  typeSel.addEventListener("change", syncTypeUI);
  form.addEventListener("submit", save);

  // live-preview triggers
  optionsList.addEventListener("input", renderPreview);
  ["text", "help_text", "scale_min", "scale_max", "scale_label_low", "scale_label_high"].forEach(function (name) {
    var f = form.querySelector('[name="' + name + '"]');
    if (f) f.addEventListener("input", renderPreview);
  });
  form.required.addEventListener("change", renderPreview);

  initToggle();
  load();
})();

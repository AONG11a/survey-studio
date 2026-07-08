/* Survey Studio — dashboard.js
   Fetches analytics + responses, renders KPIs and per-question charts with
   Chart.js, drives the individual-response viewer and date filters, and keeps
   everything live via Socket.IO (room form_<id>, owner-only on the server).
*/
(function () {
  "use strict";

  var FORM_ID = window.FORM_ID;
  var PALETTE = ["#4f46e5", "#0ea5e9", "#22c55e", "#f59e0b", "#ef4444",
    "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#64748b",
    "#84cc16", "#06b6d4"];

  var charts = {};            // id -> Chart instance (per-question + trend)
  var responses = [];         // individual-view cache
  var qOrder = [];            // [{id, text, type}] in form order
  var indIndex = 0;
  var refreshTimer = null;

  // ---- helpers ------------------------------------------------------------
  function el(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function color(i) { return PALETTE[i % PALETTE.length]; }

  function filterQS() {
    var f = el("filterFrom").value, t = el("filterTo").value;
    var p = [];
    if (f) p.push("from=" + encodeURIComponent(f));
    if (t) p.push("to=" + encodeURIComponent(t));
    return p.length ? "?" + p.join("&") : "";
  }

  function getJSON(url) {
    return fetch(url, { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function destroyChart(id) {
    if (charts[id]) { charts[id].destroy(); delete charts[id]; }
  }

  // ========================================================================
  // Analytics (overview + per-question)
  // ========================================================================
  function loadAnalytics() {
    return getJSON("/api/forms/" + FORM_ID + "/analytics" + filterQS())
      .then(function (d) {
        el("kpiTotal").textContent = d.total;
        el("kpiCompletion").textContent = d.completion_rate + "%";
        qOrder = (d.questions || []).map(function (q) {
          return { id: q.question_id, text: q.text, type: q.type };
        });
        renderTrend(d.trend || []);
        renderQuestions(d.questions || []);
      })
      .catch(function (err) {
        el("dashQuestions").innerHTML =
          '<div class="no-data">โหลดข้อมูลไม่สำเร็จ: ' + esc(err.message) + "</div>";
      });
  }

  function renderTrend(trend) {
    destroyChart("trendChart");
    var ctx = el("trendChart");
    if (!ctx) return;
    charts.trendChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: trend.map(function (t) { return t.date; }),
        datasets: [{
          data: trend.map(function (t) { return t.count; }),
          borderColor: "#4f46e5", backgroundColor: "rgba(79,70,229,.12)",
          fill: true, tension: .3, pointRadius: 3, borderWidth: 2
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
  }

  function renderQuestions(list) {
    var host = el("dashQuestions");
    host.innerHTML = "";
    if (!list.length) {
      host.innerHTML = '<div class="no-data">ยังไม่มีคำถามในฟอร์มนี้</div>';
      return;
    }
    list.forEach(function (q, i) {
      host.appendChild(buildQuestionCard(q, i));
    });
  }

  function cardShell(q, bodyHtml) {
    var card = document.createElement("div");
    card.className = "dash-q-card";
    card.innerHTML =
      '<div class="dash-q-head"><div class="dash-q-title">' + esc(q.text) + "</div></div>" +
      '<div class="dash-q-meta">' + esc(typeLabel(q.type)) +
        " · " + (q.answer_count || 0) + " คำตอบ</div>" + bodyHtml;
    return card;
  }

  function typeLabel(t) {
    return ({
      short: "คำตอบสั้น", paragraph: "ย่อหน้า", multiple: "ปรนัย",
      checkbox: "เลือกหลายข้อ", dropdown: "ดรอปดาวน์", scale: "แบบประมาณค่า",
      date: "วันที่", time: "เวลา"
    })[t] || t;
  }

  function buildQuestionCard(q, idx) {
    var chartId = "chart_q_" + q.question_id;

    if (q.type === "multiple" || q.type === "dropdown") {
      var card = cardShell(q, '<div class="chart-wrap"><canvas id="' + chartId + '"></canvas></div>');
      queueChart(chartId, function (ctx) { return pieChart(ctx, q); });
      return card;
    }
    if (q.type === "checkbox") {
      var c2 = cardShell(q,
        '<div class="chart-wrap"><canvas id="' + chartId + '"></canvas></div>' +
        '<p class="small muted">' + esc(q.note || "") + "</p>");
      queueChart(chartId, function (ctx) { return barChart(ctx, Object.keys(q.counts), Object.values(q.counts), q); });
      return c2;
    }
    if (q.type === "scale") {
      var stats =
        '<div class="stat-row">' +
          '<div class="stat-pill"><div class="n">' + (q.mean == null ? "–" : q.mean) + '</div><div class="l">ค่าเฉลี่ย</div></div>' +
          '<div class="stat-pill"><div class="n">' + (q.median == null ? "–" : q.median) + '</div><div class="l">มัธยฐาน</div></div>' +
          '<div class="stat-pill"><div class="n">' + (q.count || 0) + '</div><div class="l">จำนวนตอบ</div></div>' +
        "</div>";
      var c3 = cardShell(q, stats + '<div class="chart-wrap short"><canvas id="' + chartId + '"></canvas></div>');
      var labels = Object.keys(q.distribution || {});
      var vals = Object.values(q.distribution || {});
      queueChart(chartId, function (ctx) { return barChart(ctx, labels, vals, q, "#4f46e5"); });
      return c3;
    }
    if (q.type === "short" || q.type === "paragraph") {
      var wf = (q.word_freq || []).map(function (p) {
        return '<span class="wf-chip">' + esc(p[0]) + '<span class="c">' + p[1] + "</span></span>";
      }).join("");
      var texts = (q.responses || []);
      var list = texts.length
        ? texts.map(function (t) { return '<div class="text-answer">' + esc(t) + "</div>"; }).join("")
        : '<div class="no-data">ยังไม่มีคำตอบ</div>';
      var body =
        (wf ? '<div class="wordfreq">' + wf + "</div>" : "") +
        '<div class="text-answers">' + list + "</div>";
      return cardShell(q, body);
    }
    if (q.type === "date") {
      var c4 = cardShell(q, '<div class="chart-wrap short"><canvas id="' + chartId + '"></canvas></div>');
      queueChart(chartId, function (ctx) {
        return barChart(ctx, Object.keys(q.distribution || {}), Object.values(q.distribution || {}), q, "#0ea5e9");
      });
      return c4;
    }
    if (q.type === "time") {
      var byh = q.by_hour || {};
      var labels2 = Object.keys(byh).map(function (h) { return h + ":00"; });
      var c5 = cardShell(q, '<div class="chart-wrap short"><canvas id="' + chartId + '"></canvas></div>');
      queueChart(chartId, function (ctx) { return barChart(ctx, labels2, Object.values(byh), q, "#14b8a6"); });
      return c5;
    }
    return cardShell(q, '<div class="no-data">—</div>');
  }

  // Charts must be created after the canvas is in the DOM.
  var chartQueue = [];
  function queueChart(id, factory) { chartQueue.push([id, factory]); }
  function flushCharts() {
    chartQueue.forEach(function (pair) {
      var ctx = el(pair[0]);
      if (!ctx) return;
      destroyChart(pair[0]);
      charts[pair[0]] = pair[1](ctx);
    });
    chartQueue = [];
  }

  function pieChart(ctx, q) {
    var labels = q.options || Object.keys(q.counts);
    var data = labels.map(function (o) { return (q.counts || {})[o] || 0; });
    return new Chart(ctx, {
      type: "pie",
      data: { labels: labels, datasets: [{ data: data, backgroundColor: labels.map(function (_, i) { return color(i); }) }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: "right" },
          tooltip: { callbacks: { label: function (c) {
            var pct = (q.percent || {})[c.label];
            return " " + c.label + ": " + c.parsed + (pct != null ? " (" + pct + "%)" : "");
          } } }
        }
      }
    });
  }

  function barChart(ctx, labels, data, q, fixed) {
    return new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: fixed || labels.map(function (_, i) { return color(i); })
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: function (c) {
            var pct = q && q.percent ? q.percent[c.label] : null;
            return " " + c.parsed + (pct != null ? " (" + pct + "%)" : "");
          } } }
        },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
  }

  // ========================================================================
  // Individual responses
  // ========================================================================
  function loadResponses() {
    return getJSON("/api/forms/" + FORM_ID + "/responses" + filterQS())
      .then(function (d) {
        responses = d.responses || [];
        if (indIndex >= responses.length) indIndex = Math.max(0, responses.length - 1);
        renderIndividual();
      });
  }

  function renderIndividual() {
    var card = el("indCard");
    var idxLabel = el("respIndex");
    if (!responses.length) {
      card.innerHTML = '<p class="no-data">ยังไม่มีคำตอบ</p>';
      idxLabel.textContent = "0 / 0";
      return;
    }
    var r = responses[indIndex];
    idxLabel.textContent = (indIndex + 1) + " / " + responses.length;

    var when = new Date(r.submitted_at);
    var fields = qOrder.map(function (q) {
      var v = r.answers[q.id];
      var display, empty = false;
      if (v == null || v === "" || (Array.isArray(v) && !v.length)) { display = "(ไม่ได้ตอบ)"; empty = true; }
      else if (Array.isArray(v)) display = v.map(esc).join(", ");
      else display = esc(v);
      return '<div class="ind-field"><div class="ind-q">' + esc(q.text) + "</div>" +
             '<div class="ind-a' + (empty ? " empty" : "") + '">' + display + "</div></div>";
    }).join("");

    card.innerHTML =
      '<div class="ind-meta">ส่งเมื่อ ' + when.toLocaleString("th-TH") +
        " · รหัสคำตอบ #" + r.id + "</div>" + fields;
  }

  // ========================================================================
  // Refresh orchestration
  // ========================================================================
  function refreshAll() {
    return Promise.all([loadAnalytics().then(flushCharts), loadResponses()]);
  }

  function scheduleRefresh() {
    // debounce bursts of new_response events
    if (refreshTimer) clearTimeout(refreshTimer);
    refreshTimer = setTimeout(function () { refreshAll(); }, 400);
  }

  // ========================================================================
  // Real-time (Socket.IO)
  // ========================================================================
  function setRT(state, text) {
    var dot = document.querySelector(".rt-dot");
    dot.className = "rt-dot " + (
      state === "live" ? "rt-dot-live" :
      state === "off" ? "rt-dot-off" : "rt-dot-connecting");
    el("rtText").textContent = text;
  }

  function toast(msg) {
    var host = document.querySelector(".toast-host");
    if (!host) { host = document.createElement("div"); host.className = "toast-host"; document.body.appendChild(host); }
    var t = document.createElement("div");
    t.className = "toast"; t.textContent = msg;
    host.appendChild(t);
    setTimeout(function () { t.remove(); }, 3200);
  }

  function initSocket() {
    if (typeof io === "undefined") { setRT("off", "โหมดเรียลไทม์ไม่พร้อมใช้งาน"); return; }
    var socket = io({ transports: ["websocket", "polling"] });

    socket.on("connect", function () {
      socket.emit("join_form", { form_id: FORM_ID }, function (ack) {
        if (ack && ack.ok) setRT("live", "อัปเดตแบบเรียลไทม์ทำงานอยู่");
        else setRT("off", "ไม่มีสิทธิ์รับข้อมูลเรียลไทม์");
      });
    });
    socket.on("disconnect", function () { setRT("connecting", "การเชื่อมต่อหลุด กำลังเชื่อมต่อใหม่…"); });
    socket.on("connect_error", function () { setRT("off", "เชื่อมต่อเรียลไทม์ไม่สำเร็จ"); });

    socket.on("new_response", function () {
      toast("มีคำตอบใหม่เข้ามา");
      scheduleRefresh();
    });
  }

  // ========================================================================
  // Filters + wire-up
  // ========================================================================
  el("btnApplyFilter").addEventListener("click", refreshAll);
  el("btnClearFilter").addEventListener("click", function () {
    el("filterFrom").value = ""; el("filterTo").value = "";
    refreshAll();
  });
  el("btnPrevResp").addEventListener("click", function () {
    if (indIndex > 0) { indIndex--; renderIndividual(); }
  });
  el("btnNextResp").addEventListener("click", function () {
    if (indIndex < responses.length - 1) { indIndex++; renderIndividual(); }
  });

  setRT("connecting", "กำลังเชื่อมต่อแบบเรียลไทม์…");
  refreshAll();
  initSocket();
})();

/* Survey Studio — respond.js
   Public survey page. Collects answers by question type, validates required
   fields client-side, then POSTs JSON to /api/submit/<form_id>.
   (The submit endpoint is CSRF-exempt and re-validates everything server-side.)
*/
(function () {
  "use strict";

  var form = document.getElementById("respondForm");
  if (!form) return;
  var formId = form.getAttribute("data-form-id");
  var submitBtn = form.querySelector(".btn-submit");

  function qEls() {
    return Array.prototype.slice.call(form.querySelectorAll(".respond-q"));
  }

  function showError(qid, msg) {
    var box = form.querySelector('[data-err-for="' + qid + '"]');
    var wrap = form.querySelector('.respond-q[data-qid="' + qid + '"]');
    if (box) box.textContent = msg || "";
    if (wrap) wrap.classList.toggle("invalid", !!msg);
  }

  function clearErrors() {
    qEls().forEach(function (el) {
      el.classList.remove("invalid");
      var box = el.querySelector(".respond-error");
      if (box) box.textContent = "";
    });
  }

  // Read one question's value out of the DOM.
  function readValue(el) {
    var qid = el.dataset.qid, type = el.dataset.type;
    if (type === "checkbox") {
      return Array.prototype.slice
        .call(el.querySelectorAll('input[type="checkbox"]:checked'))
        .map(function (i) { return i.value; });
    }
    if (type === "multiple" || type === "scale") {
      var r = el.querySelector('input[type="radio"]:checked');
      return r ? r.value : "";
    }
    if (type === "dropdown") {
      var sel = el.querySelector("select");
      return sel ? sel.value : "";
    }
    var field = el.querySelector("input, textarea");
    return field ? field.value.trim() : "";
  }

  function isEmpty(v) {
    return v == null || v === "" || (Array.isArray(v) && v.length === 0);
  }

  function collect() {
    var answers = {};
    qEls().forEach(function (el) {
      answers[el.dataset.qid] = readValue(el);
    });
    return answers;
  }

  // Client-side required check (server re-checks anyway).
  function validate(answers) {
    var firstBad = null;
    qEls().forEach(function (el) {
      var qid = el.dataset.qid;
      var required = el.dataset.required === "true";
      if (required && isEmpty(answers[qid])) {
        showError(qid, "กรุณาตอบคำถามนี้");
        if (!firstBad) firstBad = el;
      }
    });
    return firstBad;
  }

  function showThanks() {
    var wrap = document.querySelector(".respond-wrap");
    wrap.innerHTML =
      '<div class="respond-card respond-thanks">' +
        '<div class="thanks-check">✓</div>' +
        "<h1>ส่งคำตอบเรียบร้อยแล้ว</h1>" +
        '<p class="muted">ขอบคุณที่สละเวลาตอบแบบสอบถามนี้</p>' +
      "</div>";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    clearErrors();
    var answers = collect();

    var bad = validate(answers);
    if (bad) {
      bad.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    submitBtn.disabled = true;
    var oldText = submitBtn.textContent;
    submitBtn.textContent = "กำลังส่ง…";

    fetch("/api/submit/" + formId, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ answers: answers })
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        return { status: r.status, data: data };
      });
    }).then(function (res) {
      if (res.status === 200 && res.data.ok) { showThanks(); return; }

      if (res.status === 400 && res.data.details) {
        (res.data.details || []).forEach(function (d) {
          showError(d.question_id, d.error);
        });
        var f = form.querySelector(".respond-q.invalid");
        if (f) f.scrollIntoView({ behavior: "smooth", block: "center" });
      } else if (res.status === 409) {
        alert("คุณได้ตอบแบบสอบถามนี้ไปแล้ว");
        showThanks();
      } else if (res.status === 403) {
        alert("แบบสอบถามนี้ปิดรับคำตอบแล้ว");
      } else if (res.status === 429) {
        alert("ส่งคำตอบถี่เกินไป กรุณารอสักครู่แล้วลองใหม่");
      } else if (res.status === 413) {
        alert("ข้อมูลที่ส่งมีขนาดใหญ่เกินไป");
      } else {
        alert("ส่งคำตอบไม่สำเร็จ กรุณาลองใหม่");
      }
      submitBtn.disabled = false;
      submitBtn.textContent = oldText;
    }).catch(function () {
      alert("เชื่อมต่อไม่สำเร็จ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่");
      submitBtn.disabled = false;
      submitBtn.textContent = oldText;
    });
  });
})();

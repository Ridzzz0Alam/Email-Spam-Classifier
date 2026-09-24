"use strict";

const SAMPLES = {
  stock: `Subject: Hot news alert - TMXO set to explode

Special situation alert! Our analysts have identified an aggressive buy with a 5 day target price of $2.40. Trimax is a provider of broadband over power line technology and is about to release breaking news.

Add TMXO to your radar watch list today. Investors who get in before the announcement stand to make huge profits. This is a sector to be in.

All material herein was prepared by us based upon information believed to be reliable. We have been compensated for this report.`,

  pharmacy: `Subject: Your order is ready - save up to 80%

Dear customer,

Canadian pharmacy online. Viagra, Cialis, Levitra, Ambien, Valium - all at the lowest prices. No prescription needed, discreet worldwide shipping.

Low dose and generic options available. Retail price $120, our price only $39. Limited time offer, order now and receive free pills with every purchase.

Click here to visit our website. To unsubscribe from our mailing list, reply with remove.`,

  colleague: `Subject: Re: code review for the parser changes

Hi Maria,

Thanks for sending the patch over. I went through it this morning and it mostly looks good. Two small things: the error handling in the tokenizer should probably log the line number, and I think the new unit tests miss the empty-input case.

Could we talk it through after the team meeting on Thursday? I'm free from 3pm. If that doesn't work, send me a time next week and I'll update the calendar invite.

Cheers,
Daniel`,

  obfuscated: `Subject: Y0ur 0rder is r3ady - s@ve up t0 80%

D3ar cust0mer,

C@nadian ph@rmacy 0nline. V1agra, C1alis, L3vitra - @ll at the l0west pr1ces. N0 prescr1ption n3eded, d1screet w0rldwide sh1pping.

L1mited t1me 0ffer, 0rder n0w and rec3ive fr33 p1lls with every purch@se.

Cl1ck h3re to v1sit 0ur w3bsite.`,
};

const $ = (id) => document.getElementById(id);
const els = {
  email: $("email"), classify: $("classify"), modelLine: $("model-line"),
  empty: $("empty"), error: $("error"), result: $("result"),
  verdictWord: $("verdict-word"), verdictProb: $("verdict-prob"),
  marker: $("marker"), equation: $("equation"), annotated: $("annotated"),
  coverage: $("coverage"), topSpam: $("top-spam"), topHam: $("top-ham"), tip: $("tip"),
};

const MAX_RENDER_CHARS = 20000;
const fmtSigned = (x, d = 2) => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(d);
const fmtInt = (n) => n.toLocaleString("en-US");

function fmtProb(p) {
  if (p > 0.9999) return "above 99.99%";
  if (p < 0.0001) return "below 0.01%";
  return (p * 100).toFixed(2) + "%";
}

// ---------- model details --------------------------------------------------------------
async function loadModelInfo() {
  try {
    const r = await fetch("/api/model");
    if (!r.ok) throw new Error(r.status);
    const m = await r.json();
    const acc = (m.metrics.accuracy * 100).toFixed(1);
    const prec = (m.metrics.precision_spam * 100).toFixed(2);
    els.modelLine.textContent =
      `Trained on ${fmtInt(m.n_train)} emails with ${fmtInt(m.n_features)} word and ` +
      `phrase features. On ${fmtInt(m.metrics.n_test)} held-out emails: ${acc}% accurate, ` +
      `and ${prec}% of emails it flags as spam really are spam.`;
  } catch {
    els.modelLine.textContent = "Model details unavailable. The API is not responding.";
  }
}

// ---------- classify -------------------------------------------------------------------
async function classify() {
  const text = els.email.value;
  if (!text.trim()) {
    showError("Paste an email into the box first, or pick one of the samples.");
    els.email.focus();
    return;
  }
  els.classify.disabled = true;
  els.classify.textContent = "Classifying…";
  try {
    const r = await fetch("/api/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, top_n: 10 }),
    });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      const detail = Array.isArray(body.detail)
        ? body.detail.map((d) => d.msg).join("; ")
        : body.detail || `The server answered with status ${r.status}.`;
      throw new Error(detail);
    }
    render(text, await r.json());
  } catch (err) {
    const offline = err instanceof TypeError;
    showError(offline
      ? "The classifier isn't reachable. Start the server with fastapi dev app/main.py and try again."
      : `The email couldn't be classified: ${err.message}`);
  } finally {
    els.classify.disabled = false;
    els.classify.textContent = "Classify email";
  }
}

function showError(msg) {
  els.empty.hidden = true;
  els.result.hidden = true;
  els.error.hidden = false;
  els.error.replaceChildren(Object.assign(document.createElement("p"), { textContent: msg }));
}

// ---------- render ---------------------------------------------------------------------
function render(text, res) {
  els.empty.hidden = true;
  els.error.hidden = true;
  els.result.hidden = false;

  const spam = res.label === "spam";
  els.verdictWord.textContent = spam ? "Spam" : "Not spam";
  els.verdictWord.className = "verdict-word " + (spam ? "is-spam" : "is-ham");
  els.verdictProb.textContent = `Probability of spam: ${fmtProb(res.p_spam)}`;

  // Symmetric log compression keeps +48 and +0.5 both readable on one track.
  const x = res.log_odds;
  const squash = Math.sign(x) * Math.log1p(Math.abs(x)) / Math.log1p(60);
  const pos = Math.min(97, Math.max(3, 50 + 47 * squash));
  els.marker.style.left = pos + "%";

  els.equation.replaceChildren();
  const eq = [
    [fmtSigned(res.prior_log_odds), " base rate  "],
    [fmtSigned(res.evidence), " from the words  =  "],
    [fmtSigned(res.log_odds), " log-odds"],
  ];
  for (const [num, label] of eq) {
    els.equation.append(Object.assign(document.createElement("strong"), { textContent: num }), label);
  }
  els.equation.append(
    x > 0 ? ". Above zero means spam." : ". Below zero means a real email.");

  annotate(text, res.word_scores);

  els.coverage.textContent = res.words_total === 0
    ? "After cleaning, nothing was left for the model to read, so the verdict is just the " +
      "base rate of spam in the training data."
    : `The model recognised ${fmtInt(res.words_recognised)} of the ${fmtInt(res.words_total)} ` +
      `words left after cleaning. Common words, numbers and words it never saw in training ` +
      `stay unshaded. Shading is relative to the strongest word in this email; hover or tap ` +
      `a word, or use the arrow keys, for its exact contribution.`;

  fillList(els.topSpam, res.top_spam, "No words pushed toward spam.");
  fillList(els.topHam, res.top_ham, "No words pushed toward a real email.");

  // On narrow screens the result sits below the textarea, off-screen.
  if (window.matchMedia("(max-width: 860px)").matches) {
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    els.result.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
  }
}

function annotate(text, scores) {
  const box = els.annotated;
  box.replaceChildren();
  box.scrollTop = 0;

  const shown = text.length > MAX_RENDER_CHARS ? text.slice(0, MAX_RENDER_CHARS) : text;
  const max = Math.max(0.05, ...Object.values(scores).map(Math.abs));
  const frag = document.createDocumentFragment();

  // URLs are stripped by the cleaner, so words inside them never reach the model.
  const urlRe = /(https?:\/\/\S+|www\.\S+|\S+@\S+\.\S+)/gi;
  for (const [i, seg] of shown.split(urlRe).entries()) {
    if (i % 2 === 1) {
      frag.append(Object.assign(document.createElement("span"), { className: "url", textContent: seg }));
      continue;
    }
    for (const piece of seg.split(/([A-Za-z]+)/)) {
      const s = /^[A-Za-z]+$/.test(piece) ? scores[piece.toLowerCase()] : undefined;
      if (s === undefined || s === 0) { frag.append(piece); continue; }
      const span = document.createElement("span");
      span.className = "w " + (s > 0 ? "s" : "h");
      span.style.setProperty("--w", Math.min(1, 0.15 + 0.85 * Math.abs(s) / max).toFixed(3));
      span.dataset.word = piece.toLowerCase();
      span.dataset.score = s;
      span.tabIndex = -1;  // focusable by arrow keys and taps, but not a tab stop
      span.textContent = piece;
      frag.append(span);
    }
  }
  if (shown.length < text.length) {
    frag.append(`\n\n[Showing the first ${fmtInt(MAX_RENDER_CHARS)} characters. The verdict used the whole email.]`);
  }
  box.append(frag);
}

function fillList(ol, items, emptyMsg) {
  ol.replaceChildren();
  if (!items.length) {
    ol.append(Object.assign(document.createElement("li"), { className: "none", textContent: emptyMsg }));
    return;
  }
  for (const it of items) {
    const li = document.createElement("li");
    li.append(
      Object.assign(document.createElement("span"), { className: "feat", textContent: it.feature }),
      Object.assign(document.createElement("span"), { className: "val", textContent: fmtSigned(it.contribution, 3) }),
    );
    ol.append(li);
  }
}

// ---------- tooltip --------------------------------------------------------------------
// Mouse: hover. Touch: tap a word. Keyboard: Tab into the email, then arrow keys move
// between shaded words (one tab stop, not hundreds), Escape hides the tip.
function showTip(w) {
  const s = parseFloat(w.dataset.score);
  els.tip.textContent =
    `“${w.dataset.word}” adds ${fmtSigned(s, 3)} log-odds toward ${s > 0 ? "spam" : "a real email"}, ` +
    `counting every time it appears and its share of any phrases.`;
  els.tip.hidden = false;
  w.setAttribute("aria-describedby", "tip");
  const r = w.getBoundingClientRect();
  const tw = els.tip.offsetWidth;
  els.tip.style.left = Math.min(window.innerWidth - tw - 8, Math.max(8, r.left + r.width / 2 - tw / 2)) + "px";
  els.tip.style.top = (r.top - els.tip.offsetHeight - 8 < 8 ? r.bottom + 8 : r.top - els.tip.offsetHeight - 8) + "px";
}

function hideTip() {
  els.tip.hidden = true;
  els.annotated.querySelector("[aria-describedby]")?.removeAttribute("aria-describedby");
}

els.annotated.addEventListener("mouseover", (e) => {
  const w = e.target.closest(".w");
  if (w) showTip(w);
});
els.annotated.addEventListener("mouseout", (e) => {
  if (e.target.closest(".w") && !e.target.closest(".w").matches(":focus")) hideTip();
});
els.annotated.addEventListener("click", (e) => {
  const w = e.target.closest(".w");
  if (w) { w.focus({ preventScroll: true }); showTip(w); }
});
els.annotated.addEventListener("focusin", (e) => {
  const w = e.target.closest(".w");
  if (w) showTip(w);
});
els.annotated.addEventListener("focusout", hideTip);
// Keep the tip on a keyboard-focused word as the box scrolls to it; otherwise hide it.
els.annotated.addEventListener("scroll", () => {
  const f = document.activeElement;
  if (f?.classList.contains("w") && els.annotated.contains(f)) showTip(f);
  else hideTip();
});

els.annotated.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { hideTip(); return; }
  const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key]
    ?? (e.key === "Home" ? -Infinity : e.key === "End" ? Infinity : 0);
  if (!step) return;
  const words = [...els.annotated.querySelectorAll(".w")];
  if (!words.length) return;
  e.preventDefault();
  const cur = words.indexOf(document.activeElement);
  const next = Number.isFinite(step)
    ? Math.min(words.length - 1, Math.max(0, cur === -1 ? 0 : cur + step))
    : (step > 0 ? words.length - 1 : 0);
  words[next].focus();
  words[next].scrollIntoView({ block: "nearest" });
});

// Tapping outside a word dismisses the tip on touch screens.
document.addEventListener("pointerdown", (e) => {
  if (!e.target.closest(".w")) hideTip();
});

// ---------- wiring ---------------------------------------------------------------------
els.classify.addEventListener("click", classify);
els.email.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); classify(); }
});
document.querySelectorAll("[data-sample]").forEach((b) =>
  b.addEventListener("click", () => {
    els.email.value = SAMPLES[b.dataset.sample];
    classify();
  }));

loadModelInfo();

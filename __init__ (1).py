:root {
  --paper: #F3F5F7;
  --sheet: #FFFFFF;
  --ink: #18202B;
  --muted: #5E6978;
  --rule: #D6DCE3;
  --spam: #C0392B;
  --ham: #2A5DB0;
  --focus: #2A5DB0;
  --tint: 42%;

  --serif: "Newsreader", "Iowan Old Style", "Palatino Linotype", Georgia, serif;
  --sans: "Public Sans", "Segoe UI", system-ui, -apple-system, sans-serif;

  --step--1: 0.8125rem;
  --step-0: 1rem;
  --step-1: 1.1875rem;
  --step-2: 1.5rem;
  --step-4: 2.75rem;

  color-scheme: light dark;
}

@media (prefers-color-scheme: dark) {
  :root {
    --paper: #121820;
    --sheet: #1B232E;
    --ink: #E6EBF1;
    --muted: #98A3B2;
    --rule: #2E3947;
    --spam: #F0776A;
    --ham: #7FA7EE;
    --focus: #7FA7EE;
    --tint: 58%;
  }
}

*, *::before, *::after { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 400 var(--step-0)/1.5 var(--sans);
  -webkit-font-smoothing: antialiased;
}

.visually-hidden {
  position: absolute; width: 1px; height: 1px; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap;
}

:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }

/* ---------- masthead ---------- */
.masthead {
  max-width: 76rem;
  margin: 0 auto;
  padding: 3rem 1.5rem 1.75rem;
}
.masthead h1 {
  margin: 0;
  font: 500 var(--step-4)/1.05 var(--serif);
  letter-spacing: -0.01em;
}
.lede {
  max-width: 38rem;
  margin: 0.75rem 0 0;
  font-size: var(--step-1);
  color: var(--muted);
}
.model-line {
  margin: 1rem 0 0;
  font-size: var(--step--1);
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

/* ---------- layout ---------- */
.bench {
  max-width: 76rem;
  margin: 0 auto;
  padding: 0 1.5rem 3rem;
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
  gap: 2.5rem;
  align-items: start;
}
@media (max-width: 860px) {
  .bench { grid-template-columns: 1fr; gap: 2rem; }
}

h2 {
  margin: 0 0 0.75rem;
  font: 600 var(--step-0)/1.3 var(--sans);
}

/* ---------- compose ---------- */
.compose { position: sticky; top: 1.5rem; }
@media (max-width: 860px) { .compose { position: static; } }

textarea {
  width: 100%;
  min-height: 22rem;
  resize: vertical;
  padding: 1rem 1.1rem;
  border: 1px solid var(--rule);
  border-radius: 6px;
  background: var(--sheet);
  color: var(--ink);
  font: 400 var(--step-0)/1.6 var(--serif);
}
textarea::placeholder { color: var(--muted); }

.samples { margin-top: 1rem; }
.samples-label { font-size: var(--step--1); color: var(--muted); }
.sample-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }

.chip {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--rule);
  border-radius: 999px;
  background: transparent;
  color: var(--ink);
  font: 500 var(--step--1)/1.2 var(--sans);
  cursor: pointer;
}
.chip:hover { border-color: var(--muted); }

.actions { display: flex; align-items: center; gap: 1rem; margin-top: 1.5rem; }
.primary {
  padding: 0.7rem 1.4rem;
  border: 0;
  border-radius: 6px;
  background: var(--ink);
  color: var(--paper);
  font: 600 var(--step-0)/1 var(--sans);
  cursor: pointer;
}
.primary:disabled { opacity: 0.55; cursor: progress; }
.hint { font-size: var(--step--1); color: var(--muted); }
@media (hover: none) { .hint { display: none; } }
kbd {
  font: inherit;
  padding: 0.05rem 0.35rem;
  border: 1px solid var(--rule);
  border-radius: 4px;
}

/* ---------- reading pane ---------- */
.empty, .error {
  padding: 2rem 1.5rem;
  border: 1px dashed var(--rule);
  border-radius: 6px;
  color: var(--muted);
  font: 400 var(--step-1)/1.55 var(--serif);
  max-width: 40rem;
}
.empty p, .error p { margin: 0; }
.error { border-style: solid; border-color: var(--spam); color: var(--ink); }
.error code { font-size: 0.9em; }

.verdict { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.25rem 1.25rem; }
.verdict-word {
  margin: 0;
  font: 600 var(--step-4)/1 var(--serif);
}
.verdict-word.is-spam { color: var(--spam); }
.verdict-word.is-ham { color: var(--ham); }
.verdict-prob {
  margin: 0;
  font-size: var(--step-1);
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

/* evidence balance: log-odds on a compressed symmetric scale */
.balance { margin: 1.5rem 0 1.75rem; }
.track {
  position: relative;
  height: 2.5rem;
  border-bottom: 1px solid var(--rule);
  background: linear-gradient(to right,
    color-mix(in srgb, var(--ham) 10%, transparent),
    transparent 50%,
    color-mix(in srgb, var(--spam) 10%, transparent));
  border-radius: 4px 4px 0 0;
}
.side {
  position: absolute; bottom: 0.45rem;
  font-size: var(--step--1); color: var(--muted);
}
.side-ham { left: 0.6rem; }
.side-spam { right: 0.6rem; }
.boundary {
  position: absolute; left: 50%; top: 0; bottom: 0;
  border-left: 1px dashed var(--muted);
}
.marker {
  position: absolute; bottom: -0.45rem; left: 50%;
  width: 0.9rem; height: 0.9rem;
  margin-left: -0.45rem;
  border-radius: 50%;
  background: var(--ink);
  border: 2px solid var(--sheet);
  transition: left 420ms cubic-bezier(.2, .8, .2, 1);
}
.equation {
  margin-top: 0.9rem;
  font-size: var(--step--1);
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.equation strong { color: var(--ink); font-weight: 600; }

/* the annotated email — the centrepiece */
.sheet {
  background: var(--sheet);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 1.75rem 2rem 1.25rem;
}
@media (max-width: 520px) { .sheet { padding: 1.25rem 1.1rem 1rem; } }

.sheet-body {
  max-width: 68ch;
  font: 400 var(--step-1)/1.75 var(--serif);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  max-height: 34rem;
  overflow-y: auto;
}
.w {
  --w: 0;
  border-radius: 3px;
  padding: 0.04em 0.06em;
  cursor: help;
}
.w.s { background: color-mix(in srgb, var(--spam) calc(var(--w) * var(--tint)), transparent); }
.w.h {
  background: color-mix(in srgb, var(--ham) calc(var(--w) * var(--tint)), transparent);
  text-decoration: underline dotted color-mix(in srgb, var(--ham) 70%, transparent);
  text-underline-offset: 0.2em;
}
.url { color: var(--muted); }

.sheet-note {
  margin: 1.25rem 0 0;
  padding-top: 0.9rem;
  border-top: 1px solid var(--rule);
  font-size: var(--step--1);
  color: var(--muted);
}

/* drivers */
.drivers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  margin-top: 2rem;
}
@media (max-width: 520px) { .drivers { grid-template-columns: 1fr; } }
.drivers h3 { margin: 0 0 0.6rem; font: 600 var(--step-0)/1.3 var(--sans); }
.driver-list { list-style: none; margin: 0; padding: 0; }
.driver-list li {
  display: flex; justify-content: space-between; gap: 1rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--rule);
  font-size: var(--step--1);
}
.driver-list .feat { font-family: var(--serif); font-size: var(--step-0); }
.driver-list .val { font-variant-numeric: tabular-nums; color: var(--muted); }
.driver-list.spam .val { color: var(--spam); }
.driver-list.ham .val { color: var(--ham); }
.driver-list .none { color: var(--muted); border-bottom: 0; }

/* tooltip */
.tip {
  position: fixed; z-index: 10;
  max-width: 16rem;
  padding: 0.45rem 0.65rem;
  border-radius: 4px;
  background: var(--ink);
  color: var(--paper);
  font: 400 var(--step--1)/1.35 var(--sans);
  pointer-events: none;
  font-variant-numeric: tabular-nums;
}

.colophon {
  max-width: 76rem;
  margin: 0 auto;
  padding: 1.5rem 1.5rem 3rem;
  border-top: 1px solid var(--rule);
  font-size: var(--step--1);
  color: var(--muted);
}
.colophon p { max-width: 60rem; margin: 0; }
.colophon a { color: inherit; }

@media (prefers-reduced-motion: reduce) {
  .marker { transition: none; }
}

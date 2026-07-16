# Design.md — Model Calibration & Reliability Dashboard

Built using the design-intelligence rules from the ui-ux-pro-max skill (priority-ordered: accessibility → touch/interaction → performance → style → layout → typography/color → animation → forms → nav → charts). Product type: analytics dashboard / data-viz tool, desktop-first (this is a portfolio artifact reviewed on laptops, not a mobile app).

## 1. Product type framing
This is a **single-purpose analytics dashboard**, not a general admin panel — one screen, one job: let a viewer judge whether a model's confidence scores are trustworthy, and see the before/after of a fix. Design should read as precise and technical, not decorative. Resist the temptation to over-style a portfolio piece — a reviewer evaluating an ML/data project rewards clarity over flourish.

## 2. Style selection
- **Style:** clean flat/minimalist with a data-density-first layout — no glassmorphism, neumorphism, or skeuomorphism. Those styles fight for attention against charts, which are the actual content here (Style Selection priority: match style to product type).
- **Rationale:** for chart-heavy technical tools, decoration reduces perceived rigor. A dashboard that looks like a fintech risk console (not a marketing page) signals the right register to a technical reviewer.

## 3. Color system
- Semantic tokens, not raw hex scattered through components:
  - `--color-raw`: neutral gray-blue — the uncorrected curve (de-emphasized, it's the "before")
  - `--color-platt`: one accent (e.g., teal)
  - `--color-isotonic`: a second, distinguishable accent (e.g., amber) — chosen for sufficient hue distance from teal so colorblind users can still separate the two lines
  - `--color-reference`: dashed neutral gray for the diagonal "perfect calibration" line
  - Semantic status colors for metric deltas: improvement vs. regression, not just red/green alone — pair with a ▲/▼ glyph or "+/–" text so color isn't the sole signal (Accessibility rule: color-not-only)
- Dark mode is optional for v1 given portfolio scope, but if included, verify contrast ≥4.5:1 for body text and ≥3:1 for chart gridlines in both themes before shipping either.

## 4. Typography
- Base 16px body, 1.5 line-height minimum.
- One font pairing: a technical/geometric sans for UI chrome (labels, nav) + monospace for numeric metric values (ECE/MCE/Brier figures) — monospace on numbers gives a "data instrument" feel and makes digit columns easier to compare at a glance.
- No text below 12px anywhere, including chart tick labels.

## 5. Layout
- Single-page, no nested navigation — this is a focused tool, not a multi-section app (Navigation Patterns: predictable, no overloaded nav needed here since there's effectively one screen).
- Above the fold: model selector + metric cards (raw vs. corrected, with delta).
- Below: reliability diagram (largest visual element, ~60% of vertical space) with legend and bin-count toggle.
- Score simulator docked as a side panel or below the diagram — a clearly secondary, interactive element, not competing with the diagram for primary attention.
- Mobile-first breakpoints still apply even though primary use is desktop: stack metric cards vertically, shrink the diagram to full-width, hide the bin-count overlay behind a toggle rather than cramming it in — no horizontal scroll under any circumstance (Layout & Responsive priority).

## 6. Charts (priority 10, but this is a chart-first product so treat as high locally)
- **Reliability diagram → line chart** (predicted vs. observed is a trend/relationship, correctly matched per chart-type rule: relationship → line, not bar).
- **Bin counts → bar underlay**, not a separate chart — keeps sample-size context spatially tied to the curve it qualifies, rather than forcing the viewer to cross-reference two charts.
- **Metric deltas → simple stat cards**, not gauges or radial charts — a gauge would imply a target/threshold that hasn't been set (ties back to Rules.md: no invented targets).
- Every chart needs a legend and tooltips on hover/tap (touch target ≥44px for any interactive chart marker on the score simulator).
- Colorblind-safe palette check on the two correction-method colors before finalizing (Charts & Data: accessible colors, don't rely on hue alone — line style differs too, e.g. solid vs. dashed).

## 7. Interaction & feedback
- Score simulator: input changes trigger a visible, non-jarring update (150–300ms transition on the marker moving along the curve) — not an instant 0ms snap, not a sluggish >500ms lag.
- Loading state on initial `/calibration/{model_id}` fetch: skeleton or spinner, never a blank screen.
- Errors (e.g., failed `/score` call) surface near the simulator control itself, not as a top-of-page banner disconnected from the input that caused it.

## 8. Accessibility checklist (must-pass before calling Phase 4 done)
- [ ] Contrast ≥4.5:1 for all body/label text
- [ ] Keyboard-navigable model selector and score simulator input
- [ ] Legend/line-style distinguishes raw vs. Platt vs. isotonic without relying on color alone
- [ ] Alt text or aria-labels on chart SVGs summarizing what the chart shows
- [ ] Focus rings visible and not removed for aesthetic reasons
- [ ] Reduced-motion respected for the simulator's marker transition

## 9. What NOT to do
- Don't add a dark-mode toggle, animated hero section, or landing page — this is a utility screen, not a marketing surface.
- Don't use emoji as icons anywhere (use a proper icon set — Lucide or similar).
- Don't let the visual design outrun what Phase 1's actual data supports — an overly polished dashboard around a thin, unverified curve is worse than a plain one around a solid curve.

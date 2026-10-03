---
name: finops-agent Engine-room Log
description: Each day's AWS cost entered as engine fuel burn in a ship's engine-room log, with the deviation ringed in red ink, read live from the deployed agent.
colors:
  cloth: "#2A201A"
  cloth-raised: "#362A22"
  cloth-hover: "#42342A"
  cloth-rule: "#54443A"
  gilt: "#D9B87A"
  cloth-text: "#EADFCB"
  cloth-dim: "#BFAE96"
  page: "#E9EEE3"
  page-shade: "#DCE4D6"
  rule-blue: "#9DBAD6"
  rule-red: "#C9574C"
  ink: "#1F2633"
  ink-dim: "#4E5A66"
  red-ink: "#A8261C"
  form: "#F2D8D1"
  form-rule: "#D9A79D"
  distress-rule: "#A8564B"
  distress-text: "#F6C9C1"
typography:
  display:
    fontFamily: "EB Garamond, Garamond, Times New Roman, serif"
    fontSize: "2.6rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.02em"
    fontFeature: "smcp, lnum, tnum"
  headline:
    fontFamily: "EB Garamond, Garamond, Times New Roman, serif"
    fontSize: "1.35rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.03em"
    fontFeature: "smcp, lnum, tnum"
  title:
    fontFamily: "EB Garamond, Garamond, Times New Roman, serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.25
    fontFeature: "lnum, tnum"
  body:
    fontFamily: "EB Garamond, Garamond, Times New Roman, serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "lnum, tnum"
  label:
    fontFamily: "EB Garamond, Garamond, Times New Roman, serif"
    fontSize: "1.02rem"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0.04em"
    fontFeature: "smcp, lnum, tnum"
  column-head:
    fontFamily: "EB Garamond, Garamond, Times New Roman, serif"
    fontSize: "0.92rem"
    fontWeight: 600
    lineHeight: 1.15
    fontFeature: "lnum, tnum"
  hand-entry:
    fontFamily: "Playwrite GB S, Segoe Script, cursive"
    fontSize: "0.95rem"
    fontWeight: 400
    lineHeight: 1.7
  hand-remark:
    fontFamily: "Playwrite GB S, Segoe Script, cursive"
    fontSize: "0.93rem"
    fontWeight: 300
    lineHeight: 1.8
  hand-form:
    fontFamily: "Playwrite GB S, Segoe Script, cursive"
    fontSize: "0.86rem"
    fontWeight: 300
    lineHeight: "28px"
  hand-verdict:
    fontFamily: "Playwrite GB S, Segoe Script, cursive"
    fontSize: "1.45rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  form: "0px"
  banner: "2px"
  page: "3px"
  tab: "4px"
spacing:
  tab-gap: "8px"
  leaf-top: "18px"
  page: "28px"
  leaf: "26px"
  rule-pitch: "28px"
  below: "30px"
  shelf-gutter: "40px"
components:
  voyage-tab:
    backgroundColor: "{colors.cloth-raised}"
    textColor: "{colors.cloth-text}"
    typography: "{typography.body}"
    rounded: "{rounded.tab}"
    padding: "8px 14px 9px"
  voyage-tab-hover:
    backgroundColor: "{colors.cloth-hover}"
  voyage-tab-pressed:
    backgroundColor: "{colors.page}"
    textColor: "{colors.ink}"
  log-page:
    backgroundColor: "{colors.page}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.page}"
    padding: "18px 26px 26px"
  log-row-today:
    textColor: "{colors.ink}"
    typography: "{typography.hand-entry}"
    padding: "1px 8px"
  log-figure-deviating:
    textColor: "{colors.red-ink}"
    typography: "{typography.hand-entry}"
  baseline-cell:
    backgroundColor: "{colors.page-shade}"
    textColor: "{colors.ink}"
    padding: "1px 8px"
  remark:
    textColor: "{colors.ink}"
    typography: "{typography.hand-remark}"
    width: "62ch"
  radio-form:
    backgroundColor: "{colors.form}"
    textColor: "{colors.ink}"
    rounded: "{rounded.form}"
  radio-form-title:
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    padding: "7px 12px 5px"
  radio-form-body:
    textColor: "{colors.ink}"
    typography: "{typography.hand-form}"
    padding: "0 12px 8px"
  distress-banner:
    textColor: "{colors.distress-text}"
    rounded: "{rounded.banner}"
    padding: "10px 14px"
---

# Design System: finops-agent Engine-room Log

## Overview

**Creative North Star: "The Engine-room Log"**

The account is a ship and every AWS service is an engine; each day's cost is that engine's fuel burn, entered in an engine-room logbook. The book lies open on a dark brown cloth binding: pale green-grey ledger stock printed with blue horizontal rules and a red double margin rule, carrying day rows by engine columns, the investigated day written in by hand at the bottom. When an engine deviates, the officer rings the figure in red ink and draws the two threshold lines in red on its chart. Beside the log, in the wide right leaf, hang the orders from the bridge (audit-trail changes), the officer's remark in the hand, and a printed radio-message form for what went to the owners, or "Nothing to report" on a quiet day. Below the book, on the cloth, sit the watch (the function's own log lines) and the archive shelf of dated log sheets.

The page is a working record, dense and printed. Two voices carry the whole hierarchy: the printed stock (EB Garamond with lining tabular figures and small caps) for everything the book was printed with or that the page itself states, and the officer's hand (Playwrite GB S) for what was written into it on the day. Red is ink, not decoration: it appears only where the officer marked a deviation. Motion is one moment: the day is written in, then ringed.

This world is its own: distinct from rag-lab's wire desk (canary teletype strips on a green-black blotter, blue pencil), order-lab's split-flap departures board (black board, gold flap ink, condensed signage) and mesh-lab's grey-blue bench instrument. It refuses the category default of a cost dashboard with line charts and an alerts table.

**Key Characteristics:**
- A dark brown cloth binding carrying one open ledger spread of pale green-grey stock (1.25fr log leaf, 1fr remarks leaf).
- Printed blue horizontal rules at a 28px pitch and a 3px red double margin rule; unused page continues as blank ruling, never a void.
- Two voices: Garamond for the printed stock, Playwrite GB S for the officer's hand.
- Red ink only where a deviation was marked: the ring, the threshold lines and labels, the deviating figure, the "Over both lines" cell, plus the printed red margin rule.
- The radio message is a printed form: title band, four field boxes, ruled body, square ink border, no shadow.
- One motion moment: the day's row is written in, then the ring draws. The resting state is always complete.

## Colors

Brown cloth and gilt outside, green-grey stock with blue and red printed rules inside, blue-black ink for entries, and red ink held for deviations.

### Primary
- **Officer's Red Ink** (red-ink): the deviation and the lines it crossed. The hand-drawn ring around the deviating figure, that figure's text, the dashed +25% and +$1 threshold lines on the chart and their hand-lettered labels, the investigated-day dot on the chart, and the "Over both lines" (or "New engine, over the $1 floor") verdict cell in the foot. Red ink is placed by the officer; nothing else on the page is red ink.

### Secondary
- **Tooled Gilt** (gilt): lettering tooled into the binding. The "Engine-room Log" title, the headings of the watch and the archive shelf on the cloth, the freshly filed sheet on the shelf, and the focus outline on the cloth.

### Tertiary
- **Radio Form Pink** (form): the radio-message form's stock. **Form Rule** (form-rule) is its field-box dividers and the ruled lines under the message body.

### Neutral
- **Binding Cloth** (cloth): the page ground around the book; scrollbar track. **Raised Cloth** (cloth-raised) is the unselected voyage tab; **Cloth Hover** (cloth-hover) its hover fill. **Cloth Rule** (cloth-rule) is every line on the binding: the header rule, tab borders, watch and shelf row rules, colophon rule, scrollbar thumb.
- **Cloth Text** (cloth-text) and **Cloth Dim** (cloth-dim): primary and secondary text on the binding (ship status figures, lede emphasis; the vessel line, lede, subtitles, watch times, shelf dates).
- **Ledger Stock** (page): the open book, and the pressed voyage tab, which is cut from the same stock so it joins the page. **Baseline Shade** (page-shade): the 7-day median window, shaded across the engine columns, and its legend swatch.
- **Printed Blue Rule** (rule-blue): every horizontal rule on the stock: table rows, the blank ruling, the orders list, foot rows.
- **Printed Margin Red** (rule-red): the 3px double vertical margin rule after the Day column, continued down the blank ruling, and the double rule between findings and between stacked leaves. It is printed, paler than the officer's ink.
- **Iron-gall Ink** (ink): every entry and printed figure on the stock, the 2px rules that bound the investigated day and the column-head and foot boundaries, the median line on the chart (at 55%), the radio form's border, focus on the page.
- **Faded Ink** (ink-dim): subtitles, foot rows, legend, unlinked orders, field labels, chart tick labels, "No message sent".
- **Distress on the Cloth** (distress-text over a 18% red-ink wash, bordered in distress-rule): the banner for a stopped server, an unreachable emulator, a down Slack stand-in or a failed run. Failure of the instrument, not a deviation; it lives on the binding, never on the page.

### Named Rules
**The Officer's Ink Rule.** Red ink marks only what the officer marked: the ring, the threshold lines and their labels, the deviating figure, the deviating verdict cell. Finding headings, "logged against this engine" notes and remarks are ink. If a red mark could not have been made by the officer ringing a deviation, it is not red ink.

**The Function's Verdict Rule.** The ring goes where the deployed function's summary.findings says, never where the page's own arithmetic would put it. The foot's "Why" row explains with the agent's detect.baseline_for; it does not decide.

**The Printed Versus Written Rule.** Margin red (rule-red) and blue rules are printed on the stock and always present; red ink (red-ink) is written and appears only on a deviation. Never swap them.

## Typography

**Display Font:** EB Garamond (with Garamond, Times New Roman, serif), self-hosted variable 400-800, roman and italic
**Body Font:** EB Garamond, same stack
**Hand:** Playwrite GB S (with Segoe Script, cursive), self-hosted variable 300-400, roman only

**Character:** Garamond is the printed stock: headings, column heads, history figures, foot rows, the page's own explanations, set with lining tabular figures page-wide and small caps for every printed heading and label. Playwrite GB S is the officer's pen, a slanted connected hand used only for what was written on the day.

### Hierarchy
- **Display** (600, 2.6rem, 2.1rem at 720px and below, line-height 1, 0.02em, small caps): the binding title only, in gilt.
- **Headline** (600, 1.35rem, 1.2, 0.03em, small caps): the leaf headings "Daily burn by engine" and "Remarks"; on the cloth, "The watch" and "The archive shelf" at 1.2rem, 0.04em, in gilt.
- **Title** (700, 1.15rem, 1.25): a finding's engine heading in ink, with its kind ("· a deviation") at 600.
- **Body** (400, 17px, 1.5): lede (75ch), subtitles in italic, figures, orders, legend (80ch), watch and shelf. Emphasis is 600-700 weight.
- **Label** (600, 1.02rem, 0.04em, small caps): "Orders from the bridge…", "The remark". The radio form's title band is the same voice at 700, 1.08rem, 0.1em; its field labels at .8rem, 0.08em in faded ink.
- **Column head** (600, .92rem, 1.15): engine names over the log, bottom-aligned above a 2px ink rule.
- **Hand entry** (400, .95rem, 1.7): the investigated day's row.
- **Hand remark** (300, .93rem, 1.8, max 62ch): the officer's cause and "Do:" lines.
- **Hand form** (300, .86rem on a 28px line): the radio message body and "No message sent"; field values at 300, .9rem.
- **Hand verdict** (400, 1.45rem, 1.5): "Nothing to report." on a quiet day.
- Chart: tick labels in Garamond 13px faded ink; threshold and median labels in the hand at 12px (red ink for thresholds, ink for the median).

### Named Rules
**The Two Voices Rule.** Printed or written, never mixed: anything the book was printed with or the page explains is Garamond; anything the officer entered on the day (the day's row, the remark, chart line labels, "Nothing to report", the radio form's field values and body) is the hand.

**The Pen Has No Bold Rule.** The hand ships no bold or italic files and font-synthesis is off for every hand-set element. Emphasis in the hand is a 1px underline at a 3px offset, as a pen would make it; italics in the hand are set upright.

**The Tabular Stock Rule.** Every Garamond figure is lining and tabular, so columns of burn never jitter.

## Layout

One centred column (max 1400px, padding 22px 28px 44px) in fixed order: binding header (title and vessel line left, ship status right, closed by a cloth rule), lede, distress banner, the row of five voyage tabs, the open book, then below it the watch (1.25fr) and the archive shelf (1fr) with a 40px gutter, then the colophon.

The voyage tabs are a five-column grid with 8px gaps, sitting directly on the book's top edge; the pressed tab is cut from the page stock and joins it. The book is a two-leaf spread, 1.25fr log and 1fr remarks, each leaf padded 18px 26px 26px. The log leaf is a column: the table, the legend, then blank ruling that fills to the foot of the leaf. The blank ruling repeats the 28px rule pitch and carries the double red margin; its left offset is measured from the Day column's right edge so the margin runs unbroken from table to blank page.

Findings in the remarks leaf stack with 26px above and 22px padding below a double red rule. The radio form sits 26px under the last finding.

At 1100px and below the spread and the below-book pair stack; the second leaf is divided by a double red rule instead of the gutter, and tabs go to three columns. At 720px and below: page padding 18px 16px 34px, the header stacks, tabs go to two columns (the fifth spans both) and become fully bordered 4px-cornered cards with a 10px gap before the book, the blank ruling is dropped, leaf padding narrows to 18px 16px 22px, the log scrolls sideways with a "swipe" note, and orders and watch rows collapse to one column.

## Elevation & Depth

The book lifts off the cloth; nothing on the page lifts. The open log casts one soft drop beneath it, and the spread's fold is a faint inner shade along the second leaf's left edge. Everything printed or written on the page, including the radio form, is flat ink on stock, separated by rules.

### Shadow Vocabulary
- **Book on the cloth** (`box-shadow: 0 18px 34px -18px rgba(0,0,0,.8)`): the open log only.
- **Spread fold** (`box-shadow: inset 12px 0 18px -16px rgba(31,38,51,.35)` with a 1px #C9D2C2 gutter line): the second leaf's left edge, side-by-side layout only.

### Named Rules
**The Printed Form Rule.** The radio form is printed on the page: a square 1.5px ink border and no shadow. It never floats as a card.

## Shapes

The book is square-cut with 3px bottom corners; voyage tabs are 4px-cornered on top only, open at the bottom where they meet the page (fully rounded at 4px when stacked on mobile); the distress banner 2px; the radio form 0. Rules are the vocabulary: 1px printed blue between rows; 2px ink to bound the column heads, the foot and the investigated day; 3px double red for the margin and between findings; 1.5px ink for the radio form's border, title band and field block, 1px form-rule between field boxes. The ring is an irregular hand-drawn closed loop (an open-ended SVG path, 1.8px red, non-scaling) that overshoots its cell by 2-3px; on the chart it is a 13 by 10 ellipse tilted -12deg round the last point. Threshold lines are dashed 5 4; the median line is solid.

## Components

### Voyage Tabs
One tab per cost story: a bold story name (600, 1.05rem) over a dim one-line gloss. Raised cloth with a cloth-rule border and no bottom border; hover to cloth-hover; press nudges 1px down over 140ms. The pressed tab turns to page stock with ink text and joins the book. While a run is in flight all tabs are disabled with a progress cursor; pressing the current tab again re-runs it.

### The Log Table (signature)
Day rows by engine columns, right-aligned figures, a left Day column closed by the double red margin. The 7-day median window is shaded across the engine columns. The investigated day is the last row, bounded above and below by 2px ink and written in the hand; a deviating figure there is red ink and ringed. The foot, opened by a 2px ink rule, prints the median, the +25% line, the +$1 line and a "Why" row (italic row heads, faded ink); the deviating verdict cell is red ink at 700. A legend with a shaded swatch explains the window and why both lines must be crossed.

### Finding (the remark)
An engine heading in ink, a figures line (median to today, ratio, delta), a small chart (the series in 1.6px ink with the last point red, the median solid, both thresholds dashed red with hand labels in a right margin, stacked 14px apart when they crowd), then "Orders from the bridge" as a ruled two-column list (time, event by actor, and an italic reason; the order logged against this engine reads upright 600 ink, unrelated orders fade), then "The remark" in the hand with "Do:" underlined, a signed line (confidence, written by rules or model) and the filed S3 key.

### Radio Message Form
A printed form on pink stock: a title band ("Radio message", "to the owners" at 400 dim), a two-by-two block of field boxes (FROM, TO, TIME RECEIPT, MSG No.: small-caps labels over hand values), and a body in the hand on 28px ruled form lines. Message emphasis is underlined, never bold. On a day with nothing sent, the same form carries "none" and a single hand line saying why.

### Nothing to Report
On a quiet day the remarks leaf carries "Nothing to report." in the hand at 1.45rem, then a remark explaining that silence is the decision. It is a result, not an empty state.

### The Watch and the Archive Shelf
Ruled lists on the cloth. The watch is time, message (600) and fields; the shelf is day, engine and when filed, with the sheet filed by this run in gilt 600 and "this run". Overflow is summarised as "N older sheets".

### Distress Banner
On the cloth under the lede: distress-text on an 18% red-ink wash with a distress-rule border, 2px corners, 10px 14px, with the recovery command in monospace.

### Focus
2px gilt outline at 3px offset on the cloth; ink on the page.

### Motion
One moment per run. The investigated day's row is written in left to right (clip-path inset from 100% to 0 over 700ms), then each ring draws (stroke-dashoffset 1 to 0 over 520ms from 620ms, plus 90ms per ring), both on cubic-bezier(.16, 1, .3, 1) via the Web Animations API with fill backwards and nothing held after the end, so the resting state is the plain entry and ring. Reduced motion shows the resting state. State transitions are 150ms background and colour changes.

## Do's and Don'ts

### Do:
- **Do** set printed matter in EB Garamond with lining tabular figures and small-caps headings, and day-written entries in the hand.
- **Do** emphasise in the hand with a 1px underline at a 3px offset, with font-synthesis off.
- **Do** place the ring from the function's findings, and draw both threshold lines in red ink on every deviation chart.
- **Do** continue unused page as blank ruling at the 28px pitch with the margin aligned to the Day column.
- **Do** give a quiet day its own written verdict ("Nothing to report.") and an empty radio form that says why.
- **Do** end motion on the visible resting state; never leave a mark that only appears through animation.

### Don't:
- **Don't** use red ink for headings, notes, links, emphasis or anything the officer did not mark as a deviation.
- **Don't** confuse printed margin red (rule-red) with the officer's red ink (red-ink).
- **Don't** synthesize bold or italic in the hand.
- **Don't** give the radio form a shadow, radius or card treatment; it is printed on the page.
- **Don't** cast shadows from anything on the page; only the book lifts off the cloth.
- **Don't** let the page's own arithmetic ring a figure.
- **Don't** fall back to a cost dashboard of line charts and an alerts table.

## Open Item

The finish review judged Playwrite GB S a monoline schoolhand rather than the direction contract's "iron-gall ledger hand". The hand is recorded here as built; replacing it is unresolved.

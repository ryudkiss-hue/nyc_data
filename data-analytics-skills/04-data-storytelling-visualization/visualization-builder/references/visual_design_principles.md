# Visual Design Principles for Data Visualisation

## Signal-to-noise ratio

Every element in a chart is either signal (it communicates data) or noise (it takes up space without adding meaning). Maximise signal; eliminate noise.

**Noise examples:**
- Gridlines that are dark or numerous
- Borders around chart areas
- Backgrounds that are not plain white
- Tick marks when labels suffice
- Legends when direct labels are possible
- Decorative icons or clip art

**The test:** Cover an element. Does the chart still make sense? If yes, remove it.

---

## Pre-attentive attributes

Pre-attentive attributes are visual properties perceived instantly, before conscious thought. Use them to guide the eye to the most important element.

| Attribute | Use for |
|---|---|
| Colour (hue) | Categorisation; highlighting |
| Colour (saturation/brightness) | Magnitude within a category |
| Size | Magnitude in scatter/bubble charts |
| Position | All quantitative comparisons |
| Shape | Categorical distinction in scatter plots |
| Motion | Changes over time (animated only) |

**Key rule:** Use only one or two pre-attentive attributes in a single chart. More creates competing focal points.

---

## Colour principles

**Encode meaning, not decoration.** Colour should communicate something: category membership, direction (positive/negative), or relative magnitude.

**Limit the palette:**
- Sequential data: single colour, varying lightness (e.g., light blue to dark blue)
- Diverging data: two colours from a neutral midpoint (e.g., red–white–blue)
- Categorical data: ≤ 6 distinct colours; grey out non-highlighted categories

**Accessibility:**
- 8% of men and 0.5% of women are red-green colour blind
- Never use red and green alone to encode "good" and "bad"
- Use blue–orange or blue–red as safe contrasting pairs
- Test charts with a colour-blind simulator before publishing

---

## Typography

- **Title:** Bold, 14–16pt, states the finding not the description
- **Axis labels:** Regular, 10–12pt, horizontal where possible
- **Data labels:** Regular or medium, 10pt, placed to avoid overlap
- **Annotation:** Italic or medium, 10pt, only for the key callout

Limit to two fonts: one for headings, one for all other text.

---

## Layout and alignment

- Align chart elements to an invisible grid
- Charts in a grid layout should share axes where possible (enables direct comparison)
- Group related charts with proximity or a shared background panel
- Leave breathing room — charts should not touch text or each other

---

## The five-second test

Show the chart to someone for five seconds, then ask: "What is the main takeaway?" If they can't answer, the chart is not communicating its message. Revise.

Common causes of failure:
- No clear focal point (too many equally-weighted elements)
- The title describes the data, not the finding
- The most important data is not visually prominent
- Too much information competing for attention

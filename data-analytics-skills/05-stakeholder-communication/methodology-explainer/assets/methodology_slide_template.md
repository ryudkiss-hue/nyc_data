# Methodology Slide — [Analysis Name]

Use this as the "How We Got There" backup slide in any presentation.
Keep it to one slide. Audiences rarely read it during the deck; it exists to answer "can you walk me through your method?" in Q&A.

---

## Slide Content (copy directly)

---

**HOW WE GOT THERE**

**Data:** [Dataset name(s)] · [N] records · pulled [date] · updated [last_modified]

**Method:** [One sentence in plain language. E.g.: "We calculated the share of ramps marked complete for each borough, using the city's ramp progress database."]

**Confidence:** [One sentence. E.g.: "Margin of error ±3 pp (95%). Boroughs with fewer than 30 records are flagged as low-confidence."]

**Limitations:** [One bullet per limitation, max 3. E.g.:
- Does not include ramps added to the database after [date]
- Physical confirmation status unknown for [X]% of records
- Staten Island sample (n=[N]) is smaller; estimates less stable]

---

## Speaker Notes (for Q&A preparation)

Prepare to answer these questions from the audience:

**"How confident are you in that number?"**
> "[State confidence level. E.g.: 'We're using the city's official database, which is updated daily. The margin of error is ±3 percentage points. The main uncertainty is whether physical confirmations have been logged — we've flagged that in the caveats.']"

**"Could the data be wrong?"**
> "[Acknowledge data limitations honestly. E.g.: 'The database relies on field inspectors logging completions in real time. We know some entries lag by a few days. We cross-checked against [secondary source] and the numbers were consistent.']"

**"Did you compare to other cities / benchmarks?"**
> "[If yes, describe benchmark. If no: 'We focused on within-NYC borough comparisons and against our own SLA targets. A cross-city comparison would require data that's not standardized — happy to explore that separately.']"

**"How recent is this?"**
> "[State pull date and last_modified. E.g.: 'Data was pulled on [date]; the dataset was last updated [date]. At that point it was within our 14-day freshness SLA.']"

**"Can you share the raw data?"**
> "[NYC Open Data citation. E.g.: 'This data is publicly available at data.cityofnewyork.us — dataset ID [fourfour]. I can share the query we used to produce these results.']"

---

## Design Notes

- Font size: minimum 18pt on body text
- Borough codes: always decode (MN → Manhattan, BX → Bronx, BK → Brooklyn, QN → Queens, SI → Staten Island)
- Color: use DOT brand palette if available; ensure sufficient contrast for projector
- Keep the slide sparse — the methodology is backup, not the headline

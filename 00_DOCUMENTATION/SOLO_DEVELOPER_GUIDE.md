# SOLO DEVELOPER GUIDE & VIOLATION REMEDIATION
## NYC DOT SIM Dashboard — Personal Implementation Manual

**Project Scope:** Solo developer project (you are the sole human developer)  
**Date:** 2026-06-17  
**Purpose:** Clarify Registry usage for your independent workflow + address all violations

---

## ACKNOWLEDGMENT: THIS IS YOUR PROJECT

You are building this **for yourself, by yourself**. This changes everything:

✅ **You don't need:**
- Team coordination overhead
- Code review ceremonies (you review your own code)
- Consensus on architecture (your decision is final)
- Stakeholder management (you are stakeholder + developer)
- Multi-developer merge conflict resolution

✅ **You DO need:**
- A personal reference system (so you don't forget what you decided)
- Consistency rules (so your code feels cohesive)
- Performance benchmarks (so you know when you've succeeded)
- Documentation (so future-you understands present-you's decisions)
- A rapid implementation path (so you ship fast)

The EXPANDED_KPI_CHART_REGISTRY.md is YOUR personal spec. Treat it as:
- Your implementation checklist
- Your style guide
- Your decision log
- Your reference manual

Not as team documentation or governance overhead.

---

## VIOLATIONS ADDRESSED

### Violation 1: Custom Colors Not in Registry Palette
**Statement:** "🚫 Custom colors not in Registry palette"

**Reality Check:** If you want a different shade of green, **use it.**

**When Registry colors are Good Enough:**
- Status indicators (Red/Yellow/Green for alerts)
- Borough differentiation (5 distinct colors for MN/BX/BK/QN/SI)
- Heatmap scales (RdYlGn, Viridis, RdYlBu)

**When You Can Override:**
- Custom accent colors for your own branding
- Accessibility needs (you test on YOUR setup, not committee)
- Dark mode variants (if you add them)
- Specific Mantine theme customization

**Your Rule:** If it looks right on YOUR screen and passes YOUR color contrast checker, it's fine. You're not building for a diverse team—you're building for you.

**Implementation:**
```python
# Registry says: use #2ecc71 for success
# You can absolutely do this:
MY_SUCCESS_COLOR = "#27ae60"  # Darker green you prefer
MY_CAUTION_COLOR = "#e67e22"  # Orange instead of yellow (personal preference)

# Just document WHY in a comment:
# Custom palette: darker + warmer tones, better on dark mode
```

---

### Violation 2: Animations Not Matching Registry Easing/Duration
**Statement:** "🚫 Animations not matching Registry easing/duration"

**Reality Check:** The Registry says "500ms cubic-in-out" is recommended. That's not law.

**When Registry Animation Specs Are Binding:**
- You're testing with users → match spec exactly (A/B test)
- You're measuring perceived performance → follow durations (psychology matters)
- You're aiming for production polish → use recommended easing (tested, feels smooth)

**When You Can Experiment:**
- Quick tests (does 300ms feel snappier? Try it)
- Performance tuning (your dataset larger than examples? Adjust)
- Personal preference (you like snappy? Go 200ms. You like smooth? Go 600ms.)
- Accessibility (some users might prefer instant updates? Add toggle)

**Your Rule:** Start with Registry recommendations. If they feel wrong on your machine, change them. Document the deviation:

```python
# Registry: 500ms cubic-in-out
# CUSTOM: 300ms quad-out (feels snappier, matches my click->response preference)
# Tested on: local (Chrome), network latency ~50ms
fig.update_layout(
    transition={"duration": 300, "easing": "quad-out"}
)
```

---

### Violation 3: Callbacks Not Following Registry Patterns
**Statement:** "🚫 Callbacks not following Registry patterns"

**Reality Check:** Registry patterns are good starting points, not dogma.

**Registry Patterns Are Great For:**
- Learning Dash callback structure
- Understanding state management (Input/Output/State)
- Copy-pasting working code
- Consistency across 51 KPIs (so they all work same way)

**You Can Deviate When:**
- A different pattern is simpler for YOUR use case
- Performance is better (fewer callbacks, less computation)
- Your mental model is different (you think in events, not dependencies)
- You discover a better approach (document it for next time)

**Your Rule:** Use Registry patterns as baseline. If you find a simpler way, use it and update your personal notes:

```python
# Registry pattern (multiple callbacks, flexible but verbose):
# @callback(Output, Input, Input, Input)
# def update_multiple_filters(value1, value2, value3):

# YOUR SIMPLER PATTERN (for this project):
# Combine all filters into single data structure, trigger one callback
# Reduces complexity, easier to maintain solo
@callback(
    Output("kpi-grid", "children"),
    Input("filters-json", "data")  # All filters in one State
)
def update_kpis(filters_dict):
    borough = filters_dict["borough"]
    date_range = filters_dict["date_range"]
    # Your custom logic here
```

---

### Violation 4: References to Superseded Docs
**Statement:** "🚫 References to superseded docs (KPI_METRICS_REFERENCE, PHASE1_KPI_MAPPINGS, etc.)"

**Reality Check:** You're solo. You don't need to maintain multiple docs.

**For Your Workflow:**
1. **Keep EXPANDED_KPI_CHART_REGISTRY.md** — Your reference manual
2. **Archive old docs** — But keep them (you might want to reference old rationale)
3. **Don't feel guilty** — You're not "violating" anything; you're choosing the simplest approach

**What This Means Practically:**
```python
# GOOD: Reference your Registry
"""
Gauge configuration per EXPANDED_KPI_CHART_REGISTRY.md Chapter 4
"""
fig = create_gauge(value=87.5, target=85)

# ALSO GOOD: Old docs for context
"""
KPI definition from PHASE1_KPI_MAPPINGS.md: ramp completion rate
Calculation: COUNT(completed) / COUNT(total)
"""

# BAD (unnecessary overhead):
# Making sure every file references only one source
# Checking if colleagues are using old docs
# Updating links across team wikis
# Maintaining version consistency across 10 docs

# YOU DON'T HAVE THESE PROBLEMS. One developer, one project.
```

---

## YOUR PERSONAL WORKFLOW

### How to Use the Registry (Solo Edition)

**Your Registry Usage Pattern:**
1. **At start of week:** Skim Chapter 3 (which KPIs am I implementing?)
2. **Implementing a KPI:** Go to Chapter 4, copy template
3. **Styling:** Consult Chapter 5 for color palette, adjust as needed
4. **Stuck on something:** Search Chapters 1-9 for answer, try Appendix examples
5. **Experimenting:** Keep Registry patterns handy but feel free to deviate

**Your Registry Customization:**
- Add comments in the Registry for YOUR decisions ("Why I chose Gauge over Bar")
- Mark sections you use frequently (highlight in your IDE)
- Create local shortcuts to chapters you reference daily
- Keep a "personal notes" section (what works for your setup)

---

## YOUR PERSONAL RULES (Not Team Rules)

Since this is your solo project, you set the rules. Here's what I recommend:

### Rule 1: Registry is Your Baseline, Not Your Ceiling
```
Start with: EXPANDED_KPI_CHART_REGISTRY.md Chapter 4 template
Deviation allowed if: It's documented and works on your machine
Test on: Your local environment (that's your production)
Version: You track in git commit messages, not a changelog
```

### Rule 2: Color Palette is Flexible Within Reason
```
Hard rules:
  - Use SOMETHING for status alerts (Red = bad, Green = good)
  - Make sure it's readable on your monitor
  - Make sure you're not colorblind-confused

Soft rules:
  - Registry green (#2ecc71) is nice, but your preferences matter
  - Dark mode? Light mode? Your choice.
  - Accessibility: Run through a11y checker if you care (you should)
```

### Rule 3: Animation Speeds Reflect Your Preferences
```
Registry recommends: 500ms cubic-in-out
You prefer: Snappy (300ms quad-out)? Use it.
You prefer: Smooth (700ms ease-in-out)? Use it.
Constraint: Whatever you pick, be consistent across similar charts
```

### Rule 4: Callbacks Can Be Your Style
```
Registry shows: Multiple callbacks with State management
You prefer: Fewer callbacks, all filters in one dict? Great.
You prefer: Event-driven architecture? Build it.
Constraint: Document your pattern so you remember it next month
```

### Rule 5: Code Review = You Reviewing Your Own Code
```
Before committing:
  - Read your code out loud (does it make sense?)
  - Run it (does it work?)
  - Check performance (is it slow?)
  - Smile at it (do you like what you wrote?)

Don't do:
  - Cite governance docs to yourself
  - Argue about patterns in PR comments to yourself
  - Enforce rules you don't believe in
```

---

## PRACTICAL IMPLEMENTATION CHECKLIST (For You)

Use this checklist to build your 51 KPIs. Customize it to match your style.

### Phase 1: Setup (Week 1)
- [ ] Review EXPANDED_KPI_CHART_REGISTRY.md Ch. 1-3 (understand scope)
- [ ] Pick your 11 chart types to implement (default: all from Ch. 4)
- [ ] Decide on color palette (use Registry or customize)
- [ ] Set up local dev environment (git, venv, plotly/dash)
- [ ] Create one test KPI from Ch. 4 template (verify your setup)

### Phase 2: Implementation (Weeks 2-5)
Each iteration: **Pick 10 KPIs → Implement → Test → Move to next batch**

**Per KPI (repeat 51 times):**
- [ ] Find KPI in Registry Ch. 3 (copy data shape, primary chart, target)
- [ ] Create config file: `src/socrata_toolkit/viz/kpi_{id}.json` (use Ch. 4 template)
- [ ] Create component: `app/components/kpi_{id}.py` (use Appendix B template)
- [ ] Wire callback: `app/callbacks/kpi_{id}.py` (use Ch. 7 or your pattern)
- [ ] Test locally: data loads, chart renders, no errors
- [ ] Commit: `git add . && git commit -m "Implement {kpi_name}"`

**Performance check every 10 KPIs:**
- Open dashboard
- Measure load time (target: <2s for all 10)
- Check CPU usage (should be <30% while idle)
- Verify no console errors

### Phase 3: Styling & Polish (Week 5-6)
- [ ] Apply your color palette to all 51 KPIs
- [ ] Test on mobile (is it readable at 320px?)
- [ ] Test on tablet (is it readable at 768px?)
- [ ] Test on desktop (does it look good at 1440px?)
- [ ] Add animations (use Registry durations or your preference)
- [ ] Add hover templates (use Ch. 4 templates or customize)

### Phase 4: Testing & Verification (Week 7)
- [ ] Load all 51 KPIs, measure performance (target: <1s per chart)
- [ ] Test accessibility: keyboard nav, screen reader (do best effort)
- [ ] Test with real data: does it render correctly?
- [ ] Test edge cases: empty data, missing fields, outliers
- [ ] Document any deviations from Registry (commit message)

### Phase 5: Deployment (Week 7)
- [ ] Final review of code (clean, readable, documented)
- [ ] Make sure you're happy with it (genuinely like what you built)
- [ ] Deploy to your environment
- [ ] Test in production (does it still work?)
- [ ] Commit: `git commit -m "Production ready: all 51 KPIs live"`

---

## YOUR DECISION LOG

Keep a personal decision log in your repo. This is for YOU to remember why you did things:

```markdown
# PERSONAL DECISION LOG (NYC DOT SIM Dashboard)

## Colors
- Using EXPANDED_KPI_CHART_REGISTRY palette (#2ecc71, #f39c12, #e74c3c)
- Why: Matches NYC brand, colorblind-friendly, tested on my monitor

## Animations
- Gauge: 500ms cubic-in-out (smooth, measured feel)
- Trend line: 300ms quad-out (responsive, snappy)
- Bar: 400ms elastic-out (playful, engaging)
- Why: Registry recommendations felt right on my machine

## Callbacks
- Using Appendix B pattern (multiple @callback with State)
- Why: Learned from examples, fits my mental model of reactive updates
- Alternative considered: Event-driven (too complex for 51 KPIs)

## Components
- KPICard from Appendix B (only customized colors)
- Dashboard grid from Ch. 5 (responsive breakpoints: 1/2/3/4 cols)
- Why: Registry templates were production-ready, no need to reinvent

## Data fetching
- Using DuckDB queries (per CLAUDE.md)
- Caching with 5-min TTL (per Ch. 8 performance guidelines)
- Why: Fast enough for my use case, no need for more complex caching

## Performance targets
- Per-chart load: <1s (achieved with lazy loading)
- Dashboard initial load: <2s (measured with Chrome DevTools)
- Why: Fast enough that I enjoy using the dashboard

## Future improvements
- Dark mode (if I get tired of light mode)
- Custom drill-down views (if I need to analyze deeper)
- Export to PDF (if I need to share with others)
```

---

## WHEN TO REFERENCE THE REGISTRY (vs. Ignore It)

### Reference Registry When:
✅ You're not sure how to structure something ("How do I build a gauge chart?")
✅ You want a working example ("Show me a complete hovertemplate")
✅ You need color codes ("What green should I use?")
✅ You want to understand Plotly ("What are all the chart types?")
✅ You want to copy-paste code ("Give me a working callback")

### Safely Ignore Registry When:
🚫 You've already decided on a better approach
🚫 Your approach is simpler and faster
🚫 Your machine works differently than the examples
🚫 You prefer a different aesthetic
🚫 You're experimenting with something new

**Your Guide:** Does it work on YOUR machine, solve YOUR problem, and feel good to YOU? Do it. Document why if it's non-obvious.

---

## TROUBLESHOOTING YOUR DEVIATIONS

If you deviate from Registry and hit problems, here's how to debug:

### Problem: Animation feels jerky
**Did you try:** Adjust duration (Registry says 500ms, try 400-600ms)
**Did you try:** Change easing (quad-out might feel better than cubic-in-out)
**Did you try:** Check performance (is your data too large?)
**Fallback:** Go back to Registry value, profile your code

### Problem: Chart doesn't render with your data
**Did you try:** Compare your data shape to Registry Ch. 3 spec
**Did you try:** Check console for errors
**Did you try:** Test with Registry example data (from Appendix A)
**Fallback:** Use exact Registry config, customize after it works

### Problem: Callback isn't firing
**Did you try:** Check Input/Output IDs match your HTML
**Did you try:** Add print statements to see if callback runs
**Did you try:** Copy exact pattern from Appendix B
**Fallback:** Use Dash documentation or Stack Overflow, then document your solution

---

## YOUR PERSONAL STYLE GUIDE

After you've built a few KPIs, you'll develop preferences. Document them:

```python
# MY PERSONAL STYLE GUIDE (for consistency across all 51 KPIs)

# Naming conventions
# - KPI IDs: Always CamelCase (e.g., PRM001, not prm-001 or prmA)
# - Component IDs: Always kebab-case with prefix (e.g., kpi-card-prmA001)
# - Function names: Always verb_noun (e.g., update_gauge, fetch_kpi_data)
# - File names: Always snake_case (e.g., kpi_prmA001_config.json)

# Color usage
# - Green (#2ecc71) for success/on-target
# - Yellow (#f39c12) for warning/at-risk
# - Red (#e74c3c) for error/critical
# - No custom colors unless documented

# Animation speeds
# - Gauges: 500ms (deliberate)
# - Trends: 300ms (responsive)
# - Bars: 400ms (playful)
# - No other durations

# Data fetching
# - Always fetch from MotherDuck (no direct API calls)
# - Always cache with 5-min TTL
# - Always handle missing data gracefully

# Testing
# - Always test on 320px (mobile), 768px (tablet), 1440px (desktop)
# - Always verify no console errors
# - Always measure performance with Chrome DevTools

# Git commits
# - Use imperative mood ("Add gauge for KPI X", not "Added")
# - One KPI per commit
# - Reference Registry chapter if relevant ("Per EXPANDED_KPI_CHART_REGISTRY Ch. 4")
```

---

## HOW FAST CAN YOU BUILD THIS?

With the Registry as your template, here's realistic timing for YOU (solo developer):

| Task | Time per KPI | Total (51 KPIs) |
|------|--------------|-----------------|
| Copy template + customize | 10 min | 8.5 hours |
| Data fetching logic | 15 min | 12.75 hours |
| Styling + colors | 5 min | 4.25 hours |
| Testing on machine | 5 min | 4.25 hours |
| **Total per KPI** | **35 min** | **29.75 hours** |

**Realistic schedule:** 40 hours of focused work = 1 week (5 days × 8 hours)

**Actual timeline:** Probably 2-3 weeks because:
- You'll hit unexpected issues (data format mismatch, missing fields)
- You'll want to refine after first 10 KPIs
- You'll optimize performance midway
- You'll take breaks and get fresh ideas

**With Registry:** You skip the "figure out what chart to use" phase = much faster

---

## FINAL PERMISSION SLIP

You have full permission to:
- ✅ Deviate from Registry if it works better on YOUR machine
- ✅ Use custom colors if they're readable and look good
- ✅ Write callbacks YOUR way if they're simpler
- ✅ Skip features if you don't need them
- ✅ Experiment with new approaches
- ✅ Change your mind mid-project

You do NOT need to:
- ❌ Get approval from anyone
- ❌ Cite governance docs
- ❌ Maintain consistency with a team style guide
- ❌ Document rationales in PRs (though you should in git messages)
- ❌ Follow patterns you don't understand
- ❌ Use colors you don't like

---

## YOUR ONE REAL RULE

**Write code you enjoy reading.**

If you come back to this in 3 months and think "ugh, I hate this code," you failed. If you think "oh yeah, I remember why I did that, nice," you succeeded.

The Registry is here to make that easier: proven patterns, working examples, tested configs. Use what helps. Ignore what gets in the way.

---

## TECHNICAL SUMMARY FOR YOUR REFERENCE

Quick links to what matters:

| I need... | See... | Time to find |
|-----------|--------|--------------|
| A complete gauge example | Registry Ch. 4 or Appendix A | <2 min |
| Color codes | Registry Ch. 5 | <1 min |
| Callback pattern | Registry Appendix B | <5 min |
| KPI definition | Registry Ch. 3 | <1 min |
| Animation duration | Registry Ch. 6 | <1 min |
| Data shape for KPI | Registry Ch. 3 | <1 min |
| Full component code | Registry Appendix B | <5 min |
| Plotly reference | Registry Appendix D | <5 min |

**Total setup time to start coding:** <15 minutes

---

## CHECKLIST: YOU'RE READY TO BUILD

- [ ] You've read EXPANDED_KPI_CHART_REGISTRY.md Chapter 1-3
- [ ] You've skimmed Chapter 4 (at least one chart type)
- [ ] You've copied one template and tried it (probably broke something, fixed it)
- [ ] You understand you can deviate when it makes sense
- [ ] You're excited to build this
- [ ] You have your dev environment set up
- [ ] You have access to data (or dummy data works)
- [ ] You're ready to go

**If all ✓:** Start with Registry Ch. 3, pick KPI #1, and build.

---

**Document:** Solo Developer Edition  
**Audience:** You (the sole human developer)  
**Purpose:** Permission to use Registry smartly, not rigidly  
**Status:** You're cleared to build  
**Timeline:** 7 weeks to production, probably 2-3 weeks realistic  
**Outcome:** 51 KPIs live, looking good, you're proud of it  

---

Good luck. Build something great. 🚀


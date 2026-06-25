# NYC Street Design Manual Compliance Test - Maintenance Guide

**File:** `tests/test_nyc_sdm_4th_edition_compliance.py`

**Purpose:** Validate all material specifications and design standards against the official NYC Street Design Manual 4th Edition.

---

## Quick Start

### Run the compliance test:
```bash
pytest tests/test_nyc_sdm_4th_edition_compliance.py -v
```

### Expected result:
```
passed 45 tests in 0.25s
```

---

## Maintenance Schedule

### Quarterly (Every 3 months)
- [ ] Visit https://www.nycstreetdesign.info/
- [ ] Check for any announcements or updates
- [ ] Verify manual version is still 4th Edition
- [ ] Update `MANUAL_METADATA["last_accessed"]` in test file

### Annually (Q2-Q3)
**CRITICAL STEP:**
1. Download the latest NYC Street Design Manual (4th Edition)
2. Compare each test assertion with official manual content
3. Update assertions if manual sections changed
4. Document any divergence with [SDM-COMPLIANCE] issue on GitHub

---

## Section-by-Section Verification Checklist

### Section 4: Sidewalk Materials and Finishes

#### Section 4.1: Hot Mix Asphalt (HMA)
- [ ] Manual states thickness = 2 inches
- [ ] Compaction specification = 96%
- [ ] Binder grade = PG58-28 (SuperPave)
- [ ] Air voids = 4.0%
- [ ] VMA = 14.0%
- [ ] Nominal max aggregate = 12.5mm
- [ ] Slip resistance = 65 BPN
- [ ] Lifecycle = 20 years
- [ ] Routine maintenance interval = 3 years
- [ ] Preventive overlay = 7 years
- [ ] Seal coat frequency = every 3 years
- [ ] Freeze-thaw climate adjustment = -2 years
- [ ] Salt exposure adjustment = -2 years

**If anything differs:**
1. Update the assertion in `test_section_4_1_hot_mix_asphalt_standard()`
2. Update the constant in `src/socrata_toolkit/material/definitions.py`
3. Create GitHub issue: `[SDM-COMPLIANCE] Update HMA specs - Section 4.1`
4. Run full test suite to catch any downstream impacts

#### Section 4.2: Portland Cement Concrete (PCC)
- [ ] Thickness = 4 inches
- [ ] Compressive strength = 3,500 PSI
- [ ] Air content = 6%
- [ ] Water-cement ratio = 0.45
- [ ] Joint spacing = 4 feet
- [ ] Lifecycle = 30 years
- [ ] Routine maintenance interval = 5 years
- [ ] Preventive overlay = 15 years
- [ ] Full reconstruction = 30 years
- [ ] Joint sealing frequency = every 5 years
- [ ] Freeze-thaw climate adjustment = -5 years
- [ ] Salt exposure adjustment = -5 years

#### Section 4.3: Permeable Pavements
- [ ] Permeable asphalt thickness = 2.5 inches
- [ ] Porosity = 18% air voids
- [ ] Infiltration rate = 360 in/hr
- [ ] Vacuum sweeping = every 6 months
- [ ] Pervious concrete thickness = 4 inches
- [ ] Pervious concrete porosity = 15%
- [ ] Pervious concrete infiltration = 480 in/hr

#### Section 4.4: Specialized Surfaces
- [ ] Natural stone (bluestone) thickness = 1.5 inches
- [ ] Bluestone slip resistance = 75+ BPN
- [ ] Clay brick dimensions: 3.625" x 7.625" x 2.25"
- [ ] Brick lifecycle = 25 years minimum

#### Section 4.5: Accessibility Elements
- [ ] Truncated dome height = 0.5 inches
- [ ] Dome diameter = 0.9 inches
- [ ] Dome spacing (center-to-center) = 1.6 inches

### Section 5: Sidewalk Width, Clearance, and Slopes

#### Section 5.1: Accessible Route Width
- [ ] Minimum clear width = 4 feet
- [ ] Preferred width = 5+ feet
- [ ] High-volume pedestrian = 8+ feet

#### Section 5.2: Longitudinal Slope
- [ ] Maximum slope = 5% (1:20 ratio)
- [ ] Exception allowed for necessary drainage

#### Section 5.3: Cross Slope
- [ ] Maximum cross slope = 2% (1:50 ratio)
- [ ] Prevents wheelchair roll-off

#### Section 5.5: Changes in Level
- [ ] ≤ 0.25": Vertical (no bevel)
- [ ] 0.25-0.5": Bevel required (max 1:2 = 50%)
- [ ] > 0.5": Curb ramp required (max 1:12 = 8.33%)

### Section 6: Walking Surface Material Performance

#### Section 6.1: Slip Resistance (British Pendulum Number)
- [ ] Dry minimum = 60 BPN
- [ ] Wet minimum = 40 BPN
- [ ] New installations = 65 BPN
- [ ] Asphalt = 65 BPN
- [ ] Concrete (broom finish) = 70+ BPN
- [ ] Bluestone = 75+ BPN

#### Section 6.2: Firm and Stable Walking Surfaces
- [ ] No holes > 0.25 inches
- [ ] No vertical movement > 0.5 inches under load
- [ ] No buckling or shifting

---

## How to Update Test Assertions

### Example: If Section 4.1 HMA thickness changed to 2.5 inches:

**Step 1:** Find the assertion in the test file:
```python
def test_section_4_1_hot_mix_asphalt_standard(self):
    design = spec.design_standards
    assert design["thickness_inches"] == 2.0, "SDM 4.1: HMA thickness = 2 inches"
```

**Step 2:** Update the constant in `src/socrata_toolkit/material/definitions.py`:
```python
ASPH_STANDARD = MaterialSpecification(
    ...
    design_standards={
        "thickness_inches": 2.5,  # UPDATED from 2.0
        ...
    }
)
```

**Step 3:** Update the test assertion:
```python
assert design["thickness_inches"] == 2.5, "SDM 4.1: HMA thickness = 2.5 inches"
```

**Step 4:** Add source documentation:
```python
assert design["thickness_inches"] == 2.5
# Source: NYC SDM 4th Edition, Section 4.1, Page XX
# Date verified: 2024-12-15
# Verifier: [Your Name]
```

**Step 5:** Run the test:
```bash
pytest tests/test_nyc_sdm_4th_edition_compliance.py::TestSection4MaterialsAndFinishes::test_section_4_1_hot_mix_asphalt_standard -v
```

**Step 6:** Create a GitHub issue (if significant change):
```
[SDM-COMPLIANCE] Update HMA thickness to 2.5" (Section 4.1)

Manual: NYC Street Design Manual 4th Edition, Section 4.1, Page XX
Change: HMA thickness updated from 2.0" to 2.5"
Impact: 
  - Updated ASPH_STANDARD in material/definitions.py
  - All dependent Metric calculations use new value
  - Lifecycle cost estimates may change

Verified by: [Your Name]
Date: 2024-12-15
```

---

## Dealing with Manual Updates or Divergence

### If the manual changes a specification:

1. **Understand the impact:**
   ```bash
   # Find all uses of the old value
   grep -r "thickness_inches.*2.0" src/
   grep -r "ASPH_STANDARD" src/ tests/
   ```

2. **Update consistently:**
   - Update `material/definitions.py`
   - Update test assertion with new value + source
   - Update related costs if applicable
   - Run full test suite to catch impacts

3. **Document the change:**
   ```python
   # Example in material/definitions.py
   ASPH_STANDARD = MaterialSpecification(
       ...
       design_standards={
           "thickness_inches": 2.5,  # 2024-12-15: Updated per SDM 4.1
           ...
       }
   )
   ```

### If we diverge from the manual intentionally:

This should be **rare**, but if NYC DOT policy differs from SDM:

1. Create an issue: `[SDM-DIVERGENCE] [Brief reason]`
2. Document the divergence in `CLAUDE.md`:
   ```markdown
   ## Known Divergences from SDM 4th Edition
   
   ### Material thickness (ASPH_STANDARD)
   - SDM specifies: 2.0 inches
   - We use: 2.5 inches
   - Reason: NYC DOT field experience shows 2.5" optimal for durability
   - Approved by: [Person/Date]
   ```

---

## ADA Compliance (Federal Standards)

**Note:** ADA compliance rules (CFR 36) are federal law and change only when federal law changes.

These are **stable** and don't need quarterly verification:
- Width: 4 feet minimum
- Slope: 5% longitudinal, 2% cross
- Slip resistance: 60 BPN dry, 40 BPN wet
- Changes in level: 0.25-0.5" bevel, >0.5" ramp

Reference: https://www.ada.gov/businesslaw/2010ADAstandards_index.html

---

## Setting Up Quarterly Reminders

### Option 1: GitHub Issues (Recommended)
Create a recurring issue using GitHub's issue templates:

**File:** `.github/ISSUE_TEMPLATE/sdm-quarterly-verification.md`
```markdown
---
name: Quarterly SDM Compliance Verification
about: Annual verification that tests match official manual
title: 'Q2: SDM 4th Edition Compliance Verification'
labels: sdm-compliance, documentation
---

## Quarterly SDM Compliance Check

- [ ] Download latest manual from https://www.nycstreetdesign.info/
- [ ] Verify edition is still 4th Edition
- [ ] Run compliance tests: `pytest tests/test_nyc_sdm_4th_edition_compliance.py -v`
- [ ] All tests passing? 
- [ ] Review Section 4.1 (HMA) for changes
- [ ] Review Section 4.2 (Concrete) for changes
- [ ] Review Section 5 (Width/Slope) for changes
- [ ] Review Section 6 (Slip Resistance) for changes
- [ ] Update `last_accessed` date in test metadata
- [ ] Close this issue once complete
```

### Option 2: Bash Script (Local)
Create `scripts/verify_sdm_compliance.sh`:
```bash
#!/bin/bash
# Run quarterly SDM compliance verification

echo "🔍 Running NYC Street Design Manual Compliance Tests..."
pytest tests/test_nyc_sdm_4th_edition_compliance.py -v

if [ $? -eq 0 ]; then
    echo "✅ All SDM compliance tests passed!"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Visit https://www.nycstreetdesign.info/"
    echo "  2. Cross-check key sections (4, 5, 6) against test file"
    echo "  3. If any changes found, update test assertions"
    echo "  4. Update MANUAL_METADATA['last_accessed'] date"
else
    echo "❌ SDM compliance tests FAILED"
    echo "Run: pytest tests/test_nyc_sdm_4th_edition_compliance.py -vvs"
fi
```

Run with: `bash scripts/verify_sdm_compliance.sh`

---

## Troubleshooting

### Test fails with "Section 4.1 HMA thickness assertion failed"

**Cause:** Material spec doesn't match manual

**Fix:**
1. Check official manual Section 4.1
2. Update constant in `material/definitions.py`
3. Update assertion in test file with new value + page reference

### "ADA rule ADA-1.2.1 not found"

**Cause:** Rule not registered in `standards/design.py`

**Fix:**
```python
# In standards/design.py, add:
ADA_RULE_1_2_1 = ADAComplianceRule(
    rule_id="ADA-1.2.1",
    title="Accessible Route Width",
    requirement="Minimum 4 feet (1220mm) clear of obstructions",
    parameters={"min_clear_width_feet": 4.0},
    failure_severity=ADAFailureSeverity.HIGH,
)
```

### Tests pass but I think manual has different values

**Process:**
1. Check manual Section 4 carefully (page numbers matter)
2. If you find a discrepancy, create issue: `[SDM-COMPLIANCE] Potential divergence in Section X`
3. Document what manual says vs. what test expects
4. Discuss with team before changing

---

## Resources

- **Official Manual:** https://www.nycstreetdesign.info/
- **ADA Standards:** https://www.ada.gov/businesslaw/2010ADAstandards_index.html
- **NYC Admin Code § 19-152 (Local Law 60):** https://www1.nyc.gov/site/buildings/bldgs_enforce_chp/chapter_4_property_maintenance.page
- **Material Standards (ASCE, ACI, NAPA):** Embedded in test file comments

---

## Contact & Support

For questions about SDM compliance:
- Create issue: `[SDM-COMPLIANCE] [Your question]`
- Reference the specific test that's unclear
- Include manual section number and page

---

**Last Updated:** 2024-06-05  
**Test Version:** 1.0  
**Manual Version:** 4th Edition  
**Maintainer:** NYC DOT Data Team

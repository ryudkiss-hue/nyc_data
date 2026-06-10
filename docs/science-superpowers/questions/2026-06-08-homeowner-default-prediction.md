# Homeowner Default Prediction (PQ-05)

**Research question:** To what extent can property assessed value and year of last structural alteration predict the probability of a homeowner defaulting to City-repair in Defective Lots within the SIM division?

**Background / motivation:** SIM division incurs significant operational debt by waiting for the 75-day legal grace period to expire before dispatching city contractors. If we can predict default probability in advance, we can pre-stage municipal contractor resources, reducing the repair-backlog cycle by up to 20%.

**Hypotheses:**
- H0 (null): Property financial/structural features have no predictive power over the probability of homeowner default.
- H1 (alternative): Higher assessed property value or older structural alteration dates increase the likelihood of homeowner default, allowing for early intervention.

**Population & unit of analysis:**
- Population: All properties in NYC with an active SIM sidewalk violation.
- Unit of Analysis: Individual property (BBL - Borough, Block, Lot).

**Key variables (operationalized):**
- Outcome (Dependent): `City_Default_Flag` (Binary: 1 if City dispatched repair, 0 if owner self-repaired).
- Predictor(s) / exposure: `Assessed_Land_Value`, `Year_Built`, `Year_Alter1` (Structural update date).
- Covariates / potential confounders: `Lot_Area`, `Building_Class`, `Zoning_District`, `Community_District` (Location-based demand).

**What counts as an answer:** A statistically significant predictive model (AUC > 0.70) that identifies high-risk lots (>75% probability of default) at the time of violation issuance.

**Scope & exclusions:**
- Scope: Sidewalk violations (SIM Division).
- Exclusions: Roadway-related violations (RRM Division), violations dismissed in court (DQ-03), and tree-related obstructions (Parks Department).

**Open questions for prior-work survey:**
- Are there known spatial correlations between default clusters?
- Does the "Equity Multiplier" (used in other SIM processes) correlate with self-repair rates?

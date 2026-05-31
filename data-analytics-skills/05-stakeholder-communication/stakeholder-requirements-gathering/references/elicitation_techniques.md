# Requirements Elicitation Techniques

Practical methods for surfacing what a stakeholder actually needs when their initial request is vague, incomplete, or potentially misdirected.

---

## Technique 1: The 5 Whys

Use when the stated request seems like a symptom rather than the real question.

**Process:** Ask "why do you need this?" five times (or until the root purpose is clear).

**Example:**
- Request: "Can you pull a list of customers who haven't logged in for 30 days?"
- Why? → "We want to reach out to them."
- Why? → "We think they might churn."
- Why do you think that? → "We saw a dip in weekly active users."
- Why does that concern you? → "It affects our renewal rate forecast."
- Root question: *How at-risk is our renewal cohort, and which customers should the CS team prioritise?*

This is a much more useful question than the original pull request.

---

## Technique 2: Scenario Walkthrough

Use when the stakeholder knows what they want but you're unsure how they'll use it.

**Process:** Ask them to walk you through exactly what they'll do with the output.

Key prompts:
- "Walk me through what happens after you receive this. Who sees it first? What decision gets made?"
- "What does success look like — what would you do differently based on this analysis?"
- "Can you show me an example of a similar output you've found useful in the past?"

What to listen for: format requirements (table vs. chart), level of granularity, who the real audience is.

---

## Technique 3: MoSCoW Prioritisation

Use when the scope is too large or there are competing requirements.

Ask the stakeholder to classify each requirement:

| Category | Definition |
|---|---|
| **Must have** | Without this, the output doesn't meet its purpose |
| **Should have** | Important but the output works without it; do if time allows |
| **Could have** | Nice to have; lowest priority |
| **Won't have** | Explicitly out of scope for this iteration |

This technique also surfaces hidden requirements — stakeholders often realise "must haves" they hadn't mentioned until asked to classify.

---

## Technique 4: The Anti-Requirements Question

Use to uncover constraints and non-goals.

**Ask:** "What would be wrong with this analysis that would make you reject it?"

Common answers reveal:
- Data sources they don't trust
- Segments that must or must not be included
- Prior analyses they want this to be comparable to
- Formatting or delivery constraints

---

## Technique 5: Show-Don't-Tell (Prototype First)

Use for ambiguous visual or formatting requirements.

**Process:** Build a rough mock-up (even a sketch) and show it before writing any queries.

"Does this structure match what you had in mind? What would you change?"

This is faster than iterating on a complete analysis and surfaces format requirements early.

---

## Handling Scope Creep During Requirements

Signs that scope is expanding beyond what was agreed:
- "And while you're at it, can you also..."
- "Actually, can we add [segment] to this?"
- "I showed this to my manager and they want to see X as well"

Response:
1. Acknowledge the new request.
2. Assess impact: "That would add approximately [X hours] to the timeline."
3. Offer a choice: "Should I prioritise this over the original ask, or should I log it for a follow-up?"
4. Document the decision.

---

## Red Flags in Requirements

| Red flag | What it usually means |
|---|---|
| "I'll know what I want when I see it" | No clear success criterion — do a prototype before committing to a full analysis |
| "As fast as possible" | No agreed deadline — confirm a specific date |
| "All the data you can get" | Scope is undefined — narrow to a specific question |
| "The same thing we do every month" | Undocumented recurring process — document it now before you inherit it |
| "The CEO wants this" | High stakes — clarify the exact question and format the CEO needs |

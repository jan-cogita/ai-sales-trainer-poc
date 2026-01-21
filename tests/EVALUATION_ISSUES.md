# Evaluation System Issues

*Detected during integration testing on 2026-01-20*

---

## Overview

The persona agent is working well, but the evaluation/scoring system has several issues that need to be addressed post-PoC.

---

## Issue 1: Live Conversation vs Transcript Scoring Discrepancy

### Description
The same "premature pitch" conversation scores very differently depending on evaluation method:

| Evaluation Method | Score |
|-------------------|-------|
| Transcript evaluation (static) | 17.5% (7/40) |
| Live conversation evaluation | 6.0/10 (60%) |

### Expected Behavior
Both should score similarly low for poor sales technique.

### Root Cause (Suspected)
The live conversation evaluator may be:
1. Evaluating the combined transcript (including persona responses) rather than just salesperson messages
2. Using different scoring criteria than the transcript evaluator

### Fix Recommendation
1. Review the live conversation evaluation prompt in `app/services/`
2. Ensure it only evaluates the salesperson's (user's) messages
3. Align scoring criteria between transcript and live evaluators

---

## Issue 2: Dimension Scores Don't Match Salesperson Behavior

### Description
In the premature pitch live conversation test, dimensions received high scores despite poor salesperson performance:

| Dimension | Actual Score | Expected Score | Issue |
|-----------|--------------|----------------|-------|
| Question Quality | 9/10 | 2-3/10 | Salesperson asked almost no questions |
| SPIN Sequence | 9/10 | 1-2/10 | No SPIN progression occurred |

### Evidence
The salesperson's messages were mostly pitching:
- *"Let me tell you what we offer - our platform provides 99.9% uptime..."*
- *"Our solution is ideal for modernizing legacy infrastructure..."*
- *"We can provide you with a great deal if you sign up this quarter..."*

### Root Cause (Suspected)
The evaluator is likely scoring the **persona's questions back to the salesperson** rather than the salesperson's questioning technique.

### Fix Recommendation
1. Modify the evaluation prompt to explicitly score only messages with role="user" (salesperson)
2. Add clear instructions: "Evaluate ONLY the salesperson's messages, ignore customer responses for scoring purposes"
3. Consider pre-filtering the transcript to include only salesperson messages before evaluation

---

## Issue 3: Monetization Quality Scoring Bug

### Description
The "excellent discovery" conversation received a low Monetization Quality score despite containing extensive quantification.

| Dimension | Score | Feedback |
|-----------|-------|----------|
| Monetization Quality | 4/10 | *"Missing problem monetization. Ask 'How much does this cost you?'"* |

### Evidence of Monetization Present
The conversation actually contained:
- "EUR 15,000 per hour in lost production"
- "EUR 4 million at risk"
- "EUR 500,000 in contracts"
- "EUR 8,000 extra per month in overtime"

### Root Cause (Suspected)
The evaluator may be:
1. Looking for specific phrases like "How much does this cost?" rather than recognizing monetization in responses
2. Only checking salesperson messages, not recognizing that monetization was successfully elicited

### Fix Recommendation
1. Update Monetization Quality criteria to recognize when the customer provides quantified impacts
2. The goal is to GET monetization info, not just ASK for it - successful elicitation should score high
3. Review the evaluation prompt for this dimension

---

## Issue 4: Evaluation Dimensions May Need Restructuring

### Current Dimensions (Live Conversation)
1. Patience
2. Implication Depth
3. Client Talk Ratio
4. Question Quality
5. SPIN Sequence
6. Vocabulary Compliance
7. Monetization Quality

### Current Dimensions (Transcript Evaluation)
1. Situation Questions
2. Problem Questions
3. Implication Questions
4. Need-Payoff Questions

### Problem
The two evaluation systems use different dimension sets, making comparison difficult.

### Fix Recommendation
1. Consider unifying the dimension structure across both evaluators
2. Alternatively, clearly document why different dimensions are used
3. Ensure dimension definitions are consistent with SPIN/sales methodology

---

## Issue 5: Implication Depth Scored Too High for Premature Pitch

### Description
The premature pitch live conversation scored 7/10 on "Implication Depth" despite no implication questions being asked by the salesperson.

### Evidence
Salesperson messages contained zero implication questions. The persona asked clarifying questions, but the salesperson didn't explore implications.

### Fix Recommendation
Same as Issue 2 - ensure evaluator scores only salesperson behavior.

---

## Components Working Correctly

For reference, these components performed well:

### Persona Agent
- Correctly shows skepticism to forbidden vocabulary
- Opens up with disarming phrases
- Shows impatience with excessive situation questions
- Reveals deeper information with implication questions
- Pushes back on premature pitching
- Shares quantified data when asked properly (analytical persona)
- References past negative experiences (skeptical persona)

### Transcript Evaluation (Standalone)
- Correctly scores excellent discovery at 85%
- Correctly scores premature pitch at 17.5%
- Provides specific, actionable feedback per SPIN category
- Feedback text is helpful and accurate

---

## Priority Order for Fixes

1. **HIGH**: Issue 2 - Dimension scores evaluating wrong party
2. **HIGH**: Issue 1 - Live vs transcript scoring discrepancy
3. **MEDIUM**: Issue 3 - Monetization scoring bug
4. **LOW**: Issue 4 - Dimension structure alignment
5. **LOW**: Issue 5 - Implication depth (likely fixed by Issue 2)

---

## Test Files for Reference

Outputs that demonstrate these issues are saved in:
```
tests/outputs/2026-01-20_22-16-15/
├── conversation_flow/
│   ├── test_excellent_conversation_flow.json    # Shows Issue 3
│   └── test_premature_pitch_conversation_flow.json  # Shows Issues 1, 2, 5
└── evaluation_endpoint/
    ├── test_excellent_discovery_transcript_evaluation.json  # Working correctly
    └── test_premature_pitch_transcript_evaluation.json  # Working correctly
```

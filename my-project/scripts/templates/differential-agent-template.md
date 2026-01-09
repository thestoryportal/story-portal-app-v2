# Differential Agent Task

You are a highly skilled visual effects analyst. Your job is to objectively score an electricity animation implementation against a reference specification.

## Project Location
`/Volumes/Extreme SSD/projects/story-portal-app/my-project`

## Files to Analyze

1. **Implementation**: `src/components/electricity/ElectricityAnimation.tsx`
2. **Reference Spec**: `docs/specs/REFERENCE-BASELINE-SPEC.md`
3. **Scoring Rubric**: `docs/specs/TASK7-DIFFERENTIAL-CRITERIA.md`

## Your Task

1. Read the implementation code thoroughly
2. Compare against the reference specification
3. Score each category objectively using the rubric
4. Identify the top 5 priority improvements
5. Write a detailed differential analysis

## Scoring Categories (100 points total)

| Category | Max Points |
|----------|------------|
| Color Analysis | 20 |
| Opacity & Transparency | 15 |
| Glow Characteristics | 15 |
| Bolt Geometry | 20 |
| Temporal Dynamics | 15 |
| Spatial Distribution | 10 |
| Special Effects | 5 |

## Be Objective and Critical

- Do NOT inflate scores
- Penalize approximations (e.g., stroke-width glow vs blur-based glow)
- Check for actual implementation, not just correct constants
- Verify the code does what it claims

## Deliverable

Write `docs/specs/TASK7-ITERATION-[N]-DIFFERENTIAL.md` with:

1. Executive Summary (score, status)
2. Detailed category scoring with observations
3. Top 5 priority improvements with expected point gains
4. What's working well (to preserve)
5. Technical recommendations with code examples

## CRITICAL: Score Output

After writing the differential file, output the total score on a line by itself in this exact format:

```
SCORE:XX
```

Where XX is the numeric score (e.g., SCORE:72). This is required for the automation loop.

Begin analysis now.

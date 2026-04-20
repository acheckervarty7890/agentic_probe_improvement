---
mode: ask
description: "Generate one red-team batch for binary probe failure search"
---

Generate a JSON object with `prompts` only.

Context:
- error_type: ${input:errorType}
- pos_label: ${input:posLabel}
- neg_label: ${input:negLabel}
- classifier_description: ${input:classifierDescription}
- prior_feedback: ${input:priorFeedback}
- batch_size: ${input:batchSize}

Rules:
1. Return exactly batch_size prompts.
2. Optimize for classifier mistakes and diversity.
3. Avoid duplicates.

Output JSON schema:
{
  "prompts": ["...", "..."]
}

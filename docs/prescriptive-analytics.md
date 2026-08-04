# Prescriptive Analytics Engine

This document explains the scenario simulation pipelines, business rule validations, and actions prioritization logic of the Prescriptive Analytics Engine.

## ⚙️ Prescriptive Workflow Flowchart

The prescriptive engine optimizes outputs by simulating permutations of actionable features inside target constraints:

```
    [Baseline State & Actionable Columns]
                      │
                      ▼
        [Scenario Permutations Grid]
                      │
                      ▼
      [Trained Model inference Runner]
                      │
                      ▼
     [Business Rules & Bounds Validator]
                      │
                      ▼
    [Improvement Deltas Prioritization]
                      │
                      ▼
  [Ranked Optimization Recommendations List]
```

---

## 1. What-If Scenario Simulations

- **Simulate Scenario**: Computes predicted outcome probabilities by merging a baseline dictionary with modified parameter variables and running them through the active model.
- **Actionable Features**: Restricts simulations to variables defined as actionable (e.g. users can modify *discount rate* or *contract length*, but cannot modify a customer's *age*).

---

## 2. Recommendation Prioritization & Constraints

1. **Business Rules**: Validates permutations against bounds (e.g. discount rules between 0% and 30% bounds). Custom inputs violating rules are filtered out.
2. **Delta Ranking**: Calculates improvement delta:
   $$\Delta = \text{Simulated Score} - \text{Baseline Score}$$
   - *Minimize targets* (e.g. churn risk probabilities): maximizes negative deltas.
   - *Maximize targets* (e.g. sales/revenue): maximizes positive deltas.
3. **Ranked output**: Output array lists feature, target action value, baseline value, score improvement, and customer-facing business rationale.

---

## 3. Workflows & Copilot Integrations

- **Workflows Builder**: native `prescriptive_analysis` node type executing prescriptive runs dynamically.
- **AI Copilot**: Automatically triggers prescriptive scans when queries contain action keywords (e.g., *"recommend actions to reduce churn"*).

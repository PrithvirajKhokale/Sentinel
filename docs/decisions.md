# Sentinel — Technical Decisions

## Decision 001 — Use XGBoost as a Candidate Model

### Context
The system requires predictive modelling for project risk.

### Alternatives
- Baseline model
- Random Forest
- XGBoost

### Decision
Evaluate all candidates and select the final model based on validation performance.

### Reason
The final selection should be evidence-based rather than assuming one algorithm will perform best.
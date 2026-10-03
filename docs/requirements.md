# Sentinel — System Requirements

## 1. Problem Definition

Traditional project monitoring is primarily focused on reporting the current status of projects.

Sentinel aims to introduce a predictive layer that uses historical and current project information to estimate future project risks before significant delays or cost overruns become evident.

The system is intended to support decision-making and prioritization. A prediction represents an estimated risk and must not be presented as a certain future outcome.

## 2. Objectives

The system shall:

1. Ingest project monitoring data.
2. Validate and preprocess project data.
3. Engineer predictive features from available project information.
4. Estimate the probability of time overruns.
5. Estimate expected project delay.
6. Estimate the probability of cost overruns.
7. Provide an optional estimate of expected cost overrun percentage.
8. Generate an overall project risk score.
9. Categorize projects into risk bands.
10. Explain the major factors contributing to a prediction.
11. Provide project-level and portfolio-level monitoring.
12. Allow users to filter and prioritize projects based on risk.
13. Present trends and relevant project analytics through a dashboard.

## 3. Data Context

The system is designed around historical project-monitoring information associated with infrastructure projects, including PAIMANA/OCMS data.

Relevant information may include:

- Project ID
- Ministry
- Sector
- Project cost
- Expenditure
- Project start date
- Expected completion date
- Current/projected completion information
- Planned physical progress
- Actual physical progress
- Milestones
- Issues
- Historical project snapshots

## 4. Primary Outputs

For each project, Sentinel should produce:

- Time-overrun probability
- Expected delay
- Cost-overrun probability
- Optional expected cost-overrun percentage
- Overall risk score
- Risk category
- Major factors contributing to the prediction

## 5. Risk Categories

The system will use configurable risk bands such as:

- LOW
- MEDIUM
- HIGH
- CRITICAL

The exact thresholds should be documented when finalized.

## 6. Risk Score

The overall risk score combines relevant risk dimensions.

An initial example discussed for the system is:

Overall Risk Score =
0.5 × Time Risk + 0.5 × Cost Risk

The weighting and thresholds should remain configurable rather than being hard-coded as a permanent assumption.

## 7. Explainability

The system should provide explanations for predictions using SHAP.

The purpose is to show which project characteristics contributed to increasing or decreasing the predicted risk.

## 8. Non-Functional Requirements

### Explainability
Predictions should be accompanied by interpretable information about their major contributing factors.

### Reliability
The system should validate incoming data before using it for prediction.

### Maintainability
The ML, backend, frontend, and database components should remain modular.

### Scalability
The architecture should allow additional projects and historical observations to be incorporated.

### Security
Sensitive configuration values and credentials must not be committed to the repository.

## 9. Limitations

Sentinel provides predictive estimates rather than guaranteed outcomes.

Model performance depends on the quality, completeness, and representativeness of the available project data.
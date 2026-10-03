# Sentinel — Development Plan

## 1. Development Methodology

Sentinel will use a hybrid Agile and stage-gated development approach.

Agile practices will allow the team to develop and integrate the system incrementally.

Stage gates will prevent major components from progressing before their
required foundations have been validated.

## 2. Team Responsibilities

### Person 1 — AI/ML + Data
Primary responsibility:
- Data exploration
- Data cleaning
- Feature engineering
- ML experimentation
- Model training
- Model evaluation
- SHAP explainability

### Person 2 — Backend + Database/MLOps
Primary responsibility:
- FastAPI backend
- API implementation
- PostgreSQL
- SQLAlchemy
- Backend integration with ML
- Docker/deployment infrastructure
- Backend testing

### Person 3 — Frontend + Product
Primary responsibility:
- React/Next.js dashboard
- UI/UX
- Project portfolio view
- Project intelligence interface
- Risk visualization
- Alerts and filtering
- Frontend/backend integration

### Shared Responsibilities

All members participate in:

- GitHub workflow
- Code review
- Testing
- Integration
- Documentation
- Final presentation and demonstration

## 3. Development Stages

### Stage 1 — Problem and Data Understanding
Validate the problem, data availability, fields, and expected outputs.

### Stage 2 — Data Contract
Define the expected input structure and validation rules.

### Stage 3 — Features and Targets
Finalize prediction targets and feature definitions.

### Stage 4 — ML Validation
Train baseline and candidate models and evaluate them.

### Stage 5 — API
Expose validated prediction functionality through FastAPI.

### Stage 6 — Frontend
Build the dashboard and project intelligence interface.

### Stage 7 — End-to-End Integration
Connect data, ML, API, and frontend.

### Stage 8 — Hardening
Testing, error handling, validation, performance, and documentation.

### Stage 9 — Demo and Presentation
Prepare the final demonstration and technical explanation.

## 4. Git Workflow

The `main` branch should always contain working code.

Team members should not directly push to `main`.

Feature branches should be used for development, followed by:

Feature branch → Pull Request → Code Review → Tests → Merge

Example branches:

- feature/frontend
- feature/ml-model
- feature/backend-api
- feature/data-pipeline
- feature/dashboard
- feature/alerts
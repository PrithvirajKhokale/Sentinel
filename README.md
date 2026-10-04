# Sentinel

AI-Driven Predictive Infrastructure Project Monitoring System

Sentinel is a web-based predictive monitoring platform developed for Smart India Hackathon problem statement SIH26103.

The system is designed to analyze infrastructure project monitoring data, identify projects at risk of schedule delay or cost overrun, explain the primary risk drivers, and provide an early-warning dashboard for decision support.

## Problem

Conventional project monitoring is primarily reactive. Sentinel aims to provide an early-warning layer by using historical and current project information to estimate the probability of future project delays and cost overruns.

## Core Capabilities

- Project data ingestion and validation
- Data preprocessing and feature engineering
- Schedule-delay prediction
- Cost-overrun prediction
- Project-level risk scoring
- Explainable AI using SHAP
- Portfolio-level risk dashboard
- Project-level intelligence dashboard
- Early-warning indicators
- Model performance evaluation
- Optional natural-language project assistant

## Architecture

```text
Project Data
     |
     v
Data Pipeline
     |
     v
Feature Engineering
     |
     v
ML Models
     |
     +------------------+
     |                  |
     v                  v
Risk Engine        Explainability
     |                  |
     +--------+---------+
              |
              v
           FastAPI
              |
              v
       Web Dashboard
```

## Local monitoring backend

See [local setup, migrations, validated import and API checks](docs/backend-local.md). The backend provides project list/detail, history and portfolio-summary endpoints on loopback only, without predictions or shared deployment.

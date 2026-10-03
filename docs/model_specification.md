# Sentinel — Model Specification

## 1. Purpose

This document defines the predictive modelling requirements for Sentinel.

Sentinel uses machine learning to estimate future project risk from historical and current project information.

Predictions are intended to support decision-making and prioritization. They must not be presented as guaranteed outcomes.

---

## 2. Prediction Tasks

### 2.1 Time Overrun Probability

Estimate the probability that a project will experience a time overrun.

Output:

```text
time_overrun_probability
```

Historical PAIMANA/OCMS Data
             ↓
      Data Cleaning
             ↓
       Validation
             ↓
     Feature Engineering
             ↓
    ┌────────┴────────┐
    ↓                 ↓
Baseline         ML Models
                 Random Forest
                 XGBoost
    └────────┬────────┘
             ↓
     Risk Predictions
             ↓
   Deterministic Risk Score
             ↓
       SHAP Explanation
             ↓
       FastAPI Backend
             ↓
    React / Next.js UI
             ↓
      Sentinel Dashboard
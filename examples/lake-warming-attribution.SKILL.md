---
name: analyze water temperature trends
description: Analyze lake water temperature trend and identify dominant driving factors using factor analysis
---
## Steps
1. 1. Load all data files: water_temperature.csv, climate.csv, land_cover.csv, hydrology.csv from /root/data/
2. 2. Calculate water temperature trend using scipy.stats.linregress (year vs mean water temp), extract slope and p-value
3. 3. Save trend_result.csv with columns 'slope' and 'p-value' to /root/output/
4. 4. Classify all predictor variables into 4 categories: Heat (air_temp, radiation), Flow (precipitation, inflow/outflow), Wind (wind_speed), Human (land_cover percentages)
5. 5. Standardize all variables using StandardScaler, then run FactorAnalyzer(n_factors=4, rotation='varimax') on scaled data
6. 6. Map factors to categories by examining loadings, calculate factor scores using fa.transform(X_scaled)
7. 7. Perform R² decomposition with LinearRegression: fit on all factor scores, calculate each factor's contribution
8. 8. Output dominant_factor.csv with 'variable' (most important category) and 'contribution' (percentage) to /root/output/
## Constraints
- Use scipy.stats.linregress for trend analysis
- Run ONE global FactorAnalyzer on all variables, not separate per category
- Standardize data before factor analysis using StandardScaler
- Output only the most important variable in dominant_factor.csv
## Dependencies
- pandas
- numpy
- scipy.stats.linregress
- sklearn.preprocessing.StandardScaler
- sklearn.linear_model.LinearRegression
- factor_analyzer.FactorAnalyzer
## Examples
- Example 1: {"input": "Water temperature data with years as index", "output": "trend_result.csv with slope=0.023 and p-value=0.003"}
- Example 2: {"input": "Factor scores and water temperature trend", "output": "Heat contributes 45.2%, Flow 28.1%, Wind 15.3%, Human 11.4%"}

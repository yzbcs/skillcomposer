---
name: temperature controller implementation
description: Implement PI temperature controller with calibration, parameter estimation, and closed-loop control
---
## Steps
1. 1. Verify simulator environment and check initial temperature is within 16-20°C range
2. 2. Run calibration test: apply 50% heater power step, collect data for 30+ seconds with 20+ points (sampling 0.5-1.5s)
3. 3. Save calibration_log.json with phase='calibration', heater_power_test=50.0, and full data array
4. 4. Load calibration data, extract ambient temp (y_ambient), fit first-order model: y(t) = y_ambient + K*u*(1-exp(-t/tau))
5. 5. Compute K = (y_steady - y_ambient)/u, tau from curve_fit, calculate r_squared and RMSE as quality metrics
6. 6. Save estimated_params.json with K, tau, r_squared, fitting_error
7. 7. Calculate PI gains: lambda=tau, Kp=tau/(K*lambda), Ki=1/(K*lambda), Kd=0
8. 8. Save tuned_gains.json with Kp, Ki, Kd, lambda
9. 9. Implement PI controller with anti-windup, setpoint=22.0°C
10. 10. Run closed-loop control: compute error, PI output, clamp to 0-100%, log all values
11. 11. Safety check: verify temperature valid (not NaN), clamp output before each step, ensure max_temp<30°C
12. 12. Continue control for >=150s until steady-state
13. 13. Save control_log.json with phase='control', setpoint, and data array (time, temperature, setpoint, heater_power, error)
14. 14. Calculate metrics: rise_time (90% of setpoint), overshoot=(max_temp-setpoint)/setpoint, settling_time (within 0.5°C), steady_state_error, max_temp
15. 15. Save metrics.json
## Constraints
- Calibration: >=30s duration, 20+ data points, 50% heater power step
- Sample rate: 0.5-1.5 seconds per sample
- Temperature measurement must be valid (not NaN/inf) before control output
- Output always clamped to 0-100% range (fail-safe)
- Safety check BEFORE applying any control output
- Control duration >=150s
- Steady-state error <0.5°C, settling time <120s, overshoot <10%
- Kd=0 for first-order systems, implement integral anti-windup
- Parameter bounds in curve_fit must constrain to physically valid solutions
- R-squared target >0.9 for quality fitting
## Dependencies
- numpy
- scipy.optimize.curve_fit
- hvac_simulator
## Examples
- Example 1: {"input": "Calibration with 50% heater power from ~18°C ambient, collecting 30s of data", "output": "calibration_log.json with phase='calibration', heater_power_test=50.0, 20+ data points"}
- Example 2: {"input": "K=0.05, tau=10.0, lambda=10.0", "output": "tuned_gains.json: Kp=20.0, Ki=2.0, Kd=0.0"}

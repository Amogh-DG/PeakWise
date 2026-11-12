# Assumptions — Person B

## B-4 missed peaks

- Heatwave threshold: target day maximum temperature (`wx_temp_c`) exceeds the 95th percentile of daily maximum temperatures observed for that season in the training period (historical data before forecast origin).
- Weather miss threshold: absolute difference between actual daily maximum temperature and forecast weather proxy maximum temperature exceeds 2.0 °C.
- Festival window: `cal_is_festival_window` flag active (target day within ±2 days of a festival).
- Holiday: `cal_is_holiday` flag active on the target date.
- Weekend: `cal_is_weekend` flag active (Saturday or Sunday).
- Default tag: "other" applied when none of the specific event or weather conditions are triggered.

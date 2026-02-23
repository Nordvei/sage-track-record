# SAGE Track Record

Public, timestamped predictions for Norwegian energy spot prices (NO1-NO5).
Resolved daily against Nord Pool day-ahead auction results.

## Files
- `predictions.csv` — Every prediction with timestamp (before market close)
- `actuals.csv` — Actual prices from Nord Pool
- `accuracy_log.csv` — Running accuracy by zone, week, month

## How to verify
1. Check prediction timestamp vs Nord Pool publication time
2. Compare predicted direction vs actual price movement
3. Git history proves no retroactive edits

## Current accuracy
Updated daily at 14:00 CET.

## Source
- Predictions: [SAGE](https://infinity-folder.no)
- Actuals: [Nord Pool](https://data.nordpoolgroup.com)

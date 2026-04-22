---
name: associate seismic phases
description: Detect P/S waves with SeisBench and group into events using GaMMA association
---
## Steps
1. Install: pip install seisbench obspy pandas numpy pyproj scipy scikit-learn GaMMA
2. Load data: stream=obspy.read('/root/data/wave.mseed'); stations_df=pd.read_csv('/root/data/stations.csv')
3. Preprocess: multiply traces by 1e10 if max amp < 1e-10, normalize traces
4. Phase picking: model=seisbench.models.PhaseNet.from_pretrained('original'); annotations=model.annotate(stream)
5. Extract picks: iterate traces, find peaks in prob_p and prob_s traces, create picks_df with columns [id, timestamp, type, prob]
6. Convert coords: proj=pyproj.Proj(f'+proj=utm +zone={zone} +ellps=WGS84'); x_km,y_km=proj(lon,lat)
7. GaMMA input: stations_df with [id, x_km, y_km, z_km] where z_km=-elevation_m/1000
8. Config: dims=['x(km)','y(km)','z(km)'], min_picks_per_eq=3, use_dbscan=True, dbscan_eps=15, dbscan_min_samples=3
9. Run association: events,assignments=association(picks_df,stations_df,config,method='gamma')
10. Output: write CSV with 'time' column in ISO format (YYYY-MM-DDTHH:MM:SS.ffffff)
## Constraints
- Timestamps must be UTC ISO format without timezone
- Station id format: network.station.channel must match between picks and stations
- Coordinates in km (projected local system, not lat/lon)
- z_km = -elevation_m/1000 (depth below surface)
- Phase type lowercase: 'p' or 's'
- Multiply tiny waveforms by 1e10 before processing
- Events matched to ground truth if time diff < 5 seconds
- F1 score must be >= 0.6
## Dependencies
- obspy (MSEED I/O)
- seisbench (PhaseNet deep learning picker)
- pytorch (SeisBench backend)
- pandas (DataFrame)
- pyproj (coord projection)
- scipy,numpy,scikit-learn (GaMMA)
- GaMMA: pip install git+https://github.com/wayneweiqiang/GaMMA.git
## Examples
- Example 1: {"input": "stream=obspy.read('/root/data/wave.mseed'); model=seisbench.models.PhaseNet.from_pretrained('original'); picks_df=model.annotate(stream)", "output": "Picks DataFrame with columns [id, timestamp, type, prob] for P and S waves"}
- Example 2: {"input": "events,assignments=association(picks_df,stations_df,config,method='gamma')", "output": "List of detected events with time, location, and associated picks"}

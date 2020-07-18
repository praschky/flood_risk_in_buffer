# flood_risk_in_buffer
Python Script to calculate average flood risk in a buffer around a point location.
This is an application for Bangladesh.

In collaboration with Shaun Ashbury


## 1. Download SRTM 1 tiles.

Manually selected and downloaded 9 tiles from http://dwtkns.com/srtm30m/:

- N23E090.hgt
- N23E089.hgt
- N23E088.hgt
- N22E090.hgt
- N22E089.hgt
- N22E088.hgt
- N21E090.hgt
- N21E089.hgt
- N21E088.hgt


## 2. SRTM processing.

The below commands were ran in an Ubuntu 18.04 docker container with GDAL and dependancies installed:

### Set project working directory.
cd PATH

### Merge SRTM tiles.
gdal_merge.py -co BIGTIFF=YES -co COMPRESS=LZW -o output-data/sw-bangladesh-dem.tif $(ls input-data/\*.hgt)

### Using QGIS 3, filled sinks with the SAGA Sink Fill (Wang & Liu) tool (processing toolbox), saving result to memory, then exported to sw-bangladesh-dem-filled.tif. Reviewing the result, watercourses appear to now have an elevation of less than 1.0 (these were mostly 0 in the SRTM input).

### Set values <1 as water, to extract watercourses (only needed for visualization).
gdal_calc.py --calc=expression --calc "(A < 1)" --co BIGTIFF=YES --co COMPRESS=LZW  --outfile=output-data/sw-bangladesh-water.tif -A output-data/sw-bangladesh-dem-filled.tif

### Set values <1 to 0, and others to -1, to set a baseline water level.
gdal_calc.py --calc=expression --calc "((A < 1) - 1) + ((A >= 1) * A)" --co BIGTIFF=YES --co COMPRESS=LZW  --outfile=output-data/sw-bangladesh-water-level.tif -A output-data/sw-bangladesh-dem-filled.tif

### Calculate flood pixels at +1m, +2m, and +3m thresholds from the baseline.
gdal_calc.py --calc=expression --calc "(A <= 1)" --co BIGTIFF=YES --co COMPRESS=LZW  --outfile=output-data/sw-bangladesh-1m-flood.tif -A output-data/sw-bangladesh-water-level.tif

gdal_calc.py --calc=expression --calc "(A <= 2)" --co BIGTIFF=YES --co COMPRESS=LZW  --outfile=output-data/sw-bangladesh-2m-flood.tif -A output-data/sw-bangladesh-water-level.tif

gdal_calc.py --calc=expression --calc "(A <= 3)" --co BIGTIFF=YES --co COMPRESS=LZW  --outfile=output-data/sw-bangladesh-3m-flood.tif -A output-data/sw-bangladesh-water-level.tif


## 3. Spatial analysis.

Ran Python script to create buffered points in a virtualenv with GDAL installed as:

source ~/workspace/envs/gis/bin/activate

cd ~PATH

python3 PATH/calculate_flood_risk.py -i input-data/treatment_places.txt -o output-data/treatment_places_flood_risk.csv $(ls output-data/sw-bangladesh-[0-9]m-flood.tif)

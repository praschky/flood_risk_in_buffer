#!/usr/bin/env python3

"""
calculate_flood_risk.py

By Shaun Astbury (shaun@shaunastbury.com)

Python 3 script to calculate average flood risk for buffered points.

"""

# Import required modules.
import csv
import argparse
from osgeo import gdal, osr, ogr

# Add command line arguments.
parser = argparse.ArgumentParser(description='Calculate average flood risk for buffered points.')
parser.add_argument('--input_csv', '-i', type=str, nargs='?', required=True, help='Input csv file with point locations.')
parser.add_argument('--output_csv', '-o', type=str, nargs='?', required=True, help='Output csv file to save results to.')
parser.add_argument('--source_srid', '-s', type=int, nargs='?', required=False, default=4326, help='EPSG code of input points.')
parser.add_argument('--target_srid', '-t', type=int, nargs='?', required=False, default=3106, help='EPSG code of projection to use for buffer.')
parser.add_argument('--lat_col', '-y', type=str, nargs='?', required=False, default='lat', help='Latitude column in the input csv.')
parser.add_argument('--lng_col', '-x', type=str, nargs='?', required=False, default='lon', help='Longitude column in the input csv.')
parser.add_argument('--buffer_dist', '-d', type=int, nargs='?', required=False, default=1000, help='Buffer distance, in units of the selected projection.')
parser.add_argument('--flood_risk_names', '-n', type=str, nargs='+', required=False, default=['avg_1m', 'avg_2m', 'avg_3m'], help='Columns to append to csv table header, should equal the numbert of flood risk files.')
parser.add_argument('flood_risk_files', type=str, nargs='+', help='Flood risk files to process.')

# Parse arguments.
args = parser.parse_args()
input_csv = args.input_csv
output_csv = args.output_csv
source_srid = args.source_srid
target_srid = args.target_srid
lat_col = args.lat_col
lng_col = args.lng_col
buffer_dist = args.buffer_dist
flood_risk_names = args.flood_risk_names
flood_risk_files = args.flood_risk_files

# Read flood risk files to memory, taking spatial ref info from first (this
# assumes the rasters are aligned and equal projections, which they should be).
raster_data = []
raster = flood_risk_files[0]
ds = gdal.Open(raster)
geotransform = ds.GetGeoTransform()
x_origin = geotransform[0]
y_origin = geotransform[3]
cell_width = geotransform[1]
cell_height = geotransform[5]
raster_sr = ds.GetProjection()
band = ds.GetRasterBand(1)
nodata = band.GetNoDataValue()
x_size = band.XSize
y_size = band.YSize
arr = band.ReadAsArray()
raster_data.append(arr)

# Read other files (if any).
for raster in flood_risk_files[1:]:
    ds = gdal.Open(raster)
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    raster_data.append(arr)

# Set up transforms.
source_sr = osr.SpatialReference()
source_sr.ImportFromEPSG(source_srid)
buffer_sr = osr.SpatialReference()
buffer_sr.ImportFromEPSG(target_srid)
buffer_transform = osr.CoordinateTransformation(source_sr, buffer_sr)
target_sr = osr.SpatialReference()
target_sr.ImportFromWkt(raster_sr)
raster_transform = osr.CoordinateTransformation(buffer_sr, target_sr)

# Open output csv file.
out_file = open(output_csv, 'w', newline='')
writer = csv.writer(out_file)

# Read csv records.
in_file = open(input_csv, newline='')
reader = csv.reader(in_file)
first = True
for row in reader:
    if first:
        lng_idx = row.index(lng_col)
        lat_idx = row.index(lat_col)
        row = row + flood_risk_names
        first = False
    else:
        lng = float(row[lng_idx])
        lat = float(row[lat_idx])

        # Create point, transform, buffer, then transform back.
        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint(lng, lat)
        pt.Transform(buffer_transform)
        poly = pt.Buffer(buffer_dist)
        poly.Transform(raster_transform)

        # Create single feature in-memory layer for polygon.
        driver = ogr.GetDriverByName('MEMORY')
        poly_ds = driver.CreateDataSource('temp')
        lyr = poly_ds.CreateLayer('temp', srs=target_sr)
        defn = lyr.GetLayerDefn()
        feat = ogr.Feature(defn)
        feat.SetGeometry(poly.Clone())
        lyr.CreateFeature(feat)

        # Create polygon raster and read to array.
        driver = gdal.GetDriverByName('MEM')
        ds = driver.Create('', x_size, y_size, 1, gdal.GDT_Byte)
        ds.SetGeoTransform(geotransform)
        band = ds.GetRasterBand(1)
        band.SetNoDataValue(0)
        ds.SetProjection(raster_sr)
        gdal.RasterizeLayer(ds, [1], lyr)
        arr = band.ReadAsArray()
        lyr = None
        poly_ds = None
        band = None
        ds = None

        # Extract flood risk mask.
        sel = arr == 255
        for raster in raster_data:
            mask = raster[sel]
            val = mask.mean()
            row.append(val)
    writer.writerow(row)

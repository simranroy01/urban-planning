from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import ee
import geemap
import rasterio
import numpy as np
import pandas as pd
import os
from PIL import Image

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ensure necessary directories exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Initialize Google Earth Engine
try:
    ee.Initialize(project='ee-simranroy186')
except ee.EEException:
    ee.Authenticate()
    ee.Initialize()

@app.get("/", response_class=HTMLResponse)
async def serve_homepage():
    with open("templates/index.html", "r") as file:
        return HTMLResponse(content=file.read())

@app.post("/process")
async def process(request: Request):
    try:
        data = await request.json()
        print("Received Data:", data)

        if "bounds" not in data:
            raise HTTPException(status_code=400, detail="Invalid request. 'bounds' key is missing.")

        bounds = data["bounds"]
        roi = ee.Geometry.Rectangle(bounds)

        # Fetch and process landcover data
        vis_params = {
            "min": 1,
            "max": 9,
            "palette": ["#1A5BAB", "#358221", "#87D19E", "#FFDB5C", "#ED022A", "#EDE9E4", "#F2FAFF", "#C8C8C8", "#C6AD8D"]
        }
        lc = ee.ImageCollection('projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS')\
            .filterDate('2017-01-01', '2017-12-31').mosaic()\
            .remap([1,2,4,5,7,8,9,10,11],[1,2,3,4,5,6,7,8,9]).rename('lc')

        landcover = lc.clip(roi).visualize(**vis_params)
        landcover_png = "static/landcover.png"

        # Export landcover image
        try:
            print("Exporting landcover image...")
            geemap.ee_export_image(landcover, filename=landcover_png, scale=30)
            print("Export completed:", landcover_png)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Landcover export failed: {str(e)}")

        # ✅ Population Data Extraction
        pop_collection = ee.ImageCollection("JRC/GHSL/P2023A/GHS_POP").filterBounds(roi)

        def pop_count(img):
            pop_sum = img.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,  # Increased scale
                maxPixels=1e13,
                bestEffort=True
            ).get("population_count")  # Corrected band name

            date = img.date().format('YYYY-MM-dd')
            return ee.Feature(None, {'date': date, 'pop': pop_sum})

        pop_values = pop_collection.map(pop_count)
        feature_list = pop_values.toList(pop_values.size()).getInfo()

        if not feature_list:
            print("⚠️ No population data found for this region!")

        date = [item['properties']['date'] for item in feature_list if 'date' in item['properties']]
        pop_sum = [item['properties']['pop'] for item in feature_list if 'pop' in item['properties']]

        print("Extracted Dates:", date)
        print("Extracted Population Values:", pop_sum)

        if len(date) == 0 or len(pop_sum) == 0:
            raise ValueError("❌ No valid population data retrieved!")

        pop_df = pd.DataFrame({'date': pd.to_datetime(date), 'pop': pop_sum})
        pop_df["change"] = pop_df["pop"].pct_change() * 100
        pop_json = pop_df.dropna().to_dict(orient="list")

        # ✅ Built-Up Area Data Extraction
        built_collection = ee.ImageCollection("JRC/GHSL/P2023A/GHS_BUILT_S").filterBounds(roi)

        def built_area(img):
            area = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=500,
                maxPixels=1e13,
                bestEffort=True
            ).get("built_surface")

            date = img.date().format('YYYY-MM-dd')
            return ee.Feature(None, {'date': date, 'area': area})

        built_values = built_collection.map(built_area)
        built_list = built_values.toList(built_values.size()).getInfo()

        if not built_list:
            print("⚠️ No built-up area data found for this region!")

        built_dates = [entry["properties"]["date"] for entry in built_list if 'date' in entry["properties"]]
        built_areas = [entry["properties"]["area"] for entry in built_list if 'area' in entry["properties"]]

        built_df = pd.DataFrame({'date': pd.to_datetime(built_dates), 'area': built_areas})
        built_df["change"] = built_df["area"].pct_change() * 100
        built_json = built_df.dropna().to_dict(orient="list")

        return {
            "landcover": landcover_png,
            "population_data": pop_json,
            "built_area_data": built_json
        }

    except Exception as e:
        print("❌ ERROR IN /process API ❌")
        return {"error": str(e)}

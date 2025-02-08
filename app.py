from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import ee
import geemap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import os

app = FastAPI()

# Mount 'static' directory for serving CSS & JS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ensure the templates directory exists
if not os.path.exists("templates"):
    os.makedirs("templates")

# Ensure the static directory exists
if not os.path.exists("static"):
    os.makedirs("static")

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

@app.get("/message")
async def home():
    return {"message": "Welcome to the Urban Planning API"}

@app.post("/process")
async def process(request: Request):
    try:
        data = await request.json()
        if "bounds" not in data:
            raise HTTPException(status_code=400, detail="Invalid request. 'bounds' key is missing.")

        bounds = data["bounds"]
        roi = ee.Geometry.Rectangle(bounds)

        # Fetch landcover data
        lc = ee.ImageCollection('projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS')\
            .filterDate('2017-01-01', '2017-12-31').mosaic()\
            .remap([1,2,4,5,7,8,9,10,11],[1,2,3,4,5,6,7,8,9]).rename('lc')

        landcover = lc.clip(roi)
        landcover_url = 'static/landcover.tif'

        try:
            geemap.ee_export_image(landcover, filename=landcover_url, scale=30)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Landcover export failed: {str(e)}")

        # Fetch population density data
        pop = ee.ImageCollection("JRC/GHSL/P2023A/GHS_POP").mosaic().clip(roi)
        pop_values = pop.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=100,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()

        # Fetch built-up area data
        built_image = ee.ImageCollection("JRC/GHSL/P2023A/GHS_BUILT_S").select('built_surface').mosaic()
        built_clipped = built_image.clip(roi)
        built_values = built_clipped.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=100,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()

        # Create population density graph
        pop_df = pd.DataFrame({'metric': list(pop_values.keys()), 'pop': list(pop_values.values())})
        pop_img = io.BytesIO()
        pop_df.plot(kind='bar', title='Population Density').get_figure().savefig(pop_img, format='png')
        pop_img.seek(0)
        pop_plot_url = base64.b64encode(pop_img.getvalue()).decode()

        # Create built-up area graph
        built_df = pd.DataFrame({'metric': list(built_values.keys()), 'area': list(built_values.values())})
        built_img = io.BytesIO()
        built_df.plot(kind='bar', title='Built-Up Area').get_figure().savefig(built_img, format='png')
        built_img.seek(0)
        built_plot_url = base64.b64encode(built_img.getvalue()).decode()

        return {
            "landcover": landcover_url,
            "pop_graph": f"data:image/png;base64,{pop_plot_url}",
            "built_graph": f"data:image/png;base64,{built_plot_url}"
        }

    except Exception as e:
        return {"error": str(e)}




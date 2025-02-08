from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import ee
import geemap
import rasterio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import os
from PIL import Image

app = FastAPI()

# Mount 'static' directory for serving CSS & JS
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

        # Visualization parameters for landcover
        vis_params = {
            "min": 1,
            "max": 9,
            "palette": ["#1A5BAB", "#358221", "#87D19E", "#FFDB5C", "#ED022A", "#EDE9E4", "#F2FAFF", "#C8C8C8", "#C6AD8D"]
        }

        # Fetch and process landcover data
        lc = ee.ImageCollection('projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS')\
            .filterDate('2017-01-01', '2017-12-31').mosaic()\
            .remap([1,2,4,5,7,8,9,10,11],[1,2,3,4,5,6,7,8,9]).rename('lc')

        landcover = lc.clip(roi).visualize(**vis_params)
        landcover_tif = "static/landcover.tif"
        landcover_png = "static/landcover.png"

        # Export landcover as TIFF
        try:
            print("Exporting landcover image...")
            geemap.ee_export_image(landcover, filename=landcover_tif, scale=30)
            print("Export completed:", landcover_tif)

            # Convert TIF to PNG
            print("Converting .tif to .png...")
            convert_tif_to_png(landcover_tif, landcover_png)
            print("Conversion complete:", landcover_png)

        except Exception as e:
            print("Landcover Export Error:", str(e))
            raise HTTPException(status_code=500, detail=f"Landcover export failed: {str(e)}")

        return {
            "landcover": landcover_png
        }

    except Exception as e:
        print("❌ ERROR IN /process API ❌")
        return {"error": str(e)}

# Convert .tif to .png with rasterio (preserves color)
def convert_tif_to_png(input_tif, output_png):
    with rasterio.open(input_tif) as src:
        image_data = src.read()  # Read bands as a NumPy array
        
        # Normalize pixel values to 0-255
        image_data = (image_data / image_data.max()) * 255
        image_data = image_data.astype(np.uint8)

        # Convert (bands, height, width) → (height, width, bands) using np.transpose
        image_rgb = np.transpose(image_data, (1, 2, 0))

        # Save as PNG
        img = Image.fromarray(image_rgb)
        img.save(output_png)




Thermal CSV Viewer 

First public version of the CSV Thermographic Image Viewer.

Thermal CSV Viewer is a lightweight desktop application for browsing thermal camera exports stored as CSV temperature matrices. It renders them as color-mapped images with live temperature readout, distortion-free zoom, and a full region-labeling workflow (rectangular/circular areas, custom classes, selection of images to move from the folder) — all without needing the camera's proprietary software.

Features: CSV thermographic image viewing, image navigation, temperature scale adjustment, real-time statistics, multiple color palettes, histogram generation, PNG export, , image selection for moving between folders, area labeling and image rotation. 
No installation required. 

Notes:

If Windows SmartScreen displays a security warning: More Info → Run anyway.

## Interface:

<img width="792" height="711" alt="TCSV" src="https://github.com/user-attachments/assets/656366de-36fd-4b45-9270-278adcc24f40" />


## How to cite

Pagin, G. (2026).
Thermal CSV Viewer.
GitHub Repository.
https://github.com/gabripagin/Thermal-CSV-Viewer


-----

## Overview

The CSV Thermographic Image Viewer is a desktop application developed in Python for the visualization, analysis, and export of thermographic images stored in CSV matrices.

The software is designed to provide researchers, engineers, and students with a simple, intuitive interface for thermal image inspection and temperature analysis.

---

## Key Features

✔ Open folders containing multiple CSV thermographic files

✔ Navigate between thermographic images

✔ Interactive cursor for inspecting the temperature of each pixel

✔ Adjustable temperature scale

✔ Multiple thermal color palettes

✔ Zoom using the mouse wheel

✔ Real-time statistics:

- Minimum temperature
- Maximum temperature
- Average temperature
- Standard deviation

✔ Thermal histogram generation

✔ Image export in PNG format

✔ Area labeling

  
---

## Instructions
Browse folders of thermal CSVs — load an entire folder and step through images with Previous/Next or jump straight to a file by name.
Color-mapped visualization — multiple palettes (turbo, inferno, magma, plasma, viridis, jet, hot, coolwarm, gray) with adjustable min/max scale.
Live temperature readout — hover over the image to see the exact temperature at the pixel under your cursor.
Distortion-free zoom — scroll to zoom in/out; the point under your cursor stays fixed on screen (no panning/jumping), and the view never shows blank space beyond the image edges. Reset anytime with a double-click or the 0 key.
Area labeling / annotation
Draw rectangular or circular (perfect-circle) regions of interest directly on the image.
Define your own label classes and assign one to each region.
Labels are shown as a subtle, translucent overlay on the image.
All annotations are saved automatically to a CSV file next to your images (one file per folder, named after the folder) and reloaded automatically the next time you open that folder.
Adjust mode: select an existing region and either drag its edge handles to resize it (center stays fixed) or drag its middle to move it — both with a live preview before you release the mouse.
Fixed-area mode: lock new regions to a specific width/height so every labeled area is consistent, even if the region varies slightly in the raw scan.
Rename a label across every region that uses it, or delete a label (and all regions tagged with it) at once.
Batch organization — mark specific images and move them to another folder in one click (files are moved, not copied).
Image correction — flip an image vertically or horizontally directly in the CSV (useful if the sensor was mounted upside-down or mirrored); linked annotations are automatically re-aligned.
Histogram view of the temperature distribution for the current image.
Export the current view as a PNG.
Adjustable area overlay color (black/white) to keep annotations visible against any color palette.

---

## Available Color Palettes

- Turbo
- Inferno
- Magma
- Plasma
- Viridis
- Jet
- Hot
- Coolwarm
- Gray
- Gray Reversed
---

## Usage Example

1. Click **Select Folder**;
2. Choose a folder containing thermographic images in CSV format;
3. Navigate through the images using the buttons:

⬅ Previous

➡ Next

4. Adjust the temperature scale, if necessary;
5. Choose the desired color palette;
6. Generate histograms or export the images.


---

## Dowload:

```
ThermalCSVViewer-v1.0.exe
```

No installation is required.

---


## Applications

This software can be used in:

- Precision Livestock Farming
- Thermography Research
- Veterinary Science
- Animal Science
- Biomedical Thermography
- Industrial Inspection
- Academic Research
- Computer Vision Studies
---

## Author

**Gabriel Pagin de Carvalho Nunes Oliveira**

Universidade de São Paulo (USP)

2026


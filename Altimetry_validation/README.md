# Altimetry Validation Workflow (CAMEO-WAGST)

## Project Overview

The second line of work within the CAMEO-WAGST project focuses on deriving water levels from satellite altimetry at RPR stations in order to validate Sentinel-3 and Sentinel-6 measurements.

This repository provides a reproducible workflow for extracting water surface heights from Sentinel-3A, Sentinel-3B and Sentinel-6, and comparing them against in-situ measurements to assess how well the satellites perform over rivers and coastal areas in Cameroon.

## Motivation
This workflow is developed to support robust hydrological validation using modern satellite altimetry techniques.
It builds upon advanced preprocessing methods (FFSAR) and aims to provide:
- A reproducible validation framework
- A simplified and transparent workflow
- A user-friendly structure for new users
## Technology Stack and environment
The project is implemented in Python and relies on the following main libraries:
- numpy, pandas
- xarray (NetCDF processing)
- geopandas, shapely (geospatial processing)
- pyproj
- netcdf4
- matplotlib (visualization)
  
A complete list of dependencies is available [here](https://github.com/MakanAKaregar/CAMEO_WGAST/blob/7f3d807ee1ceb69b2dbdc17769537746defdaf81/Altimetry_validation/requirements.txt)

## Workflow Description

The workflow is demonstrated using a representative RPR station or corresponding in-situ hydrometric data, serving as a reference implementation of the full processing chain.

It includes:
- Read Sentinel-3&6 altimetry data: The data can be found [here](https://github.com/MakanAKaregar/CAMEO_WGAST/tree/f1545be60020810de55915a8e9969401c525e66e/Altimetry_validation/data/raw)
- Select measurements around target stations
- Spatial filtering over river and coastal systems
- Extraction of SSH time series from satellite altimetry
- Geophysical corrections and slope adjustments(for river applications)
- Robust statistical aggregation (median + MAD)
- Cross-validation with ground-based observations  
## Getting Started
Follow these steps to run the altimetry validation workflow.
### 1. Installation and set up
Clone the repository to your local machine and set up a virtual environment for python.
### 2. Configuration
Modify the necessary parameters and settings in the [config](config/config.yaml) file to tailor the project to your requirements.
### 3. Prepare input data
Place all required datasets inside [data](data/raw/) directory. The required datasets are described in the *Data Sources* section. Detailed descriptions and access links for each dataset are provided inside the data/raw/ [subfolders](data/raw/).
### 4. Run the Workflow
Execute the main processing script by running the [main](main.py) file. 
### 5. Outputs
All results are automatically generated and saved after running the workflow.
- **Time series outputs (CSV format):**  
  Stored in [outputs](outputs/csv/)
- **Figures and validation plots:**  
  Stored in [outputs](outputs/figures/)

## Data Sources

This validation workflow relies on satellite altimetry products generated using the Fully-Focused SAR (FFSAR) processing chain. The FFSAR preprocessing (developed in the *Altimetry_FFSAR* module) includes:
- Omega-Kappa SAR focusing  
- Waveform retracking using SAMOSA+  
- Signal enhancement for inland and coastal waters  

The preprocessing workflow is available here: [Altimetry_FFSAR](https://github.com/chenjm-1996/JMART_Processer)

This repository uses the resulting Level-2 FFSAR products as input for validation and analysis.

The satellite products are rigorously validated against independent ground-based observations:

- ### *GNSS-IR measurements from RPR stations*
The processed GNSS-IR data, following the GNSS-IR processing workflow described in the *RPR_processing* module, are used in this study. The full processing chain is available here: [RPR_processing](https://github.com/MakanAKaregar/CAMEO_WGAST/tree/4d6a2514814fc5e725057033ca62d3d0c32899bf/RPR_processing). Additional information on the GNSS-IR installations can be found here: [Field campaign in Cameroon](https://github.com/MakanAKaregar/ESA_CAMEO_WGAST/blob/45174bde2637327c8ddf0973f80a22e07124fe13/Field%20campaign%20in%20Cameroon/README.md) and GNSS-IR data can be accessed and downloaded from: [www.GNSS4SurfaceWater.com](http://www.GNSS4SurfaceWater.com). 

- ### *In-situ hydrometric gauge data* 
The in-situ hydrometric gauge data are obtained from AES-SONEL (Energy Corporation of Cameroon) at the CAM1 station (Song Mbenguè). Water levels are recorded through manual staff gauge readings (limnimetric scales) performed four times per day at 07:00, 12:00, 17:00, and 22:00. This manual observation procedure may introduce measurement uncertainties due to operator-dependent reading accuracy.

<p align="center">
  <img src="../assets/Staff Gauge.jpeg" width="1200"/>
  <br>
</p>

- ### *water level time series* from existing virtual gauges in the DAHITI database (DGFI-TUM):
These data are accessed and downloaded through the official portal: https://dahiti.dgfi.tum.de/en/map/.

Further the ground-based observations,other ancillary data are used:
- ### *SWORD dataset*
The SWORD database is used for the river slope correction and publicly available here: https://www.swordexplorer.com/. The slope correction applied in this study follows the methodology described in: https://doi.org/10.1016/j.jhydrol.2024.132553.
- ### *River mask* 
The river mask, provided by the National Institute of Cartography (Cameroon), is used for spatial filtering. It allows the isolation of valid river pixels and the removal of non-water or out-of-basin observations within the Sanaga basin, ensuring that only measurements located within the hydrological domain of interest are retained.

## Scientific Impact

This approach supports the development of robust multi-source water level monitoring systems by integrating:

- Satellite altimetry (Sentinel missions)  
- GNSS-IR observations  
- Conventional hydrometric gauges
- water level time series from the DAHITI database

This integration improves the reliability, spatial coverage, and consistency of hydrological observations.

## Examples of altimetry validation result

The figures below show the examples of the comparison between Sentinel-3 satellite-derived water surface heights (SSH) and in-situ river gauge and DAHITI measurements at the Song Mbenguè station (CAM1).
<p align="center"> <img src="../assets/S3B_599_hydro_CAM1.png" width="1200"/> <br> </p> <p align="center"> <img src="../assets/S3B_599_Dahiti_CAM1.png" width="1200"/> <br> </p> 

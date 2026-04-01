<p align="center">
  <img src="/assets/EOAFRICA-logo-.png" width="200">
</p>

# CAMEO-WAGST

**Cameroon Advanced Measurements for Enhanced Observations of Water Levels using Affordable GNSS-IR and Sentinel-3 & Sentinel-6 Technology**

🔗 Project page (ESA EO AFRICA R&D Facility):  
https://www.eoafrica-rd.org/research/research-projects-2024-2026/#proposal_8

Poject PIs: [Makan Karegar (University of Bonn)](https://www.igg.uni-bonn.de/apmg/de/team/staff/karegar), Loudi Yap (NIC)

---

## Overview

This repository hosts the end-to-end processing workflow developed within the CAMEO-WAGST project funded by ESA (2024-2026).  
The goal of the project is to establish Africa’s first GNSS-IR water level monitoring network and to use it for the validation of Sentinel-3A/B and Sentinel-6 satellite altimetry over rivers, estuaries and coastal zones in Cameroon.

The workflow integrates:

- Low-cost GNSS-IR water level monitoring using the [Raspberry Pi Reflector (RPR)](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2021WR031713) network
- Satellite altimetry processing for Sentinel-3 and Sentinel-6 (including FFSAR focusing and retracking)
- Validation and performance assessment of satellite water levels against GNSS-IR (RPR) observations and available in-situ river gauges

The repository is designed to support reproducible research, open-source development and scalable deployment in data-sparse regions under under the GNU General Public License v3.0 - see the LICENSE file for details.

---

## Key objectives of the CAMEO-WAGST project

- Deploy and operate low-cost GNSS-IR sensors for continuous and near real-time water/sea level monitoring
- Quantify the performance and limitations of Sentinel-3 and Sentinel-6 in tropical riverine and coastal environments of Cameroon
- Provide independent in-situ reference data for satellite altimetry validation
- Support flood monitoring and early-warning applications in Cameroon and beyond
- Enable scalable adoption across Africa and other developing regions**

---

## Repository scope

This repository covers the full processing chain:

1. GNSS-IR data acquisition and processing using RPR and [gnssrefl python package](https://gnssrefl.readthedocs.io/en/latest/) 
2. Sentinel-3A/B and Sentinel-6 altimetry processing
3. Spatio-temporal collocation and validation
4. Statistical analysis and visualization for scientific publications

Each component can be used independently or as part of a complete pipeline.

---

## Citation

If you use this repository or derived products, please cite:

> Establishing Africa’s first GNSS-IR network for coastal and river water level monitoring and satellite altimetry validation (WRR)

---

## License

This project follows an open-source philosophy and licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

---

## Contact

**Project Leads**
- University of Bonn (Germany): Makan Karegar (karegar@uni-bonn.de), Jiaming Chen (jchen1@uni-bonn.de)  
- National Institute of Cartography (Cameroon): Loudi Yap (loudiyap@yahoo.fr) 

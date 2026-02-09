In CAMEO-WAGST prohect, eigh RPR were installed in 2015. The workflow bwlow, is a use case for one of RPRs insatlled in.

# RPR Processing

This directory contains GNSS-IR processing workflows and post-processing
scripts used in the CAMEO-WAGST project.

It focuses on:
- GNSS-IR reflector height estimation
- Water level time series generation
- Quality control and filtering
- Formatting outputs for satellite validation

# Wouri estuary, Camroon

The data collected here is from a [Raspberry Pi Reflector](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2021WR031713). Detailed instructions for RPR setup are provided [here.](https://github.com/MakanAKaregar/RPR/tree/v2.0.0)

This RPR is operating in the Wouri estuary.
<p align=center>
<img src="../assets/cam4_sitePhoto.jpeg" width="400" >
</p>

## metadata

**Station Name:**  cam4

**Location:** Wouri estuary, Cameroon

**Archive:**  [zenodo]()

**Ellipsoidal Coordinates:**

- Latitude: 4.03296304

- Longitude: 9.66628988 

- Height: 41.723 m

[Google Map Link](https://maps.app.goo.gl/Hg3inK8Rb4ZkBJBS6)


### Data Summary

Station cam4 is located in Wouri estuary, Cameroon. It is operated by the University of Bonn, Institute of Geodesy and Geoinformation, [APMG](https://www.apmg.uni-bonn.de/) and [the National Cartography Institute (INC)](https://minresi.gov.cm/en/national-institute-of-cartography/), Camroon. 

The RPR antenna is mounted about 5 m abover the water surface. SNR data on the L1 frequency every 1 second are collected for GPS, Glonass and Galileo satellites.

### 1. Pick up RPR data
RPR data for period 01.06.2025 - ??.??.2026 are publically available from a [zenodo archive](). The data record is updated daily under [the University of Bonn's cloud]().

Download all data (~ 1.7 GB, or 3.3 GB for the extended record):

<code>wget https://zenodo.org/record/6828597/files/MakanAKaregar/RPRatWesel-NMEA.zip?download=1 </code>

or download only a few days data from here:

https://github.com/MakanAKaregar/RPRatWesel

Create nmea and station directory:

<code>mkdir -p $REFL_CODE/nmea/cam4</code>

and then store RPR NMEA files in <code>$REFL_CODE/nmea/cam4/yyyy/</code> where <code>yyyy</code> is the year number.

[$REFL_CODE](https://github.com/kristinemlarson/gnssrefl/blob/master/docs/pages/README_install.md) is an environmental variable to be used by gnssrefl.

### 2. Pick up an azimuth and elevation angle mask

Use either gnssrefl's [<code>refl_zone</code>](https://gnssrefl.readthedocs.io/en/latest/api/gnssrefl.refl_zones_cl.html) command:

<code>refl_zones_all.py cam4 -lat 4.03296304 -lon 9.66628988 -height 41.723 -RH 5 -system all -fr 1 -azlist 180 360 -el_list 2 10</code>

or try the [reflection zone webapp](https://gnss-reflections.org/rzones) with input parameters as:

- Lat. 4.03296304
- Lon. 9.66628988
- EllipseHt. 41.723
- Set Reflector Ht. Value 5
- Elevation Angles 2,10
- Azimuth Angles Start 180 End 360

Here is a KML map generated from [<code>refl_zone</code>](https://gnssrefl.readthedocs.io/en/latest/api/gnssrefl.refl_zones_cl.html) command:

<img src="../assets/cam4_reflection_zone.png" width="600">

### 3. Translate NMEA format to SNR-ready format

Now we should translate NMEA data to gnssrefl internal format ([SNR-ready files](https://gnssrefl.readthedocs.io/en/latest/pages/file_structure.html#the-snr-data-format)) using gnssrefl's [<code>nmea2snr</code>](https://gnssrefl.readthedocs.io/en/latest/api/gnssrefl.nmea2snr_cl.html) command. Here is an example for a single-day translation (doy 1 of 2026).

<code>nmea2snr cam4 2026 1 -lat 4.03296304 -lon 9.66628988 -height 41.723 -gzip True -snr 88 </code>

to translate all data (from doy * of 2025 to doy * of 2026):

<code>nmea2snr cam4 2025 * -year:end 2026 -doy_end 366 -lat 4.03296304 -lon 9.66628988 -height 41.723 -gzip True -snr 88</code>

The SNR files are stored in <code>$REFL_CODE/yyyy/snr/WESL/</code>

### 3. Test quality control parameters

With gnssrefl's[<code>quickLook</code>](https://gnssrefl.readthedocs.io/en/latest/api/gnssrefl.quickLook_cl.html) you can visually examin various azimuth mask settings and quality control parameters. 

<code>quickLook cam4 2026 1 -h1 1 -h2 8</code>

[quickLook](https://gnssrefl.readthedocs.io/en/latest/api/gnssrefl.quickLook_cl.html) makes two plots:

1- Periodogram against reflector height for each 90 degree quadrant:

<img src="../_static/WESLquickLook2.png" width="800">

Since the RPR antenna is installed sideways facing the river (pointing toward west), it doesn't record any reflection from the northeast and southeast directions (right upper and lower panels). There is a bridge to the south of the antenna which interferes with the reflected signals so reflection data recorded from the southwest (left lower panel) direction are noisy and not reliable. Left upper panel shows coherent peaks in periodogram of SNR data recorded from the northwest direction. The peaks correspond to a reflector height of around 11 meters. That means the water is ~ 11 meters below the RPR antenna. However, there are several satellite tracks with double peaks that might be related to the reflections from objects very close to the antenna. These double peaks can be removed after imposing a better elevation or azimuth mask.

2- Reflector height, peak2noise value and peak amplitude against azimuth:

<img src="../_static/WESLquickLook1.png" width="800">

These plots provide more details for quality control. Acceptable reflector heights are plotted in the top plot in blue. Gray points are the reflector heights do not pass quality control. Their corresponding peak to noise ratio plotted in the middle plot is smaller than a default value of 2.7. Reflector height retrievals for satellite tracks sweeping from the azimuth ~250 to ~330 degrees are acceptable. We often don't set value smaller than 2.7 for the peak to noise ratio.

### 4. Define analysis inputs

Based on your finding from [<code>quickLook</code>](https://gnssrefl.readthedocs.io/en/latest/api/gnssrefl.quickLook_cl.html) and the quality control parameters you can now set most of input parameters using [gnssir_input](https://gnssrefl.readthedocs.io/en/latest/api/gnssrefl.gnssir_input.html) command.

Key parameters to set:

The reflector height lower limit <code>-h1</code> and the upper limit <code>-h2</code>. 

Elevation <code>-e1</code> and <code>-e2</code> and azimuth <code>-azlist</code> mask. In our case we set <code>5&le; elevation angle &le;20</code> and <code>250&le; azimuth &le;330</code>

List of GNSS constellations and frequencies <code>-frlist</code>. We set to 1 as we have only GPS L1 data.

<code>gnssir_input WESL -lat 51.646144 -lon 6.606817 -height 73.057 -h1 6 -h2 16 -e1 5 -e2 20 -frlist 1 -azlist 250 330</code>

### 5. Analyze data

Once an appropriate input parameters were set, reflector heights can be estimated using the [gnssir](https://gnssrefl.readthedocs.io/en/latest/api/gnssrefl.gnssir_cl.html#module-gnssrefl.gnssir_cl) command:

Here, we process a single day, doy 233 of 2021, setting plt option:  

<code>gnssir cam4 2026 1 -plt T</code>

<img src="../_static/WESL_gnssir_plot.png" width="800" >

The daily analysis output files are stored in <code>$REFL_CODE/yyyy/results/cam4</code>
  
### 6. Processing and post-processing time series of reflector heights

We now process 3 months of data from doy ** to doy ** of 2025.

I maintain the daily archive of this RPR data at [the University of Bonn’s cloud](https://uni-bonn.sciebo.de/s/7CH1ctSPfQeLQbK):

Download 2023 data and then store the NMEA files in <code>$REFL_CODE/nmea/WESL/yyyy/</code>

Translate NMEA format to SNR format:

<code>nmea2snr WESL 2023 93 -doy_end 117 -lat 51.646144 -lon 6.606817 -height 73.057</code> 

and process the data:

<code>gnssir WESL 2023 93 -doy_end 171 </code>

with [daily_avg](https://gnssrefl.readthedocs.io/en/latest/pages/README_dailyavg.html) command, we can derive daily 
average of reflector height with plots, remove outliers and print daily average reflector height to 
a text file in <code>$REFL_CODE/Files/wesl/wesl_dailyRH.txt</code>. Note that this command 
should be used with caution when applying to fast-changing tidal river and sea level. At this site tides are absent.

Positional parameters to set in [daily_avg](https://gnssrefl.readthedocs.io/en/latest/pages/README_dailyavg.html):

<code>medfilter</code> is a tolerance (in meter) in which all residuals larger than this tolerance are removed.

<code>ReqTracks</code> is the minimum required number of satellite tracks for averaging.

These post-processing parameters are site specific. For example, historical river gauge data (2010–2021) for 
the Rhine near Wesel indicates the 95th percentile of day-to-day water-level variation amounts 
to 30 cm, thus we identify a reflector height as outlier when it differs from the median value of all 
reflector height (for each day) by more than 30 cm. The value for <code>ReqTracks</code> depends on azimuth mask.

<code>daily_avg wesl 0.3 10</code>

<img src="../_static/WESL_SubDaily.png" width="500">

<img src="../_static/WESL_DailyAvg.png" width="500">

All and daily mean of reflector heights are printed to <code>wesl_allRH.txt</code> and 
<code>wesl_dailyRH.txt</code> text files in <code>$REFL_CODE/Files/wesl/</code>, respectively.


Prepared by [Makan Karegar](https://github.com/MakanAKaregar). Last updated June 30, 2023.

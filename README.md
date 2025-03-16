# What's New?
HOBOlink has upgraded to a redesigned platform, now LI-COR Cloud. The current repository, HOBOlink API version 2.0, has been updated to be fully compatiable with the redesigned platform.

Credentials are no longer required to retrieve data from the API platform. API tokens can be generated directly through the HOBOlink UI. 

"Get Data Endpoint" URL is now: https://api.hobolink.licor.cloud/v1/data and will only work in timeframe mode. Each request will need to include a logger serial number, start date time and an end date time (in UTC).

The following are all of the response changes to data request to the "Get Data Endpoint":
- “observation_list” has been renamed “data”
- Sensor data is now only reported in the units configured for the device. As a result, field name variations have been combined into the following single fields: 
	- “value” holds numeric reading value for unit (si_value, us_value, scaled_value fields are no longer available)
	- “unit” field holds string name for unit (si_unit, us_unit, scaled_unit fields are no longer available)
	- “sensor_measurement_type” continues to hold the string name for sensor measurement, which is the base sensor measurement name for sensors not scaled, and the scaled measurement name for scaled sensors.
- New, user readable “data_type” string field has been added to describe the data type of the sensor reading. “data_type_id” is provided for legacy compatibility. 
	- Current / Normal data: “CURRENT” (legacy type: “1”)
	- Minimum statistics data: “MINIMUM” (legacy type: “2”)
	- Maximum statistics data: “MAXIMUM” (legacy type: “3”)
	- Average statistics data: “AVERAGE” (legacy type: “4”)
	- Standard deviation statistics data: “STANDARD_DEVIATION” (legacy type: “5”)

# HOBOlink API 2.0
HOBOlink is web-based software for configuring and monitoring RX3000 Remote Monitoring Stations and RX2100 MicroRX & MicroRX Water Level Stations. HOBOlink.py is a Python script that will pull data directly from [HOBOlink](https://hobolink.com/). The python script follows the [HOBOlink® Web Services V3 Developer’s Guide](https://www.onsetcomp.com/sites/default/files/resources-documents/25113-B%20HOBOlink%20Web%20Services%20V3%20Developer%27s%20Guide.pdf) and the [HOBOlink Swagger API doc] (https://api.hobolink.licor.cloud/v1/docs/#/). The guide walks you through the steps to use the REST API and OAuth to grant access to users to view and retrieve data from loggers remotely. The following will breakdown the steps needed to use the python script and retrieve data from the API.

## Access to a HOBOlink account and a Remote Monitoring Station
It is neccessary to have access to a HOBOlink account and a Remote Monitoring station that is operational.
To create an account go to [HOBOlink](https://www.licor.cloud/), and register your device (the serial number and device key is required to register a device). Keep a record of the device is serial number as it will be used in the python script.

## Generate API Token
Login to [HOBOlink](https://www.licor.cloud/) and generate an API token. Once you have logged in, head to *Data* > *API* > *Add Token*

Record this token somewhere safe.

# Setup and Run Your Python Environment in Docker

This repository contains a setup script to create a Docker environment for running Python scripts, including `HOBOlink.py`.

## Prerequisites

- Install [Docker](https://docs.docker.com/get-docker/) on your system.

## Setup Instructions

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd <your-repo-name>
   ```

2. **Run the setup script**

   ```bash
   ./setup.sh
   ```

   This script will:

   - Make all files in the repository executable.
   - Create a `Dockerfile` (if it doesn’t already exist).
   - Build a Docker image named `my_python_env`.

## Running the Container

### Option 1: Enter the container and run the script manually

```bash
docker run -it --rm my_python_env
```

Once inside the container, run:

```bash
python HOBOlink.py
```

### Option 2: Run the script automatically when the container starts

1. Modify the `Dockerfile` to set `HOBOlink.py` as the startup command:
   ```dockerfile
   CMD ["python", "HOBOlink.py"]
   ```
2. Rebuild the Docker image:
   ```bash
   docker build -t my_python_env .
   ```
3. Run the container:
   ```bash
   docker run --rm my_python_env
   ```

### Option 3: Run the script directly using `docker run`

```bash
docker run --rm my_python_env python HOBOlink.py
```

## Additional Notes

- The container will install the required Python libraries automatically.
- If you update `HOBOlink.py` or any dependencies, rebuild the image:
  ```bash
  docker build -t my_python_env .
  ```

## Create .env file to store environement variables
Create a new `.env` file in the root directory where `HOBOlink.py` is located.
Add the following lines into the `.env` file and input the API token that was generated within the HOBOlink UI.

	# API Token - generated within the HOBOlink UI
	TOKEN='XXXXXXXXXXXXXXX'

The variables stored in the `.env` can now be called on with the `dotenv` and `os` python module within the `HOBOlink.py` script. `.gitignore` has been set up to avoid any potential risk of accidentally pushing it to git repo. All of your sensitive information is now safely stored.

## Metadata CSV
Create a `.csv` file to keep things organized and simplify the process of retrieving data from the API. 

Note: the repository was designed to retrieve data from standalone precipitation gauges and stream gauges so `HOBOlink.py` will have file paths hard-coded

For example, to retrieve data from stream sites, we will create a `Streams_Metadata.csv` with the following header:

	Header: site_ID,CDEC_ID,logger_SN,logging_int,start_time,latitude,longitude,site_elevation_m

The csv will store the site ID, logger serial number and start time. The CDEC ID is optional and can be left blank. It is recommanded to store the csv within the HOBOlink API directory, or alternatively the path can be specified within the `HOBOlink.py` script.

# HOBOlink.py and HOBOlink_parse.py
`HOBOlink.py` will be the main script, and uses a number of functions from `HOBOlink_parse.py`
The following will breakdown each of the scripts further:


# CSV File Formats
The following are the csv files that will be produced for either standalone precipitation gauges or stream gauges. Daily files will also be produced in stored in their respective directories. Daily files will have identical formats to their respective long running files.

**Stream Gauge CSV Formats**

*Site_ID_MasterTable_Raw.csv:*

    Header: "timestamp_UTC","water_temperature_Celsius","water_level_m","water_pressure_kPa","water_pressure_psi","diff_pressure_kPa","diff_pressure_psi","water_temperature_Fahrenheit","water_level_ft","barometric_pressure_kPa","barometric_pressure_psi","level_corrected_ft","level_corrected_m","level_corrected_cm","discharge_cfs","discharge_cms","qc_status"
 
  - Column  1: Timestamp recorded in UTC format
	- Column  2: Water Pressure in kilopascals
	- Column  3: Water Pressure in pounds per square inch
	- Column  4: Diff Pressure in kilopascals
	- Column  5: Diff Pressure in pounds per square inch
	- Column  6: Water Temperature in celsius
	- Column  7: Water Temperature in fahrenheit
	- Column  8: Water Level in meters
	- Column  9: Water Level in feet
	- Column 10: Barometric Pressure in kilopascals
	- Column 11: Barometric Pressure in pounds per square inch

*Site_ID_MasterTable_Processed.csv:*

    Header: "timestamp_UTC","water_temperature_Celsius","water_level_m","water_pressure_kPa","water_pressure_psi","diff_pressure_kPa","diff_pressure_psi","water_temperature_Fahrenheit","water_level_ft","barometric_pressure_kPa","barometric_pressure_psi","level_corrected_ft","level_corrected_m","level_corrected_cm","discharge_cfs","discharge_cms","qc_status"
 
  - Column  1: Timestamp recorded in UTC format
	- Column  2: Water Pressure in kilopascals
	- Column  3: Water Pressure in pounds per square inch
	- Column  4: Diff Pressure in kilopascals
	- Column  5: Diff Pressure in pounds per square inch
	- Column  6: Water Temperature in celsius
	- Column  7: Water Temperature in fahrenheit
	- Column  8: Water Level in meters
	- Column  9: Water Level in feet
	- Column 10: Barometric Pressure in kilopascals
	- Column 11: Barometric Pressure in pounds per square inch
	- Column 12: adjusted water leevl in feet
	- Column 13: adjusted water level in meters
	- Column 14: adjusted water level in centimeters
	- Column 15: Discharge in cubic feet per second 
	- Column 16: Discharge in cubic meters per second
	- Column 17: Quality Contol Status

	**Standalone Precipitation Gauge Formats:**
	Data logger by default will record tips and will require further configuration on the UI to record in correct units.

	*Site_ID_MasterTable_Raw.csv:

    Header: "timestamp_UTC","precipitation","accumulated_precipitation"

	- Column 1: Timestamp recorded in UTC format
	- Column 2: Precipitation in mm
	- Column 3: Accumulated Precipitation in mm - will reset at the start of the new water year October 1st 00:00:00Z

# Log File:
`HOBOlink.py` will create a log files and record important events. Each site and its respective logger will have a log file generated.

# Run script and helpful notes
The script is setup to run and create csv files for all the loggers listed in the `.env` file. Once all info has been inputted the script is ready to run. The script will pull data from a default start time (on the initial run) and will pull any new available data for that logger since that default time. After the first time the script is ran for a site, it will proceed to retrieve data from the last recorded timestamp to the current time.

There are limitattions to pulling data for large time periods since the API is only capable of proving up to 100,000 data points at any given time. This will require the script to be ran multiple times until all available data is recorded into its csv file. Pulling large amounts of data points at any given time is not advised with the API, and can result in missing values, or error responses. 
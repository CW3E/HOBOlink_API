#!/usr/bin/python
# CW3E Field Team
# 2024/04
# Adolfo Lopez Miranda

# import modules
import sys, requests, json, urllib3, pandas as pd, os, csv, numpy as np, pytz
from datetime import datetime, timedelta, timezone
from collections import namedtuple
from pathlib import Path
from io import StringIO

# disable warnings for Insecure Request Warning
urllib3.disable_warnings() # warnings occur when obtaining a token

# Functions to be used when pulling data from HOBOlink

# function to obtain a new OAuth 2.0 token from the authentication server
def get_new_token(auth_server_url, client_id, client_secret):
    token_req_payload = {'grant_type': 'client_credentials'}

    token_response = requests.post(auth_server_url,
                                   data=token_req_payload, 
                                   verify=False, 
                                   allow_redirects=False,
                                   auth=(client_id, client_secret)
                                   )
			 
    if token_response.status_code !=200:
        print("Failed to obtain token from the OAuth 2.0 server")
        sys.exit(1)
        
    tokens = json.loads(token_response.text)
    return tokens['access_token']

def get_num_lines(fname):
    with open(fname,"r") as f:
        for i, _ in enumerate(f):
            pass
    return i + 1

import pandas as pd
from datetime import datetime, timedelta

def csv_timestamp(filename, logging_interval_minutes):
    """
    Reads the last non-empty timestamp from a specified column in a CSV file, adjusts the time by a given interval,
    and returns the adjusted time in both datetime and formatted string suitable for URL parameters.

    Parameters:
    - filename (str): Path to the CSV file.
    - logging_interval_minutes (int): Number of minutes to add to the last recorded timestamp.

    Returns:
    - A tuple containing the formatted timestamp string for URL use and the datetime object representing the adjusted time.
    """
    # Configure Pandas to read only the first column in chunks
    chunk_iterator = pd.read_csv(filename, header=None, skip_blank_lines=True, iterator=True, chunksize=1000, usecols=[0])
    
    date_str = None
    for chunk in chunk_iterator:
        last_row = chunk.dropna().tail(1)  # Use tail to get the last non-empty row
        if not last_row.empty:
            date_str = last_row.iloc[0, 0]  # Assuming timestamp is in the first column

    if date_str is None:
        raise ValueError("No valid timestamps found in the CSV.")

    # Convert string to datetime object and add logging interval
    dt_start = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S%z') + timedelta(minutes=logging_interval_minutes)
    
    # Prepare timestamp for URL encoding
    start_timestamp = dt_start.strftime("&start_date_time=%Y-%m-%d+%H:%M:%S").replace(':', '%3A')
    
    return start_timestamp, dt_start


def convert_time(time_string, target_format=None):
    """
    Convert a given UTC time string to a format suitable for use in scripts or URLs.
    
    Parameters:
    - time_string (str): Time in UTC to be converted, formatted as 'YYYY-MM-DD HH:MM:SSZ'.
    - target_format (str, optional): Target format for the conversion. Use 'start' for start time format,
                                      'end' for end time format, or leave as None for no additional formatting.
    
    Returns:
    - A tuple of (datetime object, formatted time string). If target_format is None, the second element is the original time string.
    """
    utc_format = '%Y-%m-%d %H:%M:%S%z'  # Original date and time format with UTC timezone
    dt_time = datetime.strptime(time_string, utc_format)
    
    # Base format for URL encoding
    base_format = '&{}_date_time=%Y-%m-%d+%H:%M:%S'.format(target_format.lower()) if target_format else None
    
    if base_format:
        # Encode the datetime object into the specified URL format
        timestamp = dt_time.strftime(base_format).replace(':', '%3A')
    else:
        # No conversion required, use original time string
        timestamp = time_string
    
    return dt_time, timestamp

def start_time_offset(time_string, logging_int, target_format=None):
    """
    function to convert start_time stored in metadata csv to be used in scripts
    time must be provided in UTC, example: 2024-03-01 00:00:00Z
    will also apply offset using logging interval to get the next available value
    """
    utc_format = '%Y-%m-%d %H:%M:%S%z'  # Original date and time format with UTC timezone
    dt_time = datetime.strptime(time_string, utc_format) + timedelta(minutes=logging_int)
    
    # Base format for URL encoding
    base_format = '&{}_date_time=%Y-%m-%d+%H:%M:%S'.format(target_format.lower()) if target_format else None
    
    if base_format:
        # Encode the datetime object into the specified URL format
        timestamp = dt_time.strftime(base_format).replace(':', '%3A')
    else:
        # No conversion required, use original time string
        timestamp = time_string
    
    return dt_time, timestamp
     
# function to parse the data from the HOBOlink API
def parse_stream(hobolink_data, site_name, cdec=None, base_path=None, shef_toggle=False):
    
    """
    Parses JSON data that was pulled and found with the dictionary key "observation_list"
    JSON data is passed into the DataFrame into daily CSV files within a specified or default directory structure.
    
    Parameters:
    - hobolink_data: data returned by the HOBOLink API call
    - site_name: str, the name of the site, used in the directory structure and file naming. Typically a 3 character ID
    - base_path: str or None, the base path where files will be saved. If None, uses a default directory structure.
    """   

    observation_list = hobolink_data["data"]
    
    # Define units - will depend on what sensors are connected
    si_units = {"kPa", "°C", "meters"}
    us_units = {"psi", "°F", "feet"}

    # Process observations into a list for DataFrame
    rows = []
    tracked_units = set()  # To track encountered units (excluding battery voltage)

    for obs in observation_list:
        unit = obs["unit"]
        sensor_type = obs["sensor_measurement_type"]
        
        if sensor_type.lower() != "battery":  # Ignore battery voltage
            tracked_units.add(unit)

        if unit in si_units:
            key = f"{sensor_type} si"
        elif unit in us_units:
            key = f"{sensor_type} us"
        else:  # Battery voltage or other unknown units
            key = sensor_type

        rows.append({"timestamp": obs["timestamp"], key: obs["value"]})

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Determine if all non-battery units are SI or US
    if tracked_units.issubset(si_units):
        unit_type = "SI"
    elif tracked_units.issubset(us_units):
        unit_type = "US"
    else:
        unit_type = "Mixed"
    
    # If there's no values, or there were only Battery V measurements, return
    if df.empty:
        print('No new data found.')
        return df.shape[0]
    
    # Handle duplicate timestamps by grouping and aggregating
    df = df.groupby("timestamp", as_index=False).first()
    
    # Remove rows that are just battery data
    df = df[~((df["Battery"].notna()) & (df.drop(columns=["timestamp", "Battery"]).isna().all(axis=1)))]
    
    # remove any rows with nan values
    # uncomment this if we don't want any data from a timestamp when one of the values is missing.
    df = df.dropna()
    
    # reset index
    df = df.reset_index(drop=True)
    
    #convert all measurements to either SI or US units
    if unit_type == "US":
        # convert all US units to SI and add to dataframe
        if 'Water Pressure us' not in df:
            df['Water Pressure us'] = df['Barometric Pressure us'] + df['Diff Pressure us']
        df['Water Pressure si'] = df['Water Pressure us'] * 6.89476
        df['Diff Pressure si'] = df['Diff Pressure us'] * 6.89476
        df['Barometric Pressure si'] = df['Barometric Pressure us'] * 6.89476
        df['Water Temperature si'] = (df['Water Temperature us'] - 32) * (5/9)
        df['Water Level si'] = df['Water Level us'] * 0.3048
    elif unit_type == "SI":
        # convert all SI units to US and add to dataframe
        if 'Water Pressure si' not in df:
            df['Water Pressure si'] = df['Barometric Pressure si'] + df['Diff Pressure si']
        df['Water Pressure us'] = df['Water Pressure si'] / 6.89476
        df['Diff Pressure us'] = df['Diff Pressure si'] / 6.89476
        df['Barometric Pressure us'] = df['Barometric Pressure si'] / 6.89476
        df['Water Temperature us'] = df['Water Temperature si'] * (9/5) + 32
        df['Water Level us'] = df['Water Level si'] * 3.28084
    else:
        print("US and SI units are mixed")

    # Apply rounding and formatting to all numeric values
    df = df.applymap(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)

    # Rename columns to match MasterTable column names
    new_column_names = {'timestamp': 'timestamp_UTC',
                        'Water Temperature si': 'water_temperature_Celsius',
                        'Water Level si': 'water_level_m',
                        'Water Pressure si': 'water_pressure_kPa',
                        'Water Pressure us': 'water_pressure_psi',
                        'Diff Pressure si': 'diff_pressure_kPa',
                        'Diff Pressure us': 'diff_pressure_psi',
                        'Water Temperature us': 'water_temperature_Fahrenheit',
                        'Water Level us': 'water_level_ft',
                        'Barometric Pressure si': 'barometric_pressure_kPa',
                        'Barometric Pressure us': 'barometric_pressure_psi',
                        'Battery': 'battery_V'
                        }
    
    df = df.rename(columns=new_column_names)
    
    # If one of the columns doesn't exist, create a column with the right name and fill with nans
    for col in new_column_names.values():
        if col not in df.columns:
            df[col] = np.nan

# check for 15 minute data and then resample

    # Define the path for the long-running file
    # if base_path=None the rating curve csv file must be stored in the same directory as where the script is running
    dir_path = Path(base_path if base_path else './')
    #dir_path.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    rating_curve_path = dir_path / f'{site_name}/Rating_Curve/{site_name}.rating_curve_100_points.csv'
    
    # check if there is a rating curve. If not, set discharge to -9999.99
    rating_curve_exists = os.path.exists(rating_curve_path)
    if rating_curve_exists:
        print('Rating curve found.')
        # load the rating curve
        rating_curve = pd.read_csv(rating_curve_path)
        # Apply the rating curve to calculate discharge
        water_flow_cfs = df['water_level_ft'].apply(lambda x: calculate_discharge(x, rating_curve))
        water_flow_cfs = water_flow_cfs.round(6)

        # Convert from cfs to cms with a vectorized operation
        water_flow_cms = np.where(water_flow_cfs == -9999.99,
                                            -9999.99,
                                            water_flow_cfs * 0.0283168).round(6)
    else:
        print('No rating curve. Setting all discharge to -9999.99')
        # Set the discharge to -9999.99
        water_flow_cfs = np.full(len(df['water_level_ft']),-9999.99)
        water_flow_cms = np.full(len(df['water_level_ft']),-9999.99)
    
    # Add discharge columns to the dataframe
    df2 = df.drop(columns=['battery_V'])
    df2['discharge_cfs'] = water_flow_cfs
    df2['discharge_cms'] = water_flow_cms

    # Define new columns - used for QC process
    df2['level_corrected_ft'] = [-9999.99] * len(df2)
    df2['level_corrected_m'] = [-9999.99] * len(df2)
    df2['level_corrected_cm'] = [-9999.99] * len(df2)
    df2['qc_status'] = ["Provisional"] * len(df2)

    # Define the desired order of columns for the processed data
    desired_column_order = [
        'timestamp_UTC',
        'water_temperature_Celsius',
        'water_level_m',
        'water_pressure_kPa',
        'water_pressure_psi',
        'diff_pressure_kPa',
        'diff_pressure_psi',
        'water_temperature_Fahrenheit',
        'water_level_ft',
        'barometric_pressure_kPa',
        'barometric_pressure_psi',
        'level_corrected_ft',
        'level_corrected_m',
        'level_corrected_cm',
        'discharge_cfs',
        'discharge_cms',
        'qc_status'
    ]

    # Define columns for Raw data (subset)
    raw_columns = [
        'timestamp_UTC',
        'water_temperature_Celsius',
        'water_level_m',
        'water_pressure_kPa',
        'water_pressure_psi',
        'diff_pressure_kPa',
        'diff_pressure_psi',
        'water_temperature_Fahrenheit',
        'water_level_ft',
        'barometric_pressure_kPa',
        'barometric_pressure_psi'
    ]

    # Reorder columns for processed data
    df2 = df2[desired_column_order]

    # Resample the data to correct 15-minute intervals
    df2['timestamp_UTC'] = pd.to_datetime(df2['timestamp_UTC'])

    if any(df2['timestamp_UTC'].dt.minute % 15 != 0):
        print("There are timestamps with irregular minutes. Resampling.")
        
        df2.set_index('timestamp_UTC', inplace=True)
        df2.replace(-9999.99, np.nan, inplace=True)
        
        # Define aggregation rules (mean for numeric columns)
        aggregations = {col: 'mean' for col in df2.columns if col != 'qc_status'}
        
        # Resample and round data
        df2_resampled = df2.resample('15T').agg(aggregations).round(2)

        # Fill NaN values with -9999.99 for numeric columns
        for col in df2_resampled.select_dtypes(include=['number']).columns:
            df2_resampled[col] = df2_resampled[col].fillna(-9999.99)

        df2_resampled["qc_status"] = 'Provisional'
        df2_resampled.index = df2_resampled.index.strftime('%Y-%m-%d %H:%M:%SZ')
        
        df2_resampled = df2_resampled.rename_axis('timestamp_UTC').reset_index()
        df2 = df2_resampled
    else:
        print("All timestamps have regular minutes (00, 15, 30, or 45).")
        df2['timestamp_UTC'] = df2['timestamp_UTC'].dt.strftime('%Y-%m-%d %H:%M:%SZ')

        # Fill NaN values with -9999.99
        for col in df2.select_dtypes(include=['number']).columns:
            df2[col] = df2[col].fillna(-9999.99)

    # Set up base master path
    master_path = Path(base_path if base_path else './') / site_name

    # Create subdirectories for Raw and Processed
    raw_path = master_path / "Raw"
    processed_path = master_path / "Processed"
    raw_path.mkdir(parents=True, exist_ok=True)
    processed_path.mkdir(parents=True, exist_ok=True)

    # File names
    master_table_raw = raw_path / f"{site_name}_MasterTable_Raw.csv"
    master_table_processed = processed_path / f"{site_name}_MasterTable_Processed.csv"

    # Write to Raw CSV (only subset of columns)
    df2[raw_columns].to_csv(master_table_raw, mode='a' if master_table_raw.exists() else 'w', 
                            index=False, header=not master_table_raw.exists(), 
                            escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)

    # Set file permissions for Raw (User: RW, Group: R, Others: R) = `0o644`
    os.chmod(master_table_raw, 0o744)

    # Write to Processed CSV (all columns)
    df2.to_csv(master_table_processed, mode='a' if master_table_processed.exists() else 'w', 
            index=False, header=not master_table_processed.exists(), 
            escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)

    # Set file permissions for Processed (User: RW, Group: RWX, Others: R) = `0o744`
    os.chmod(master_table_processed, 0o774)

    # Convert timestamp back for grouping
    df2['timestamp_UTC'] = pd.to_datetime(df2['timestamp_UTC'], format='%Y-%m-%d %H:%M:%S%z')

    # Group data by date and hour
    grouped = df2.groupby([
        df2['timestamp_UTC'].dt.year,
        df2['timestamp_UTC'].dt.month.apply(lambda x: f'{x:02d}'),
        df2['timestamp_UTC'].dt.day.apply(lambda x: f'{x:02d}'),
        df2['timestamp_UTC'].dt.hour.apply(lambda x: f'{x:02d}00')
    ])

    # Raw Daily & Processed Daily
    for (year, month, day, hour), group in grouped:
        
        # **Raw Daily**
        raw_daily_path = raw_path / "Raw_Daily" / str(year) / str(month)
        raw_daily_path.mkdir(parents=True, exist_ok=True)
        raw_daily_file = raw_daily_path / f"{site_name}_{year}{month}{day}.csv"
        
        # Format timestamp for storage
        group['timestamp_UTC'] = group['timestamp_UTC'].dt.strftime('%Y-%m-%d %H:%M:%S') + 'Z'
        
        # Store only selected raw columns
        group[raw_columns].to_csv(raw_daily_file, mode='a' if raw_daily_file.exists() else 'w',
                                index=False, header=not raw_daily_file.exists(),
                                escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)

        # Set file permissions for Raw Daily (User: RWX, Group: R, Others: R) = `0o744`
        os.chmod(raw_daily_file, 0o744)

        # **Processed Daily**
        processed_daily_path = processed_path / "Processed_Daily" / str(year) / str(month)
        processed_daily_path.mkdir(parents=True, exist_ok=True)
        processed_daily_file = processed_daily_path / f"{site_name}_{year}{month}{day}.csv"
        
        # Store entire DataFrame
        group.to_csv(processed_daily_file, mode='a' if processed_daily_file.exists() else 'w',
                    index=False, header=not processed_daily_file.exists(),
                    escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)

    # Set file permissions for Processed Daily (User: RWX, Group: R, Others: R) = `0o744`
    os.chmod(processed_daily_file, 0o774)            
    
    #------------------------------------------------------------------------------
    
    if shef_toggle == True and cdec != None:
        # convert files to shef - must be done outside since the other files are in UTC 
        # Add battery column back in
        df2['battery_V'] = df['battery_V']
        
        # Ensure timestamps include a timezone offset instead of just 'UTC'
        # If not, you'll need to preprocess them to include a proper offset (e.g., replace 'UTC' with '+0000')
        df2['timestamp_UTC'] = pd.to_datetime(df2['timestamp_UTC'], format='%Y-%m-%d %H:%M:%S%z')
        
        # Convert to Pacific Time
        pacific = pytz.timezone('US/Pacific')
        df2['timestamp_UTC'] = df2['timestamp_UTC'].dt.tz_convert(pacific)

        # Group data by date
        grouped = df2.groupby([df2['timestamp_UTC'].dt.year, 
                            df2['timestamp_UTC'].dt.month.apply(lambda x: f'{x:02d}'), 
                            df2['timestamp_UTC'].dt.day.apply(lambda x: f'{x:02d}'),
                            df2['timestamp_UTC'].dt.hour.apply(lambda x: f'{x:02d}')])

        for (year, month, day, hour), group in grouped:
            #SHEF Hourly Output
            shef_path = Path(base_path if base_path else f'./') / site_name / 'SHEF_Output' / str(year) / str(month) / str(day)
            shef_path.mkdir(parents=True, exist_ok=True)
            # Define the filename for SHEF files
            shef_file = f"{cdec}_Streamflow_SHEF_{year}{month}{day}{hour}.txt"

            # Full path for the file to be saved
            shef_file_path = shef_path / shef_file
            
            # Determine the file mode: 'a' to append if the file exists, 'w' to write otherwise
            file_mode = 'a' if shef_file_path.exists() else 'w'

            # Open the file to write SHEF data
            with shef_file_path.open(mode=file_mode) as file:
                for _, row in group.iterrows():
                    # Format the timestamp in SHEF format
                    timestamp_shef = row['timestamp_UTC'].strftime('%Y%m%d%H%M')
                    # Write stage and discharge lines in SHEF format
                    """
                    The .A format is designed for the transmission of one or more hydrometeorological parameters observed at various times for a single station.
                    .A is the format used
                    P indicates Pacific time
                    DH = hour of day and also include minute value e.g. for 21:15 will be written as 2115
                    HGI = river stage (feet)
                    QRI = discharge (cubic feet per second)
                    """
                    # Write a shef line with the stage value
                    data_line = f".A {cdec} {timestamp_shef[:8]} P DH{timestamp_shef[8:]} /HGI {format_shef_value(row['water_level_ft'])}"
                    # If the rating_cuve_exists, include the discharge in the shef code.
                    if rating_curve_exists:
                        data_line = data_line + f"/QRI {format_shef_value(row['discharge_cfs'])}"
                    # Include the water temperature (TWI for Fahrenheit, instantaneous)
                    data_line = data_line + f"/TWI {format_shef_value(row['water_temperature_Fahrenheit'])}"
                    # Include the barometric pressure (PAI in inHg, instantaneous).
                    data_line = data_line + f"/PAI {format_shef_value(row['barometric_pressure_psi']*2.03602)}"
                    # Include the battery data (VBI for battery voltage in Volts, instantaneous)
                    data_line = data_line + f"/VBI {format_shef_value(row['battery_V'])}"
                    

                    # Write to the file
                    file.write(data_line + '\n')
                    os.chmod(shef_file_path, 0o774)
            
        #SHEF output - append all new data to one file
        shef_path = Path(base_path if base_path else f'./') / site_name / 'SHEF_Output'
        shef_path.mkdir(parents=True, exist_ok=True)
        # Define the filename for SHEF files
        shef_file = f"{cdec}_Streamflow_SHEF_latest.txt"

        # Full path for the file to be saved
        shef_file_path = shef_path / shef_file
        
        # Determine the file mode: 'a' to append if the file exists, 'w' to write otherwise
        file_mode = 'a' if shef_file_path.exists() else 'w'
        # check if there is any timestamp at the start of the new hour (00 minute)
        #overwrite = df2['timestamp_UTC'].dt.minute.isin([0]).any()
        #file_mode = 'w' if overwrite else 'a'
            
        # Open the file to write SHEF data
        with shef_file_path.open(mode=file_mode) as file:
            for _, row in df2.iterrows():
                # Format the timestamp in SHEF format
                timestamp_shef = row['timestamp_UTC'].strftime('%Y%m%d%H%M')
                # Write stage and discharge lines in SHEF format
                """
                The .A format is designed for the transmission of one or more hydrometeorological parameters observed at various times for a single station.
                .A is the format used
                P indicates Pacific time
                DH = hour of day and also include minute value e.g. for 21:15 will be written as 2115
                HGI = river stage (feet)
                QRI = discharge (cubic feet per second)
                """
                # Write a shef line with the stage value
                data_line = f".A {cdec} {timestamp_shef[:8]} P DH{timestamp_shef[8:]} /HGI {format_shef_value(row['water_level_ft'])}"
                # If the rating_cuve_exists, include the discharge in the shef code.
                if rating_curve_exists:
                    data_line = data_line + f"/QRI {format_shef_value(row['discharge_cfs'])}"
                # Include the water temperature (TW for Fahrenheit, TU for Celcius)
                data_line = data_line + f"/TWI {format_shef_value(row['water_temperature_Fahrenheit'])}"
                # Include the barometric pressure (PAI in inHg, instantaneous).
                data_line = data_line + f"/PAI {format_shef_value(row['barometric_pressure_psi']*2.03602)}"
                # Include the battery data (VBI for battery voltage in Volts, instantaneous)
                data_line = data_line + f"/VBI {format_shef_value(row['battery_V'])}"

                # Write to the file
                file.write(data_line + '\n')
                os.chmod(shef_file_path, 0o775)

    # Return both the number of records processed and the list of filenames
    return df2.shape[0] #, filename_list

# TODO: this function is no longer up to date
def backfill_stream(hobolink_data,site_name, base_path=None, append_to_single_file=False):
    # pass JSON data into a dateframe
    df = pd.DataFrame.from_dict(hobolink_data["observation_list"])
    # Parse data for stream gage
    # Water Pressure
    water_pressure = df.loc[df['sensor_measurement_type'] == 'Water Pressure']
    # Check if the resulting DataFrame is empty
    if water_pressure.empty:
        # If no water pressure data is found, set default values
        water_pressure_si = np.nan
        water_pressure_us = np.nan
        timestamp = np.nan
    else:
        water_pressure_si = water_pressure['si_value'].round(2).reset_index(drop=True)
        water_pressure_us = water_pressure['us_value'].round(2).reset_index(drop=True)
        # Date timestamps for data - each 'sensor_measurement_type' provides a 'timestamp' but only uses one value per timestamp so we drop duplicates
        timestamp = water_pressure['timestamp'].reset_index(drop=True)
        
    # Difference Pressure
    diff_pressure = df.loc[df['sensor_measurement_type'] == 'Diff Pressure']
    # Check if the resulting DataFrame is empty
    if diff_pressure.empty:
        # If no water pressure data is found, set default values
        diff_pressure_si = np.nan
        diff_pressure_us = np.nan
    else:
        diff_pressure_si = diff_pressure['si_value'].round(2).reset_index(drop=True)
        diff_pressure_us = diff_pressure['us_value'].round(2).reset_index(drop=True)

    # Water Temperature
    water_temp = df.loc[df['sensor_measurement_type'] == 'Water Temperature']
    # Check if the resulting DataFrame is empty
    if water_temp.empty:
        # If no water pressure data is found, set default values
        water_temp_si = np.nan
        water_temp_us = np.nan
    else:
        water_temp_si = water_temp['si_value'].round(2).reset_index(drop=True)
        water_temp_us = water_temp['us_value'].round(2).reset_index(drop=True)
        
    # Water Level
    water_lvl = df.loc[df['sensor_measurement_type'] == 'Water Level']
    # Check if the resulting DataFrame is empty
    if water_lvl.empty:
        # If no water pressure data is found, set default values
        water_lvl_si = np.nan
        water_lvl_us = np.nan
    else:   
        water_lvl_si = water_lvl['si_value'].round(2).reset_index(drop=True)
        water_lvl_us = water_lvl['us_value'].round(2).reset_index(drop=True)
    
    # Barometric Pressure
    bar_pressure = df.loc[df['sensor_measurement_type'] == 'Barometric Pressure']
    # Check if the resulting DataFrame is empty
    if bar_pressure.empty:
        # If no barometric pressure data is found, set default values
        bar_pressure_si = np.nan
        bar_pressure_us = np.nan
    else:
        bar_pressure_si = bar_pressure['si_value'].round(2).reset_index(drop=True)
        bar_pressure_us = bar_pressure['us_value'].round(2).reset_index(drop=True)
        
    # Attempt to filter for Water Flow measurements
    water_flow = df.loc[df['sensor_measurement_type'] == 'Water Flow']
    # Check if the resulting DataFrame is empty
    if water_flow.empty:
        # If no Water Flow data is found, set default values
        water_flow_cfs = -9999.99
        water_flow_cms = -9999.99
    else:
        # Proceed with the normal logic for non-empty DataFrame
        water_flow_si = water_flow['si_value'].round(2).reset_index(drop=True)
        water_flow_cfs = water_flow['us_value'].round(2).reset_index(drop=True)
        # Convert L/s to m³/s and round to the second decimal point
        water_flow_cms = (water_flow_si * 0.001).round(2)
    
    # Create a new dataframe with the parsed data
    df2 = pd.DataFrame({'timestamp_UTC': timestamp,
                        'water_temperature_Celsius': water_temp_si,
                        'water_level_m': water_lvl_si,
                        'water_pressure_kPa': water_pressure_si,
                        'water_pressure_psi': water_pressure_us,
                        'diff_pressure_kPa': diff_pressure_si,
                        'diff_pressure_psi': diff_pressure_us,
                        'water_temperature_Fahrenheit': water_temp_us,
                        'water_level_ft': water_lvl_us,
                        'barometric_pressure_kPa': bar_pressure_si,
                        'barometric_pressure_psi': bar_pressure_us,
                        'discharge_cfs': water_flow_cfs,
                        'discharge_cms': water_flow_cms
                        })

    # Define new columns - used for QC process
    new_columns = {
        'level_corrected_ft': [-9999.99] * len(df2),
        'level_corrected_m': [-9999.99] * len(df2),
        'level_corrected_cm': [-9999.99] * len(df2),
        'qc_status': ["Provisional"] * len(df2)
        }

    # Convert new columns to DataFrame
    new_columns_df = pd.DataFrame(new_columns)

    # Concatenate existing DataFrame with new columns
    df2 = pd.concat([df2, new_columns_df], axis=1)

    # Define the desired order of columns
    desired_column_order = ['timestamp_UTC',
                            'water_temperature_Celsius',
                            'water_level_m',
                            'water_pressure_kPa',
                            'water_pressure_psi',
                            'diff_pressure_kPa',
                            'diff_pressure_psi',
                            'water_temperature_Fahrenheit',
                            'water_level_ft',
                            'barometric_pressure_kPa',
                            'barometric_pressure_psi',
                            'level_corrected_ft',
                            'level_corrected_m',
                            'level_corrected_cm',
                            'discharge_cfs',
                            'discharge_cms',
                            'qc_status']

    # Reorder columns
    df2 = df2[desired_column_order]

    #read csv where data will be backfilled
    csv_df = pd.read_csv(site_name + ".csv")

    # Iterate over the rows in the CSV DataFrame
    for index, csv_row in csv_df.iterrows():
        # Find the index of the row in the original DataFrame with the same timestamp
        idx = df2[df2['timestamp_UTC'] == csv_row.iloc[0]].index
        if not idx.empty:
           # Replace the row in the CSV DataFrame with the row from the original DataFrame
            csv_df.loc[index] = df2.loc[idx].iloc[0]  # Update the row in the CSV DataFrame with the corresponding row from df2
            # Write back the DataFrame to the CSV file, specifying header=True to keep the header
            csv_df.to_csv(site_name + ".csv", index=False, header=True, escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)
            #os.chmod(filepath, 0o775)
    return df2.shape[0]


# Function to parse the data from the HOBOlink API
def parse_precip(hobolink_data, site_name, base_path=None, append_to_single_file=False):
    # Parse data for PrecipMet Tipping Bucket
    df = pd.DataFrame.from_dict(hobolink_data["observation_list"])

    # Filter for precipitation data
    precipitation_pulses = df.loc[df['sensor_measurement_type'] == 'Precipitation']
    if precipitation_pulses.empty:
        precipitation_mm = np.nan
        timestamp = np.nan
    else:
        precipitation_mm = precipitation_pulses['scaled_value'].round(2).reset_index(drop=True)
        timestamp = precipitation_pulses['timestamp'].iloc[:].reset_index(drop=True)

    # Create a new dataframe with the parsed data
    df2 = pd.DataFrame({'timestamp_UTC': timestamp, 'precipitation_mm': precipitation_mm})

    df2['timestamp_UTC'] = pd.to_datetime(df2['timestamp_UTC'], format='%Y-%m-%d %H:%M:%S%z')

    # Calculate accumulated precipitation
    df2['accumulated_precipitation_mm'] = df2['precipitation_mm'].cumsum()

    # Set up base master path
    master_path = Path(base_path if base_path else './') / site_name

    # Ensure Raw directory exists
    raw_path = master_path / "Raw"
    raw_path.mkdir(parents=True, exist_ok=True)

    # Master table raw file path
    master_table_raw = raw_path / f"{site_name}_MasterTable_Raw.csv"

    # Read the site.csv file to get the last recorded accumulated value
    site_csv_path = raw_path / f"{site_name}.csv"
    if site_csv_path.exists():
        with open(site_csv_path, 'r') as file:
            reader = csv.DictReader(file)
            last_record = None
            for row in reader:
                last_record = row
            if last_record is not None:
                last_accumulated_precip = float(last_record['accumulated_precipitation_mm'])
                df2['accumulated_precipitation_mm'] += last_accumulated_precip

    # Identify the index where Timestamp reaches October 1st, 00:00:00 (New Water Year)
    october_indices = df2[df2['timestamp_UTC'].dt.month == 10].index
    if not october_indices.empty:
        october_index = october_indices[0]
    else:
        october_index = None

    if october_index is not None:
        df2['Water_Year'] = (df2['timestamp_UTC'].dt.year + (df2['timestamp_UTC'].dt.month >= 10)).astype(str)
        df2.loc[october_index:, 'accumulated_precipitation_mm'] -= df2.loc[october_index, 'accumulated_precipitation_mm']
        precip_at_reset = df2.loc[october_index, 'precipitation_mm']
        df2.loc[october_index, 'accumulated_precipitation_mm'] = 0

        # Add precipitation recorded at the reset moment to the new water year's accumulated total
        if precip_at_reset > 0:
            df2.loc[october_index + 1, 'accumulated_precipitation_mm'] += precip_at_reset

    df2['accumulated_precipitation_mm'] = df2['accumulated_precipitation_mm'].round(2)

    # Group data by date
    grouped = df2.groupby([
        df2['timestamp_UTC'].dt.year, 
        df2['timestamp_UTC'].dt.month.apply(lambda x: f'{x:02d}'), 
        df2['timestamp_UTC'].dt.day.apply(lambda x: f'{x:02d}')
    ])

    # Append to Master Table Raw
    df2.drop(columns=['Water_Year'], inplace=True, errors='ignore')
    df2.to_csv(master_table_raw, mode='a' if master_table_raw.exists() else 'w', 
            index=False, header=not master_table_raw.exists(), 
            escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)

    # Set file permissions for Master Table Raw (User: RW, Group: R, Others: R) = `0o644`
    os.chmod(master_table_raw, 0o644)

    if append_to_single_file:
        # Define the path for the long-running file
        site_csv_path = raw_path / f"{site_name}.csv"
        df2['timestamp_UTC'] = df2['timestamp_UTC'].dt.strftime('%Y-%m-%d %H:%M:%S') + 'Z'
        mode = 'a' if site_csv_path.exists() else 'w'
        header = not site_csv_path.exists()
        
        # Append data to the single file
        df2.to_csv(site_csv_path, mode=mode, index=False, header=header, escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)

        # Set the file permissions to `0o644`
        os.chmod(site_csv_path, 0o644)

    else:
        for (year, month, day), group in grouped:
            # **Raw Daily Directory**
            raw_daily_path = raw_path / "Raw_Daily" / str(year) / str(month)
            raw_daily_path.mkdir(parents=True, exist_ok=True)

            # **Raw Daily File**
            raw_daily_file = raw_daily_path / f"{site_name}_{year}-{month}-{day}.csv"

            # Format timestamp for storage
            group['timestamp_UTC'] = group['timestamp_UTC'].dt.strftime('%Y-%m-%d %H:%M:%S') + 'Z'
            mode_daily = 'a' if raw_daily_file.exists() else 'w'
            header_daily = not raw_daily_file.exists()

            # Write to Raw Daily File
            group.drop(columns=['Water_Year'], inplace=True, errors='ignore')
            group.to_csv(raw_daily_file, mode=mode_daily, index=False, header=header_daily,
                        escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)

            # Set file permissions for Raw Daily (User: RW, Group: R, Others: R) = `0o644`
            os.chmod(raw_daily_file, 0o644)

    # Return only the number of records processed
    return df2.shape[0]

def backfill_precip(hobolink_data,filename):
    # Parse data for PrecipMet Tipping Bucket
    df = pd.DataFrame.from_dict(hobolink_data["observation_list"])
    # Parse data for PrecipMet Tipping Bucket
    precipitation_pulses = df.loc[df['sensor_measurement_type'] == 'Precipitation']
    if precipitation_pulses.empty:
        # If no water pressure data is found, set default values
        precipitation_mm = np.nan
        timestamp = np.nan
    else:
        precipitation_mm = precipitation_pulses['si_value'].round(2).reset_index(drop=True)
        # Date timestamps for data - each 'sensor_measurement_type' provides a 'timestamp' but only uses one value per timestamp so we drop duplicates   
        timestamp = precipitation_pulses['timestamp'].iloc[:].reset_index(drop=True)

    # Create a new dataframe with the parsed data
    df2 = pd.DataFrame({'timestamp_UTC': timestamp,
                        'precipitation_mm': precipitation_mm
                        })

    # Calculate accumulated total
    df2['accumulated_precipitation_mm'] = df2['precipitation_mm'].cumsum()

    # Read the site.csv file to get the last recorded accumulated value
    site_csv_path = Path(filename)
    if site_csv_path.exists():
        with open(site_csv_path, 'r') as file:
            reader = csv.DictReader(file)
            last_record = None
            for row in reader:
                last_record = row
            if last_record is not None:
                last_accumulated_precip = float(last_record['accumulated_precipitation_mm'])
                df2['accumulated_precipitation_mm'] += last_accumulated_precip
    
    # Identify the index where Timestamp reaches October 1st, 00:00:00
    october_indices = df2[df2['timestamp_UTC'].dt.month == 10].index
    if not october_indices.empty:
        october_index = october_indices[0]
    else:
        # Handle the case where there are no timestamps for October
        # For example, set october_index to None or handle the situation in an appropriate way
        october_index = None

    if october_index is not None:
        # Reset accumulated precipitation to 0 for each water year
        df2['Water_Year'] = (df2['timestamp_UTC'].dt.year + (df2['timestamp_UTC'].dt.month >= 10)).astype(str)
        df2.loc[october_index:, 'accumulated_precipitation_mm'] -= df2.loc[october_index, 'accumulated_precipitation_mm']
        precip_at_reset = df2.loc[october_index, 'precipitation_mm']
        df2.loc[october_index, 'accumulated_precipitation_mm'] = 0

        # Add precipitation recorded at the reset moment to the new water year's accumulated total
        if precip_at_reset > 0:
            df2.loc[october_index + 1, 'accumulated_precipitation_mm'] += precip_at_reset

    csv_df = pd.read_csv(filename)

    # Iterate over the rows in the CSV DataFrame
    for index, csv_row in csv_df.iterrows():
        # Find the index of the row in the original DataFrame with the same timestamp
        idx = df2[df2['timestamp_UTC'] == csv_row.iloc[0]].index
        if not idx.empty:
           # Replace the row in the CSV DataFrame with the row from the original DataFrame
            csv_df.loc[index] = df2.loc[idx].iloc[0]  # Update the row in the CSV DataFrame with the corresponding row from df2
            # Write back the DataFrame to the CSV file, specifying header=True to keep the header
            csv_df.to_csv(filename, index=False, header=True, escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)
            #os.chmod(filepath, 0o775)
    return df2.shape[0]

# split datetime into intervals to pull smaller data chunks for larger pulls of data
# work around to not run into the data limit issues with the HOBOlink_API
# currently doing 
def timestamp_chunks(start_date, end_date, overlap_delta):
    intervals = []
    current_date = start_date
    while current_date < end_date:
        interval_end = min(current_date + timedelta(weeks=2), end_date)
        intervals.append((current_date, interval_end - overlap_delta))
        current_date = interval_end
    # Replace the end of the last interval with the provided end_date
    if intervals:
        intervals[-1] = (intervals[-1][0], end_date)
    return intervals

def find_nan(csv_file):
    # Read the CSV file
    df = pd.read_csv(csv_file)
    
   # Initialize variables to store timestamp ranges just before and after NaN ranges
    nan_ranges = []
    current_start = None
    #nan_found = False

    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        # Check if any NaN values exist in the row
        if row.isnull().any() or (row == "").any():
            # If not already recording, record the timestamp just before the NaN range begins
            if current_start is None:
                if index == df.index[0]:  # If it's the first row, there's no previous row
                    current_start = None
                else:
                    current_start = df.loc[df.index.get_loc(index) - 1, 'timestamp_UTC']
        else:
            # If recording, record the timestamp just after the NaN range ends
            if current_start is not None:
                nan_ranges.append((current_start, row['timestamp_UTC']))
                current_start = None
            #nan_found = True

    # If recording when reaching the end of the DataFrame
    if current_start is not None:
        nan_ranges.append((current_start, df.iloc[-1]['timestamp_UTC']))

    if not nan_ranges:
        return "no"
    else:
        return nan_ranges
    
def find_nan_optimized(csv_file):
    # Read the CSV file
    df = pd.read_csv(csv_file)
    
    # Ensure the 'timestamp_UTC' column exists
    if 'timestamp_UTC' not in df.columns:
        return "Error: 'timestamp_UTC' column not found in the CSV file."
    
    # Replace empty strings with np.nan for uniformity
    df.replace("", np.nan, inplace=True)
    
    # Identify rows with any NaN values
    has_nan = df.isnull().any(axis=1)
    
    # Find start and end indices of NaN ranges
    starts = np.where(has_nan & ~has_nan.shift(1, fill_value=False))[0]
    ends = np.where(has_nan & ~has_nan.shift(-1, fill_value=False))[0]
    
    # Initialize variable to store timestamp ranges
    nan_ranges = []
    
    # Iterate over the start and end indices to form timestamp ranges
    for start, end in zip(starts, ends):
        start_timestamp = df.iloc[start - 1]['timestamp_UTC'] if start > 0 else None
        end_timestamp = df.iloc[end]['timestamp_UTC']
        nan_ranges.append((start_timestamp, end_timestamp))
    
    return nan_ranges if nan_ranges else "no"

# Custom aggregation function that handles -9999 values correctly
def custom_mean(series):
    filtered_series = series[series != -9999]  # Exclude -9999 values
    if len(filtered_series) == 0:  # If all values were -9999
        return -9999.99
    else:
        return filtered_series.mean()
    
# Function to calculate discharge using linear interpolation
def calculate_discharge(stage, rating_curve):
    # Check if the rating curve DataFrame is empty
    if rating_curve.empty:
        return -9999.99  # Set discharge to -9999 if no rating curve
    # If the stage is outside the range of the rating curve, handle accordingly
    if stage < rating_curve['Level.ft'].min() or stage > rating_curve['Level.ft'].max():
        return -9999.99  # Also set to -9999 or any other value indicating out-of-range
    
    # Perform the interpolation
    interpolated_value = np.interp(stage, rating_curve['Level.ft'], rating_curve['discharge.cfs'])

    # Check if the interpolated value is infinite and replace it with -9999.99 if true
    if np.isinf(interpolated_value):
        return -9999.99
    else:
        return interpolated_value

# Adjusted function to handle formatting and special case
def format_shef_value(value):
    # First, handle the special case of -9999.99
    if value == -9999.99:
        return "-9999"
    # Then, format other values as floating-point numbers with appropriate precision
    else:
        return f"{value:.2f}"
    

#!/usr/bin/python
# CW3E Field Team 
# Adolfo Lopez Miranda

# import modules
import sys, requests, json, urllib3, pandas as pd, os
from datetime import datetime, timedelta, timezone
from collections import namedtuple

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

# function to grab last recorded timestamp and convert to JSON format
# timestamp will be used to pull new data since that timestamp
def csv_timestamp(filename):
    # Read the CSV file in reverse order using pandas
    df = pd.read_csv(filename, header=None, skip_blank_lines=True, iterator=True, usecols=[0])
    # Get the last non-empty value for the timestamp column
    date_str = None
    for chunk in df:
        last_row = chunk.dropna().iloc[-1]
        date_str = last_row[last_row.last_valid_index()]
        if pd.notna(date_str):
            break
    date_format = '%Y-%m-%d %H:%M:%S%z' # date timestamp format
    # create datetime object and 5 minutes to last recorded timestamp
    # 5 minutes are added to pull data from the next available timestamp
    dt_start = datetime.strptime(date_str, date_format) + timedelta(minutes=5) # add 5 minutes
    # format string to be used in url
    start_timestamp = dt_start.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + dt_start.strftime("%M") + "%3A" + dt_start.strftime("%S")
    return start_timestamp, dt_start

# function to create timestamp (in UTC)
def current_timestamp():
    current_dt = datetime.now(timezone.utc).replace(microsecond=0, second=0) # previous hours timestamp
    # current_dt = datetime.now(timezone.utc).replace(microsecond=0, second=0, minute=55) - timedelta(hours=1) # previous hours timestamp
    # format string to be used in url
    #end_time = current_dt.strftime("&end_date_time=%Y-%m-%d+%H") + "%3A" + current_dt.strftime("%M")+ "%3A" + current_dt.strftime("%S") # end of the hour
    return current_dt

# function to parse the data from the HOBOlink API
def parse_stream(hobolink_data, filename):
    df = pd.DataFrame.from_dict(hobolink_data["observation_list"])
    # Parse data
    # Water Pressure
    water_pressure = df.loc[df['sensor_measurement_type'] == 'Water Pressure']
    water_pressure_si = water_pressure['si_value'].iloc[:].round(2).reset_index(drop=True)
    water_pressure_us = water_pressure['us_value'].iloc[:].round(2).reset_index(drop=True)
    # Difference Pressure
    diff_pressure = df.loc[df['sensor_measurement_type'] == 'Diff Pressure']
    diff_pressure_si = diff_pressure['si_value'].iloc[:].round(2).reset_index(drop=True)
    diff_pressure_us = diff_pressure['us_value'].iloc[:].round(2).reset_index(drop=True)
    # Water Temperature
    water_temp = df.loc[df['sensor_measurement_type'] == 'Water Temperature']
    water_temp_si = water_temp['si_value'].iloc[:].round(2).reset_index(drop=True)
    water_temp_us = water_temp['us_value'].iloc[:].round(2).reset_index(drop=True)
    # Water Level
    water_lvl = df.loc[df['sensor_measurement_type'] == 'Water Level']
    water_lvl_si = water_lvl['si_value'].iloc[:].round(2).reset_index(drop=True)
    water_lvl_us = water_lvl['us_value'].iloc[:].round(2).reset_index(drop=True)
    # Barometric Pressure
    bar_pressure = df.loc[df['sensor_measurement_type'] == 'Barometric Pressure']
    bar_pressure_si = bar_pressure['si_value'].round(2).iloc[:].reset_index(drop=True)
    bar_pressure_us = bar_pressure['us_value'].round(2).iloc[:].reset_index(drop=True)
    # Battery
    battery = df.loc[df['sensor_measurement_type'] == 'Battery']
    battery_si = battery['si_value'].iloc[:].round(2).reset_index(drop=True)
    #battery_us = battery['us_value'].iloc[:].reset_index(drop=True)
    # Date timestamps for data
    dates = battery['timestamp'].iloc[:].reset_index(drop=True)

    # Create a new dataframe with the parsed data
    df2 = pd.DataFrame({'Timestamp [UTC]': dates,
                        'Water Pressure [kPa]': water_pressure_si,
                        'Water Pressure [psi]': water_pressure_us,
                        'Diff Pressure [kPa]': diff_pressure_si, 
                        'Diff Pressure [psi]': diff_pressure_us, 
                        'Water Temperature [Celsius]': water_temp_si, 
                        'Water Temperature [Fahrenheit]': water_temp_us, 
                        'Water Level [m]': water_lvl_si, 
                        'Water Level [ft]': water_lvl_us, 
                        'Barometric Pressure [kpa]': bar_pressure_si, 
                        'Barometric Pressure [psi]': bar_pressure_us, 
                        'Battery [V]': battery_si 
                        })

    # Save data to csv file
    file_exists = os.path.isfile(filename)
    if file_exists == True:
        header = False
    elif file_exists == False:
        header = True
    df2.to_csv(filename, index=False, mode='a', header=header) # save dateframe to csv file
    
    start_t = datetime.strptime(df2.iloc[0,0], '%Y-%m-%d %H:%M:%S%z') # check start date timestamp
    end_t = datetime.strptime(df2.iloc[-1,0], '%Y-%m-%d %H:%M:%S%z') # check end date timestamp
    parse_df = namedtuple("parsed_df", ["Dataframe", "Start_Timestamp", "End_Timestamp"]) # create tuple to call values from functions
    return parse_df(Dataframe=df2.shape[0],Start_Timestamp=start_t, End_Timestamp=end_t)

# function to parse the data from the HOBOlink API
def parse_precip(hobolink_data, filename):
    df = pd.DataFrame.from_dict(hobolink_data["observation_list"])
    # Parse data
    # Percipitation
    tb_values = df.loc[df['sensor_measurement_type'] == 'Precipitation']
    tb_counts_mm = tb_values['si_value'].iloc[:].round(2).reset_index(drop=True)
    
    # Date timestamps for data
    # check alternative method to grab timestamp
    dates = tb_values['timestamp'].iloc[:].reset_index(drop=True)

    # Create a new dataframe with the parsed data
    df2 = pd.DataFrame({'Timestamp [UTC]': dates,
                        'Precipitation [mm]': tb_counts_mm
                        })

    # Save data to csv file
    file_exists = os.path.isfile(filename)
    if file_exists == True:
        header = False
    elif file_exists == False:
        header = True
    df2.to_csv(filename, index=False, mode='a', header=header) # save dateframe to csv file
    
    start_t = datetime.strptime(df2.iloc[0,0], '%Y-%m-%d %H:%M:%S%z') # check start date timestamp
    end_t = datetime.strptime(df2.iloc[-1,0], '%Y-%m-%d %H:%M:%S%z') # check end date timestamp
    parse_df = namedtuple("parsed_df", ["Dataframe", "Start_Timestamp", "End_Timestamp"]) # create tuple to call values from functions
    return parse_df(Dataframe=df2.shape[0],Start_Timestamp=start_t, End_Timestamp=end_t)

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
    nan_found = False

    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        # Check if any NaN values exist in the row
        if row.isnull().any() or (row == '').any():
            # If not already recording, record the timestamp just before the NaN range begins
            if current_start is None:
                if index == df.index[0]:  # If it's the first row, there's no previous row
                    current_start = None
                else:
                    current_start = df.loc[df.index.get_loc(index) - 1, 'Timestamp [UTC]']
        else:
            # If recording, record the timestamp just after the NaN range ends
            if current_start is not None:
                nan_ranges.append((current_start, row['Timestamp [UTC]']))
                current_start = None
            nan_found = True

    # If recording when reaching the end of the DataFrame
    if current_start is not None:
        nan_ranges.append((current_start, df.iloc[-1]['Timestamp [UTC]']))

    if nan_found:
        return nan_ranges
    else:
        return "no"
    
def backfill_stream(hobolink_data,filename):
    df = pd.DataFrame.from_dict(hobolink_data["observation_list"])
    # Parse data
    # Water Pressure
    water_pressure = df.loc[df['sensor_measurement_type'] == 'Water Pressure']
    water_pressure_si = water_pressure['si_value'].iloc[:].round(2).reset_index(drop=True)
    water_pressure_us = water_pressure['us_value'].iloc[:].round(2).reset_index(drop=True)
    # Difference Pressure
    diff_pressure = df.loc[df['sensor_measurement_type'] == 'Diff Pressure']
    diff_pressure_si = diff_pressure['si_value'].iloc[:].round(2).reset_index(drop=True)
    diff_pressure_us = diff_pressure['us_value'].iloc[:].round(2).reset_index(drop=True)
    # Water Temperature
    water_temp = df.loc[df['sensor_measurement_type'] == 'Water Temperature']
    water_temp_si = water_temp['si_value'].iloc[:].round(2).reset_index(drop=True)
    water_temp_us = water_temp['us_value'].iloc[:].round(2).reset_index(drop=True)
    # Water Level
    water_lvl = df.loc[df['sensor_measurement_type'] == 'Water Level']
    water_lvl_si = water_lvl['si_value'].iloc[:].round(2).reset_index(drop=True)
    water_lvl_us = water_lvl['us_value'].iloc[:].round(2).reset_index(drop=True)
    # Barometric Pressure
    bar_pressure = df.loc[df['sensor_measurement_type'] == 'Barometric Pressure']
    bar_pressure_si = bar_pressure['si_value'].round(2).iloc[:].reset_index(drop=True)
    bar_pressure_us = bar_pressure['us_value'].round(2).iloc[:].reset_index(drop=True)
    # Battery
    battery = df.loc[df['sensor_measurement_type'] == 'Battery']
    battery_si = battery['si_value'].iloc[:].round(2).reset_index(drop=True)
    #battery_us = battery['us_value'].iloc[:].reset_index(drop=True)
    # Date timestamps for data
    dates = battery['timestamp'].iloc[:].reset_index(drop=True)

    # Create a new dataframe with the parsed data
    df2 = pd.DataFrame({'Timestamp [UTC]': dates,
                        'Water Pressure [kPa]': water_pressure_si,
                        'Water Pressure [psi]': water_pressure_us,
                        'Diff Pressure [kPa]': diff_pressure_si, 
                        'Diff Pressure [psi]': diff_pressure_us, 
                        'Water Temperature [Celsius]': water_temp_si, 
                        'Water Temperature [Fahrenheit]': water_temp_us, 
                        'Water Level [m]': water_lvl_si, 
                        'Water Level [ft]': water_lvl_us, 
                        'Barometric Pressure [kpa]': bar_pressure_si, 
                        'Barometric Pressure [psi]': bar_pressure_us, 
                        'Battery [V]': battery_si 
                        })

    csv_df = pd.read_csv(filename)
    # Convert the timestamp column to datetime format if it's not already
    #csv_df['Timestamp [UTC]'] = pd.to_datetime(csv_df['Timestamp[UTC]'])

    # Iterate over the rows in the CSV DataFrame
    for index, csv_row in csv_df.iterrows():
        # Find the index of the row in the original DataFrame with the same timestamp
        idx = df2[df2['Timestamp [UTC]'] == csv_row.iloc[0]].index
        if not idx.empty:
           # Replace the row in the CSV DataFrame with the row from the original DataFrame
            csv_df.loc[index] = df2.loc[idx].iloc[0]  # Update the row in the CSV DataFrame with the corresponding row from df2

        # Save data to csv file
    file_exists = os.path.isfile(filename)
    if file_exists == True:
        header = False
    elif file_exists == False:
        header = True
    csv_df.to_csv(filename, index=False, header=header) # save dateframe to csv file
    
    start_t = datetime.strptime(df2.iloc[0,0], '%Y-%m-%d %H:%M:%S%z') # check start date timestamp
    end_t = datetime.strptime(df2.iloc[-1,0], '%Y-%m-%d %H:%M:%S%z') # check end date timestamp
    parse_df = namedtuple("parsed_df", ["Dataframe", "Start_Timestamp", "End_Timestamp"]) # create tuple to call values from functions
    return parse_df(Dataframe=df2.shape[0],Start_Timestamp=start_t, End_Timestamp=end_t)

def backfill_precip(file_csv):
    
    return

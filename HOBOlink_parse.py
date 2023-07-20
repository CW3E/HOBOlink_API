#!/usr/bin/python
# CW3E Field Team 
# Adolfo Lopez Miranda
# June 08, 2023

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

# function to grab last recorded timestamp and convert to JSON format
# timestamp will be used to pull new data since that timestamp
def csv_timestamp(filename):
    #check timestamp of last entry of the csv file
    df_file = pd.read_csv(filename) # read csv
    df = df_file.iloc[-1:,0].values # last recorded timestamp
    date_str = df[0]
    date_format = '%Y-%m-%d %H:%M:%S%z' # date timestamp format
    # create datetime object and 5 minutes to last recorded timestamp
    # 5 minutes are added to pull data from the next available timestamp
    date_obj = datetime.strptime(date_str, date_format) + timedelta(minutes=5) # add 5 minutes
    # format string to be used in url
    start_timestamp = date_obj.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + date_obj.strftime("%M") + "%3A" + date_obj.strftime("%S")
    return start_timestamp, date_obj

# function to create timestamp (in UTC)
def current_timestamp():
    current_dt = datetime.now(timezone.utc).replace(microsecond=0, second=0, minute=55) - timedelta(hours=1) # previous hours timestamp
    # format string to be used in url
    end_time = current_dt.strftime("&end_date_time=%Y-%m-%d+%H") + "%3A" + current_dt.strftime("%M")+ "%3A" + current_dt.strftime("%S") # end of the hour
    return end_time, current_dt

def check_error(hobolink_data):
    
    return

# function to parse the data from the HOBOlink API
def parse_data(hobolink_data, filename):
    df = pd.DataFrame.from_dict(hobolink_data["observation_list"])
    # Parse data
    # columns for SI and US values for each sensor measurement
    si_col = 4
    us_col = 6
    # Water Pressure
    water_pressure_si = df.iloc[0::6, si_col].reset_index(drop=True)
    water_pressure_us = df.iloc[0::6, us_col].reset_index(drop=True)
    # Difference Pressure
    diff_pressure_si = df.iloc[1::6, si_col].reset_index(drop=True)
    diff_pressure_us = df.iloc[1::6, us_col].reset_index(drop=True)
    # Water Temperature
    water_temp_si = df.iloc[2::6, si_col].reset_index(drop=True)
    water_temp_us = df.iloc[2::6, us_col].reset_index(drop=True)
    # Water Level
    water_lvl_si = df.iloc[3::6, si_col].reset_index(drop=True)
    water_lvl_us = df.iloc[3::6, us_col].reset_index(drop=True)
    # Barometric Pressure
    bar_pressure_si = df.iloc[4::6, si_col].reset_index(drop=True)
    bar_pressure_us = df.iloc[4::6, us_col].reset_index(drop=True)
    # Battery
    battery_si = df.iloc[5::6, si_col].reset_index(drop=True)
    battery_us = df.iloc[5::6, us_col].reset_index(drop=True)
    # Date timestamps for data
    dates = df.iloc[0::6,2].reset_index(drop=True)

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


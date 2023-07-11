#!/usr/bin/python
# CW3E Field Team 
# Adolfo Lopez Miranda
# June 08, 2023

# import modules
import sys
import requests
import json
import urllib3
import pandas as pd
import os
from datetime import datetime

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

def timestamp(filename):
    #check timestamp of last entry of the csv file
    df_file = pd.read_csv(filename)
    df = df_file.iloc[-1:,0].values

    date_str = df[0]
    date_format = '%Y-%m-%d %H:%M:%S%z'

    date_obj = datetime.strptime(date_str, date_format)
    start_min =  date_obj.strftime("%M")
        
    return date_obj, start_min

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
    df2.to_csv(filename, index=False, mode='a', header=header)
    return
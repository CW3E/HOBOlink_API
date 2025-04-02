#!/usr/bin/env python
# CW3E Field Team 
# Adolfo Lopez Miranda

# import modules
import requests, os, time, pandas as pd, csv, numpy as np, logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
from HOBOlink_parse import convert_time, csv_timestamp, parse_stream, parse_precip

# load .env file - the .env file is the best place to store sensitive info such as the user ID, and token information
load_dotenv(find_dotenv())

# load path where data will be stored - 
#base_dir = "/data/CW3E_data/CW3E_PrecipMet_Archive/"
base_dir = "/data/CW3E_data/CW3E_Streamflow_Archive/"
base_dir_path = Path(base_dir)
# Note base_dir will need to be indicated in the parse fucntion - the default is None (data will be stored in the same place as where the script is running)

# SHEF Output Toggle
shef = True

site_type = 'S' #S = streams and P = Precip
# load site metadata CSV into DataFrame
if site_type == 'S' or site_type == 's':
    df_sites = pd.read_csv('Streams_Metadata.csv').set_index('site_ID')
elif site_type == 'P' or site_type == 'p':
    # load site metadata CSV into DataFrame
    df_sites = pd.read_csv('PrecipMet_Metadata.csv').set_index('site_ID')

# HOBOlink API Token
token = os.environ.get("TOKEN") # user ID found on HOBOlink

# loop through each site in the DataFrame
for site_id, row in df_sites.iterrows():
    try:
        print(f'Pulling data for {site_id}.')
        logger = str(row['logger_SN'])
        cdec_id = row['CDEC_ID']
        
        # if cdec_id is not included set it to None
        if cdec_id == 'NaN' or cdec_id == '':
            cdec_id = None
    
        # Convert DataFrame's 'start_time' to string format as needed by your API URL
        initial_start_time = row['start_time'] # Adjust format as necessary
        logging_int = row['logging_int']
        
        #site_log_file = base_dir + site_id + "/" + site_id + ".log"
        site_log_file = site_id + ".log"
        # create multiple log files:
        site_logger = logging.getLogger(site_id + '_Logger')
        site_logger.setLevel(logging.DEBUG)
        site_handler = logging.FileHandler(site_log_file, mode='a')
        site_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S%z')
        site_handler.setFormatter(site_formatter)
        site_logger.addHandler(site_handler)
        
        # file name of long running file
        # need to provide path to where this is located at to check timestamp of last successful log
        file_csv = site_id + "_MasterTable_Raw.csv"
        # full path to the site csv file
        file_csv_path = base_dir_path / site_id / "Raw" / file_csv
    
        # check if file exists
        file_exists = os.path.isfile(file_csv_path)
        # file exists
        if file_exists == True:
            start_time, start_dt = csv_timestamp(file_csv_path, logging_int) # read last entry in file and use last timestamp as the start time for the data pulled
        #file does not exist  
        elif file_exists == False:
            start_dt, start_time = convert_time(initial_start_time, target_format="start") # use start time found in metadata csv - Uses the true start time from deployment
        
        # end time isn't specified, the script will pull all new data regardless of what time it is ran
        # This method can only be ran once per account as Time Frame Querying is tracked on the backend
        # Alternative method is to use end_time = "&end_date_time=YYYY-MM-DD+HH%3Amm%3ASS" in UTC format
        end_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + 'Z'
        end_dt, end_time = convert_time(end_str,target_format="end")
        #end_dt, end_time = start_time_offset(initial_start_time, 180, target_format="end") #useful if need to run tests
        #end_time = "&only_new_data=true"
         
        # HOBOlink url to get data from file endpoints
        hobolink_api_url = "https://api.hobolink.licor.cloud/v1/data?loggers=" + logger + start_time + end_time
    
        while True:
            #  send data request using token
            api_call_headers = {
                'accept': 'application/json',
                'Authorization': 'Bearer ' + token} # HTTP Authentication required for HOBOlink
            api_call_response = requests.get(hobolink_api_url, headers=api_call_headers, verify=True) # requests a representation of the specified resource
            if api_call_response.status_code == 200: 
                # Convert data to dict
                data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
                if len(data["data"]) > 0 :
                    #print(data['observation_list'])
                    #parse data based off site type
                    if site_type == 'S' or site_type == 's':
                        data_int = parse_stream(data, site_id, cdec_id, base_path=base_dir, shef_toggle=shef)
                    elif site_type == 'P' or site_type == 'p':
                        data_int = parse_precip(data, site_id, base_path=None, append_to_single_file=True, shef_toggle=False)
                    site_logger.info('Data found and recorded to csv file.')
                elif len(data["observation_list"]) == 0:
                    site_logger.warning('No new data since the last recorded timestamp.')            
                break
            elif api_call_response.status_code == 400 or api_call_response.status_code == 500 or api_call_response.status_code == 509: 
                # Failures have occured - Record error code and error description in log file
                data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
                site_logger.error('error: %s\nmessage: %s\nerror_description: %s' %(data["error"], data["message"], data["error_description"]))
            else:
                # record status code and response in log file
                data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
                site_logger.error('Unexpected status code: %s\n Unexpected Response: %s' %(api_call_response.status_code, data))
            break
    except Exception as e:
        print(f"An error occurred for {site_id}: {e}")

#End of script

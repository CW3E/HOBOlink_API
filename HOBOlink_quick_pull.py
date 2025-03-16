#!/usr/bin/env python
# CW3E Field Team 
# Adolfo Lopez Miranda

# import modules
import requests, os, time, pandas as pd, csv, numpy as np
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv, find_dotenv
#from pathlib import Path
from HOBOlink_parse import get_new_token, parse_stream, timestamp_chunks, find_nan_optimized, backfill_stream, calculate_discharge

# load .env file - the .env file is the best place to store sensitive info such as the user ID, and token information
load_dotenv(find_dotenv())

# load path where data will be stored
base_dir = "/data/CW3E_data/CW3E_Streamflow_Archive/"
# Note base_dir will need to be indicated in the parse fucntion - the default is None (data will be stored in the same place as where the script is running)
#base_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

# SHEF Output Toggle
shef = True

# HOBOlink account and device info
logger_id='22050044' # update this to the correct Logger SN - can be found on HOBOlink
site_id='WHT' # Change this to the appropriate site ID
cdec = 'WIC' # Change this to the appropriate cdec ID
site_type = 'S' #S = streams and P = Precip

# HOBOlink API Token
token = os.environ.get("TOKEN") # user ID found on HOBOlink

#-------------------------------------------------------------------------------------------------------------------------------------
# Specify the start and end time for data to be pulled
# The HOBOlink API has limitations on how much data can be pulled at any given time.
# Max is 100,000 data points. It's recommended to break up data pulls into smaller chunks

# timestamps are in UTC
date_format = '%Y-%m-%d %H:%M:%S%z' # date timestamp format

# start_time corresponds to the time in which the first packet of a data is pulled from
start_str='2024-06-26 18:55:00Z' # update the start time in UTC
start_dt = datetime.strptime(start_str, date_format)
#start_time = start_dt.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + start_dt.strftime("%M") + "%3A" + start_dt.strftime("%S")

# end_time corresponds to the time for the last data packet that will be pulled
end_str='2024-08-13 00:00:00Z'# update the end time in UTC
end_dt = datetime.strptime(end_str, date_format)
#end_time = end_dt.strftime("&end_date_time=%Y-%m-%d+%H") + "%3A" + end_dt.strftime("%M") + "%3A" + end_dt.strftime("%S")

# interval - logging interval setup on HOBOlink
# streams is 15 and precip is 2 - as of March 2024
interval = 15
int_t =  60 * interval  #converting log interval into seconds
overlap_t = timedelta(seconds=int_t) # will be used to break up data chunks appropriately on data pull
    
# workaround to avoid data limit is to break up timestamps into smaller intervals (if needed)
timestamp_intervals = timestamp_chunks(start_dt, end_dt, overlap_t)
url_intervals = []  # list to hold url str with timestamp parameters
for interval in timestamp_intervals:
    url_start = interval[0].strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + interval[0].strftime("%M") + "%3A" + interval[0].strftime("%S")
    url_end = interval[1].strftime("&end_date_time=%Y-%m-%d+%H") + "%3A" + interval[1].strftime("%M") + "%3A" + interval[1].strftime("%S")
    url_timestamp = url_start + url_end
    url_intervals.append(url_timestamp)

#--------------------------------------------------------------------------------------------------------------------------------------------------
# loop over the intervals and make requests to get the data
print("Timestamp ranges for the desired data:", start_str, "to", end_str)

for i in range(len(url_intervals)):
    print("pulling data chunk for the following period:")
    print(timestamp_intervals[i][0].strftime("%Y-%m-%d %H:%M:%SZ"), "-", timestamp_intervals[i][1].strftime("%Y-%m-%d %H:%M:%SZ"))
    # HOBOlink url to get data from file endpoints
    hobolink_api_url = "https://api.hobolink.licor.cloud/v1/data?loggers=" + logger_id + url_intervals[i]
    while True:
        #  send data request using token
        api_call_headers = {
            'accept': 'application/json',
            'Authorization': 'Bearer ' + token} # HTTP Authentication required for HOBOlink
        api_call_response = requests.get(hobolink_api_url, headers=api_call_headers, verify=True) # requests a representation of the specified resource
        if api_call_response.status_code == 200: 
            # Convert data to dict
            data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
            
            # TODO: resample the data
            
            
            if len(data["observation_list"]) > 0 :
                data_int = parse_stream(data, site_id, cdec, base_path=base_dir, append_to_single_file=False, shef_toggle=shef)
            elif len(data["observation_list"]) == 0:
                print('No data available.')
            break
        elif api_call_response.status_code == 400 or api_call_response.status_code == 500 or api_call_response.status_code == 509: 
            # Failures have occured - Record error code and error description in log file
            data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
            print('error: %s\nmessage: %s\nerror_description: %s' %(data["error"], data["message"], data["error_description"]))
        else:
            # record status code and response in log file
            data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
            print('Unexpected status code: %s\n Unexpected Response: %s' %(api_call_response.status_code, data))
        break
    time.sleep(5) #delay added to avoid excessive requests to server.

#----------------------------------------------------------------------------------------------------------------------------------
# Backfill data if data points were missed
# check csv for missing data points
file_csv = f'{site_id}_MasterTable.csv'
#nan_check = find_nan(file_csv)
nan_check = find_nan_optimized(f'{base_dir}/{site_id}/{file_csv}')
print(nan_check)
# If NaN's or blank spaces exist backfill that data by pulling data again
# check if NaN's or blank spaces were found
nan_range = []
url_intervals = []  # list to hold url str with timestamp parameters
if nan_check != "no":
    print("Timestamp ranges with NaN values or empty spaces:")
    for start, end in nan_check:
        print(f"Start: {start}, End: {end}")
        datetime.strptime(start, date_format)
        nan_range.append((datetime.strptime(start, date_format), datetime.strptime(end, date_format)))
    
    for nan_start, nan_end in nan_range:
        # workaround to avoid data limit is to break up timestamps into smaller intervals (if needed)
        timestamp_intervals = timestamp_chunks(nan_start, nan_end, overlap_t)
        #print(timestamp_intervals)
        for interval in timestamp_intervals:
            url_start = interval[0].strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + interval[0].strftime("%M") + "%3A" + interval[0].strftime("%S")
            url_end = interval[1].strftime("&end_date_time=%Y-%m-%d+%H") + "%3A" + interval[1].strftime("%M") + "%3A" + interval[1].strftime("%S")
            url_timestamp = url_start + url_end
            url_intervals.append(url_timestamp)
    
    #print(url_intervals)

    for url in url_intervals:
        print("Backfilling data.")
        # HOBOlink url to get data from file endpoints
        hobolink_api_url = "https://api.hobolink.licor.cloud/v1/data?loggers=" + logger_id + url_intervals[i]
    
        while True:
            #  send data request using token
            api_call_headers = {
                'accept': 'application/json',
                'Authorization': 'Bearer ' + token} # HTTP Authentication required for HOBOlink
            api_call_response = requests.get(hobolink_api_url, headers=api_call_headers, verify=True) # requests a representation of the specified resource
            if api_call_response.status_code == 200: 
                # Convert data to dict
                data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
                if len(data["observation_list"]) > 0 :
                    #print(data["observation_list"])
                    backfill_stream(data,file_csv)
                    #print("Data has been parsed and stored in:", f)
                elif len(data["observation_list"]) == 0:
                    print('No data available.')
                break
            elif api_call_response.status_code == 400 or api_call_response.status_code == 500 or api_call_response.status_code == 509: 
                # Failures have occured - Record error code and error description in log file
                data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
                print('error: %s\nmessage: %s\nerror_description: %s' %(data["error"], data["message"], data["error_description"]))
            else:
                # record status code and response in log file
                data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
                print('Unexpected status code: %s\n Unexpected Response: %s' %(api_call_response.status_code, data))
            break
        time.sleep(5) #delay added to avoid excessive requests to server.

else:
    print("No NaN's or blanks found. Data is complete.")

#------------------------------------------------------------------------------------------------------------------------------
# TODO: have it resample data between the start and end date.
# Have it put the resampled data into the correct place in the MasterTable.
'''
# Resample data if neccessary - this is only necessary for streams at the moment. Will output a seperate csv from the raw data
# Define the target date for comparison (March 15th, 2024)
target_date = datetime(2024, 8, 1, tzinfo=timezone.utc) # all streams were switch to 15th minute logging intervals around this time
# Check if start_dt is before the target date and if it also a Stream site (S)
if site_type == 'S' or site_type == "s" and start_dt < target_date:
    df = pd.read_csv(f'{base_dir}/{site_id}/{file_csv}')
    # Convert the timestamp column to datetime
    df['timestamp_UTC'] = pd.to_datetime(df['timestamp_UTC'])
    # Set the timestamp column as the index
    df.set_index('timestamp_UTC', inplace=True)
    # Step 1: Convert -9999.99 to NaN
    df.replace(-9999.99, np.nan, inplace=True)
    # Define an aggregation dictionary that specifies how to aggregate each column
    # For numeric columns, use 'mean'; exclude or use a different function for non-numeric columns
    aggregations = {col: 'mean' for col in df.columns if col != 'qc_status'}
    # You can add the 'qc_status' column back later or handle it separately as needed
    # Resample using the defined aggregations
    df_resampled = df.resample('15T').agg(aggregations)
    # Round the values to two decimal places
    df_resampled = df_resampled.round(2)
    # Fill NaN values with -9999.99 for numeric columns only
    for col in df_resampled.select_dtypes(include=['number']).columns:
        if col != 'qc_status':  # Skip 'qc_status' column
            df_resampled[col] = df_resampled[col].fillna(-9999.99)
                
    #add qc column back in
    df_resampled["qc_status"] = 'Provisional'
    # Convert timestamp back to string format
    df_resampled.index = df_resampled.index.strftime('%Y-%m-%d %H:%M:%SZ')
    # Output the resampled data to a new CSV file
    # Save data to csv file
    resampled_csv = f'{base_dir}/{site_id}/{site_id}_resampled_data.csv'
    file_exists = os.path.isfile(resampled_csv)
    if file_exists == True:
        header = False
    elif file_exists == False:
        header = True
    #df_resampled.to_csv(resampled_csv, mode='a', header=header, escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)
    #print("Data has been resampled and stored in:", resampled_csv)
    
    df_resampled.to_csv(resampled_csv, mode='a', header=header, escapechar='\\', quoting=csv.QUOTE_NONNUMERIC)
    print("Data has been resampled and stored in:", resampled_csv)
    
print("Data pull complete for:", site_id)

# Write the RawDaily files.
write_RawDaily(pd.read_csv(resampled_csv), site_id, base_dir)

# Write the hourly SHEF_Output files, and a backfill file with all the shef codes to send to CDEC.
#write_SHEFhourly(pd.read_csv(resampled_csv), site_id, base_dir)
'''
#-----------------------------------------------------------------------------------------
# process stream data
# Define the path to the rating curve and stage data files
# Update the base_path as per your network configuration or direct path
#base_dir = "/data/CW3E_data/CW3E_PrecipMet_Archive/"
# could append streams or precip specific directory to the base_dir in the site type logic statements
"""
# Read the site.csv file to get the last recorded accumulated value
site_csv_path = Path(base_path if base_path else f'./{site_name}.csv')
filename = f"{site_name}.csv"
site_csv_path = site_csv_path / filename
"""
'''
rating_curve_path = base_dir / f'{site_id}/Rating_Curve/{site_id}.rating_curve_100_points.csv' #if running within parse script change site_id to site_name
stage_data_path = "whatever data var we're using for stage data" # if running inside parse script it will be the column name of the dataframe

# load the rating curve
rating_curve = pd.read_csv(rating_curve_path)

# load stage data
stage_data = pd.read_csv(stage_data_path) 

# apply the rating curve to calculate discharge
stage_data['discharge_cfs'] = stage_data['stage'].apply(lambda x: calculate_discharge(x, rating_curve))

# convert from cfs to cms
stage_data['discharge_cms'] = stage_data["discharge_cfs"] * 0.0283168

# output the result
print(stage_data)

# store data to csv
'''


#End of script

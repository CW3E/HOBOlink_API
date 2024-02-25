#!/usr/bin/env python
# CW3E Field Team 
# Adolfo Lopez Miranda

# import modules
import requests, os, time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv, find_dotenv
from HOBOlink_parse import get_new_token, parse_precip, parse_stream, timestamp_chunks, find_nan, backfill_stream

# load .env file - the .env file is the best place to store sensitive info such as the user ID, and token information
load_dotenv(find_dotenv())

# HOBOlink account and device info
user_id = os.environ.get("USER_ID") # user ID found on HOBOlink
logger_id='XXXXXXX' # update this to the correct Logger SN - can be found on HOBOlink
site_id='XXX' # Change this to the appropriate site ID

#HOBOlink authentication server
# url provided by HOBOlink Web Services V3 Developer's Guide
auth_server_url = "https://webservice.hobolink.com/ws/auth/token"

# credentials provided by Onset Tech support
client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")

#-------------------------------------------------------------------------------------------------------------------------------------
# Specify the start and end time for data to be pulled
# The HOBOlink API has limitations on how much data can be pulled at any given time.
# Max is 100,000 data points. It's recommended to break up data pulls into smaller chunks

# timestamps are in UTC
date_format = '%Y-%m-%d %H:%M:%S%z' # date timestamp format

# start_time corresponds to the time in which the first packet of a data is pulled from
start_str='2023-10-10 21:45:00Z' # update the start time in UTC
start_dt = datetime.strptime(start_str, date_format)
#start_time = start_dt.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + start_dt.strftime("%M") + "%3A" + start_dt.strftime("%S")

# end_time corresponds to the time for the last data packet that will be pulled
end_str='2024-02-16 20:15:00Z'# update the end time in UTC
end_dt = datetime.strptime(end_str, date_format)
#end_time = end_dt.strftime("&end_date_time=%Y-%m-%d+%H") + "%3A" + end_dt.strftime("%M") + "%3A" + end_dt.strftime("%S")

# interval - logging interval setup on HOBOlink
# streams is 5 and precip is 2 - as of Feb 2024
interval = 5
int_t =  60 * interval  #converting log interval into seconds
overlap_t = timedelta(seconds=int_t) # will be used to break up data chunks appropriately on data pull
    
# file name
csv_time = start_dt.strftime("%Y-%m-%d_%H%M") + "_to_" + end_dt.strftime("%Y-%m-%d_%H%M") #timestamp to include in csv name
file_csv = site_id + "_" + csv_time + ".csv"

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
    hobolink_api_url = "https://webservice.hobolink.com/ws/data/file/JSON/user/" + user_id + "?loggers=" + logger_id + url_intervals[i]

    while True:
        # Obtain a token before calling the HOBOlink API for the first time
        token = get_new_token(auth_server_url, client_id, client_secret)
        #  Use the API with the newly acquired token
        api_call_headers = {'Authorization': 'Bearer ' + token} # HTTP Authentication required for HOBOlink
        api_call_response = requests.get(hobolink_api_url, headers=api_call_headers, verify=True) # requests a representation of the specified resource
        # Create a new token incase it expires
        # Token from Hobolink will expire after 10 minutes, or if another one is expired
        if api_call_response.status_code == 200: 
            # Convert data to dict
            data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
            if len(data["observation_list"]) > 0 :
                check_data = parse_stream(data, file_csv)
                print("Data has been parsed and stored in:", file_csv)
            elif len(data["observation_list"]) == 0:
                print('No data available.')
            break
        elif api_call_response.status_code == 401: #http 401 code will appear if token is expired
            token = get_new_token(auth_server_url, client_id, client_secret)
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

counter = 0
while counter < 2:
    # check csv for missing data points
    nan_check = find_nan(file_csv)

    # If NaN's or blank spaces exist backfill that data by pulling data again
    # check if NaN's or blank spaces were found
    nan_range = []
    if nan_check != "no":
        print("Timestamp ranges with NaN values or empty spaces:")
        for start, end in nan_check:
            print(f"Start: {start}, End: {end}")
            datetime.strptime(start, date_format)
            nan_range.append((datetime.strptime(start, date_format), datetime.strptime(end, date_format)))
        
        for nan_interval in nan_range:
            # workaround to avoid data limit is to break up timestamps into smaller intervals (if needed)
            timestamp_intervals = timestamp_chunks(nan_interval[0], nan_interval[1], overlap_t)
            url_intervals = []  # list to hold url str with timestamp parameters
            for interval in timestamp_intervals:
                url_start = interval[0].strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + interval[0].strftime("%M") + "%3A" + interval[0].strftime("%S")
                url_end = interval[1].strftime("&end_date_time=%Y-%m-%d+%H") + "%3A" + interval[1].strftime("%M") + "%3A" + interval[1].strftime("%S")
                url_timestamp = url_start + url_end
                url_intervals.append(url_timestamp)

            #--------------------------------------------------------------------------------------------------------------------------------------------------
            # loop over the intervals and make requests to get the data
            print("Backfilling data for timestamp ranges:", start, "to", end)

            for i in range(len(url_intervals)):
                print("pulling data chunk for the following period:")
                print(timestamp_intervals[i][0].strftime("%Y-%m-%d %H:%M:%SZ"), "-", timestamp_intervals[i][1].strftime("%Y-%m-%d %H:%M:%SZ"))
                # HOBOlink url to get data from file endpoints
                hobolink_api_url = "https://webservice.hobolink.com/ws/data/file/JSON/user/" + user_id + "?loggers=" + logger_id + url_intervals[i]

                while True:
                    # Obtain a token before calling the HOBOlink API for the first time
                    token = get_new_token(auth_server_url, client_id, client_secret)
                    #  Use the API with the newly acquired token
                    api_call_headers = {'Authorization': 'Bearer ' + token} # HTTP Authentication required for HOBOlink
                    api_call_response = requests.get(hobolink_api_url, headers=api_call_headers, verify=True) # requests a representation of the specified resource
                    # Create a new token incase it expires
                    # Token from Hobolink will expire after 10 minutes, or if another one is expired
                    if api_call_response.status_code == 200: 
                        # Convert data to dict
                        data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
                        if len(data["observation_list"]) > 0 :
                            check_data = backfill_stream(data, file_csv)
                            print("Data has been parsed and stored in:", file_csv)
                        elif len(data["observation_list"]) == 0:
                            print('No data available.')
                        break
                    elif api_call_response.status_code == 401: #http 401 code will appear if token is expired
                        token = get_new_token(auth_server_url, client_id, client_secret)
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
        break
    counter += 1
# End of script

#!/usr/bin/python
# CW3E Field Team 
# Adolfo Lopez Miranda
# June 08, 2023

# import modules
import requests
import logging
import urllib3
import os
from datetime import datetime, timedelta, timezone
from HOBOlink_parse import get_new_token, timestamp, parse_data

# Input your info for user ID, SN for logger, and client credentials
# HOBOlink account and device info
user_id = 'XXXXX' # user ID found on HOBOlink
logger_id = 'XXXXXXXX' # SN from logger
site_id = "XXX" #nickname given to device on HOBOlink

#HOBOlink authentication server
# url provided by HOBOlink Web Services V3 Developer's Guide
auth_server_url = "https://webservice.hobolink.com/ws/auth/token"

# credentials provided by Onset Tech support
client_id = 'XXXXXX'
client_secret = 'XXXXXXXXXXXXXX'

# create log file to capture warnings
logging.basicConfig(filename=site_id + '.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  datefmt='%Y-%m-%d %H:%M:%S%z')
logging.captureWarnings(True)

# file name
daily_file_csv = site_id + ".csv"

# check if file exists
file_exists = os.path.isfile(daily_file_csv)
if file_exists == True:
    # file exists so grab last date timestamp
    start_dt, start_min = timestamp(daily_file_csv) # last entry in file
    previous_dt = datetime.now(timezone.utc) - timedelta(hours=1) # current time (previous hour)
    # format strings for url 
    start_time = start_dt.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + start_min + "%3A01" # start of the hour
    end_time = previous_dt.strftime("&end_date_time=%Y-%m-%d+%H") + "%3A59%3A59" # end of the hour
    # Difference in time
    time_diff = previous_dt.replace(microsecond=0, second=0, minute=55) - start_dt
elif file_exists == False:
    # file does not exist
    start_dt = datetime.now(timezone.utc)
    previous_dt = datetime.now(timezone.utc) - timedelta(hours=1) # current time (previous hour)
    # format strings for url 
    start_time = previous_dt.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A00%3A00" # start of the hour
    end_time = previous_dt.strftime("&end_date_time=%Y-%m-%d+%H") + "%3A59%3A59" # end of the hour
    # Difference in time
    time_diff = start_dt - previous_dt

# Difference in time (hours) for data being pulled
hours = time_diff.total_seconds() / 3600
t = int(hours * 12) # expected values - data is recorded in 5 minute intervals

# HOBOlink url to get data from file endpoints
hobolink_api_url = "https://webservice.hobolink.com/ws/data/file/JSON/user/" + user_id + "?loggers=" + logger_id + start_time + end_time

# Obtain a token before calling the HOBOlink API for the first time
token = get_new_token(auth_server_url, client_id, client_secret)

while True:
#  Use the API with the newly acquired token
    api_call_headers = {'Authorization': 'Bearer ' + token} # HTTP Authentication required for HOBOlink
    api_call_response = requests.get(hobolink_api_url, headers=api_call_headers, verify=True) # requests a representation of the specified resource
    
# Create a new token incase it expires
# Token from Hobolink will expire after 10 minutes, or if another one is expired
    if	api_call_response.status_code == 401: #http 401 code will appear if token is expired
        token = get_new_token(auth_server_url, client_id, client_secret)
    else:
        # Convert data to dict
        data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation

    break

# check size of data packet
if len(data["observation_list"]) == t :
    print("New data is available, and is complete.")
    parse_data(data, daily_file_csv) # pull and store data
elif len(data["observation_list"]) == 0 :
    logging.warning("No data new data since the last recorded timestamp.")
elif 0 < len(data["observation_list"]) < t :
    logging.warning("There is new data, but may be incomplete.")
    parse_data(data, daily_file_csv) # pull and store data
elif len(data["observation_list"]) > t :
    logging.warning("The data packet is greater than what is expected and duplicates may exist for some timestamps.")
    parse_data(data, daily_file_csv) # pull and store data
    
# End of script
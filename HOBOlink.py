#!/usr/bin/python
# CW3E Field Team 
# Adolfo Lopez Miranda
# June 08, 2023

# import modules
import sys
import requests
import json
import logging
import os
import time
from datetime import datetime, timedelta

# record warnings during process
logging.captureWarnings(True)

# Input your info for user ID, SN for logger, and client credentials
# HOBOlink account and device info
user_id = 'XXXXX' # user ID found on HOBOlink
logger_id = 'XXXXXXXX' # SN from logger
site_id = "XXX" #nickname given to device on HOBOlink

# credentials provided by Onset Tech support
client_id = 'XXXXXX'
client_secret = 'XXXXXXXXXXXXXXXXXXXX'

# Current date and time
current_datetime = datetime.now()
# Subtract one hour using a timedelta
previous_hour_datetime = current_datetime - timedelta(hours=1)

# format strings for url 
start_time = previous_hour_datetime.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A00%3A00" # start of the hour
end_time = current_datetime.strftime("&end_date_time=%Y-%m-%d+%H") + "%3A59%3A59" # end of the hour

# HOBOlink url to get data from file endpoints
hobolink_api_url = "https://webservice.hobolink.com/ws/data/file/JSON/user/" + user_id + "?loggers=" + logger_id + start_time + end_time

# Format folder and file prior to logging
folder_date = previous_hour_datetime.strftime("/%Y/%m/%d/")
folder = "HOBOlink" + "/" + site_id + folder_date
#parent_dir = os.getcwd()
os.system("mkdir -p " + folder)
daily_file = folder + site_id + previous_hour_datetime.strftime("_%Y-%m-%d") + ".txt"

# function to obtain a new OAuth 2.0 token from the authentication server
def get_new_token():
    # url provided by HOBOlink Web Services V3 Developer's Guide
    auth_server_url = "https://webservice.hobolink.com/ws/auth/token"

    token_req_payload = {'grant_type': 'client_credentials'}

    token_response = requests.post(auth_server_url,
    data=token_req_payload, verify=False, allow_redirects=False,
    auth=(client_id, client_secret))
			 
    if token_response.status_code !=200:
        print("Failed to obtain token from the OAuth 2.0 server")
        sys.exit(1)
        
    print("Successfuly obtained a new token!")
    tokens = json.loads(token_response.text)
    print(tokens['access_token'])
    return tokens['access_token']

# Obtain a token before calling the HOBOlink API for the first time
token = get_new_token()


while True:
#  Use the API with the newly acquired token
    api_call_headers = {'Authorization': 'Bearer ' + token} # HTTP Authentication required for HOBOlink
    api_call_response = requests.get(hobolink_api_url, headers=api_call_headers, verify=False) # requests a representation of the specified resource
    # Convert data to dict
    data = json.loads(api_call_response.text)
 
    # Convert dict to string
    data = json.dumps(data)
    # will output the desired data specifed in the hobolink_api_url data ranges
    with open(daily_file, "a") as file:
        file.write(data)

# Create a new token incase it expires
# Token from Hobolink will expire after 10 minutes, or if another one is expired
    if	api_call_response.status_code == 401: #http 401 code will appear if token is expired
        token = get_new_token()
    else:
        print(data)
        print(type(data))

    break
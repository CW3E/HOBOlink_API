#!/usr/bin/python
# CW3E Field Team 
# Adolfo Lopez Miranda
# June 08, 2023

# import modules
import sys
import requests
import json
import logging
import time
# import datetime

# record warnings during process
logging.captureWarnings(True)

user_id = '26954' # user ID found on HOBOlink
logger_id = '21667527' # SN from logger
day = '2023-06-08' # previous day
# HOBOlink url to get data from file endpoints
hobolink_api_url = "https://webservice.hobolink.com/ws/data/file/JSON/user/26954?loggers=21667527&start_date_time=2023-06-08+00%3A00%3A00&end_date_time=2023-06-08+01%3A00%3A00"

# function to obtain a new OAuth 2.0 token from the authentication server
def get_new_token():
    # url provided by HOBOlink Web Services V3 Developer's Guide
    auth_server_url = "https://webservice.hobolink.com/ws/auth/token"
    # credentials provided by Onset Tech support
    client_id = 'CW3E_WS'
    client_secret = '4e76ee99629bc0708c68483fb1aeac3f9ee87713'

    token_req_payload = {'grant_type': 'client_credentials'}

    token_response = requests.post(auth_server_url,
    data=token_req_payload, verify=False, allow_redirects=False,
    auth=(client_id, client_secret))
			 
    if token_response.status_code !=200:
        print("Failed to obtain token from the OAuth 2.0 server", file=sys.stderr)
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
    # will output the desired data specifed in the hobolink_api_url data ranges
    with open("resp_text.txt", "w", encoding="utf-8") as file:
        file.write(api_call_response.text)

# Create a new token incase it expires
# Token from Hobolink will expire after 10 minutes, or if another one is expired
    if	api_call_response.status_code == 401: #http 401 code will appear if token is expired
        token = get_new_token()
    else:
        print(api_call_response.text)
        print(api_call_response.encoding)

    time.sleep(30)

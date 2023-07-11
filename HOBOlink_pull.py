#!/usr/bin/python
# CW3E Field Team 
# Adolfo Lopez Miranda
# June 08, 2023

# import modules
import requests
from datetime import datetime
from HOBOlink_parse import get_new_token, parse_data

# Input your info for user ID, SN for logger, and client credentials
# HOBOlink account and device info
user_id = input("Enter user ID found on HOBOlink:") # user ID found on HOBOlink
logger_id = input("Enter SN from logger:") # SN from logger
site_id = input("Enter site ID:") #nickname given to device on HOBOlink

#HOBOlink authentication server
# url provided by HOBOlink Web Services V3 Developer's Guide
auth_server_url = "https://webservice.hobolink.com/ws/auth/token"

# credentials provided by Onset Tech support
client_id = input("Enter client ID provoded by Onset:")
client_secret = input("Enter client secret provided by Onset:")

# file name
daily_file_csv = site_id + ".csv"

# provide date timestamp for desired data pull
print("Enter date timestamp in the following format:")
print("YYYY-mm-dd HH:MM:SS")
start_dt = input("Enter start date timestamp (UTC):")
end_dt = input("Enter end date timestamp (UTC):")

date_format = '%Y-%m-%d %H:%M:%S'

start_dt = datetime.strptime(start_dt, date_format)
start_min =  start_dt.strftime("%M")
start_sec = start_dt.strftime("%S")

end_dt = datetime.strptime(end_dt, date_format)
end_min =  end_dt.strftime("%M")
end_sec = end_dt.strftime("%S")

start_time = start_dt.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + start_min + "%3A" + start_sec  # start of the hour
end_time = end_dt.strftime("&end_date_time=%Y-%m-%d+%H") + "%3A" + end_min + "%3A" + end_sec # end of the hour
# Difference in time
time_diff = end_dt.replace(microsecond=0, second=0, minute=55) - start_dt

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
        print("Successfully connected to HOBOlink!")
        data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation

    break

# check size of data packet
if len(data["observation_list"]) == t :
    print("New data is available, and is complete.")
    parse_data(data, daily_file_csv) # pull and store data
elif len(data["observation_list"]) == 0 :
    print("No data new data since the last recorded timestamp.")
elif 0 < len(data["observation_list"]) < t :
    print("There is new data, but may be incomplete.")
    parse_data(data, daily_file_csv) # pull and store data
elif len(data["observation_list"]) > t :
    print("The data packet is greater than what is expected and duplicates may exist for some timestamps.")
    parse_data(data, daily_file_csv) # pull and store data
    
# End of script
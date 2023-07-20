#!/usr/bin/python
# CW3E Field Team 
# Adolfo Lopez Miranda
# June 08, 2023

# import modules
import requests, logging, os
from datetime import datetime, timedelta, timezone
from HOBOlink_parse import get_new_token, csv_timestamp, current_timestamp, parse_data

# Input your info for user ID, SN for logger, and client credentials
# HOBOlink account and device info

#HOBOlink authentication server
# url provided by HOBOlink Web Services V3 Developer's Guide
auth_server_url = "https://webservice.hobolink.com/ws/auth/token"

# credentials provided by Onset Tech support

# create log file to capture warnings
logging.basicConfig(filename=site_id + '.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  datefmt='%Y-%m-%d %H:%M:%S%z')
logging.captureWarnings(True)

# file name
daily_file_csv = site_id + ".csv"

# check if file exists
file_exists = os.path.isfile(daily_file_csv)
if file_exists == True:
    start_time, start_dt = csv_timestamp(daily_file_csv) # last entry in file
    end_time, current_dt = current_timestamp() # current time (previous hour)
    # Expected values between start time and end time 
    t1 = (current_dt - start_dt).total_seconds() / 300 + 1
elif file_exists == False:
    # Expected values between start time and end time
    end_time, current_dt = current_timestamp() # current time (previous hour)
    start_dt = current_dt.replace(microsecond=0, second=0, minute=0)
    # format start time for url 
    start_time = start_dt.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + start_dt.strftime("%M") + "%3A" + start_dt.strftime("%S") # start of the hour
    # Expected values between start time and end time
    t1 = (current_dt - start_dt).total_seconds() / 300 + 1

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
    if api_call_response.status_code == 200: 
        # Convert data to dict
        data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
        if len(data["observation_list"]) > 0 :
            check_data = parse_data(data, daily_file_csv)
            t2 = (check_data.End_Timestamp - check_data.Start_Timestamp).total_seconds() / 300 + 1
            if t1 == t2:
                logging.info("Data is complete.")
            elif t1 > t2:
                logging.warning("Data may be incomplete.\n" + 
                                "Data recorded for the following timestamp ranges: " + 
                                str(check_data.Start_Timestamp) + " - " + str(check_data.End_Timestamp) + "\n" +
                                "Expected data for the following timestamp ranges: " + 
                                str(start_dt) + " - " + str(current_dt)
                                )
            elif t1 < t2:
                logging.warning("The data packet is greater than what is expected and duplicates may exist for some timestamps.\n" +
                                "Data recorded for the following timestamp ranges: " + 
                                str(check_data.Start_Timestamp) + " - " + str(check_data.End_Timestamp)
                                )
        elif len(data["observation_list"]) == 0:
            logging.warning("No new data since the last recorded timestamp.")
        break
    elif api_call_response.status_code == 401: #http 401 code will appear if token is expired
        token = get_new_token(auth_server_url, client_id, client_secret)
    elif api_call_response.status_code == 400 or api_call_response.status_code == 500 or api_call_response.status_code == 509: 
        # Failures have occured - Record error code and error description in log file
        data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
        logging.error("error: " + str(data["error"]) + "\n" +
                      "message: "+ str(data["message"]) + "\n" +
                      "error_description: " + str(data["error_description"])
                      )
    else:
        # record status code and response in log file
        data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
        logging.error("Unexpected status code: " + str(api_call_response.status_code) + "\n"
                     "Unexpected response: ", str(data)
                     )
    break

# End of script
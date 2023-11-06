#!/usr/bin/env python
# CW3E Field Team 
# Adolfo Lopez Miranda

# import modules
import requests, logging, os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv, find_dotenv
from HOBOlink_parse import get_new_token, csv_timestamp, current_timestamp, parse_data
from email_fcns import gmail_authenticate, send_message

# load .env file - the .env file is the best place to store sensitive info such as the user ID, and token information
load_dotenv(find_dotenv())

# get the Gmail API service
service = gmail_authenticate()
email_list = os.environ.get("EMAIL_LIST")

# HOBOlink account and device info
user_id = os.environ.get("USER_ID") # user ID found on HOBOlink
logger_id = os.environ.get("LOGGER_ID").split(',') # SN from logger
site_id = os.environ.get("STREAM_SITE_ID").split(',') #nickname given to device on HOBOlink or 3 digit site ID

#HOBOlink authentication server
# url provided by HOBOlink Web Services V3 Developer's Guide
auth_server_url = "https://webservice.hobolink.com/ws/auth/token"

# credentials provided by Onset Tech support
client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")

# loop through each site and corresponding logger
for j in  range(len(site_id)):
    site = site_id[j] 
    logger = logger_id[j]
    
    # create log file to capture warnings and info when pulling data
    # One log for all sites:
    #logging.basicConfig(filename='streams.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  datefmt='%Y-%m-%d %H:%M:%S%z')
    #logging.captureWarnings(True)
    
    # create multiple log files:
    site_logger = logging.getLogger(site + 'Logger')
    site_logger.setLevel(logging.DEBUG)
    site_handler = logging.FileHandler(site + '.log', mode='a')
    site_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S%z')
    site_handler.setFormatter(site_formatter)
    site_logger.addHandler(site_handler)
    
    # file name
    file_csv = site + ".csv"

    # check if file exists
    file_exists = os.path.isfile(file_csv)
    # file exists
    if file_exists == True:
        start_time, start_dt = csv_timestamp(file_csv) # read last entry in file and use last timestamp as the start time for the data pulled
        current_dt = current_timestamp() # current time
        # Expected values between start time and end time 
        t1 = (current_dt - start_dt).total_seconds() / 300 + 1
    #file does not exist
    elif file_exists == False:
        # Expected values between start time and end time
        current_dt = current_timestamp() # current time
        start_dt = current_dt - timedelta(minutes=55) # start time
        # format start time for url 
        #start_time = start_dt.strftime("&start_date_time=%Y-%m-%d+%H") + "%3A" + start_dt.strftime("%M") + "%3A" + start_dt.strftime("%S") # start of the hour
        start_time = "&start_date_time=2023-04-19+20%3A30%3A00" # start time for first logger installed in the field under the same user
        # Expected values between start time and end time - (12 samples/hour if we have a 5min sample rate, i.e. 12 lines added to csv file)
        t1 = (current_dt - start_dt).total_seconds() / 300 + 1 #if no new data 

    """
    Note 1:
    The expected values can be pre-determined by looking at settings for each logger on HOBOlink
    In this case, the sampling rate for the sensor values is 1 sample/5mins
    We can check that we get the correct expected values with the following calculations:
    expected values from data pulled = (Difference in time [seconds]) * (1 [minute] / 60 [seconds]) * (1 [interval] / 5 [minutes]) + 1
    Note: 1 is added to account for the initial position of the first timestamp
    Adjust variable t1 based off the sampling rate in logger settings
    """
    
    # end time isn't specified, the script will pull all new data regardless of what time it is ran
    # This method can only be ran once per account as Time Frame Querying is tracked on the backend
    # Alternative method is to use end_time = "&end_date_time=YYYY-MM-DD+HH%3Amm%3ASS" in UTC format
    end_time = "&only_new_data=true"
    
    # HOBOlink url to get data from file endpoints
    hobolink_api_url = "https://webservice.hobolink.com/ws/data/file/JSON/user/" + user_id + "?loggers=" + logger + start_time + end_time

    # Obtain a token before calling the HOBOlink API for the first time
    token = get_new_token(auth_server_url, client_id, client_secret)

    while True:
        #  Use the API with the newly acquired token
        api_call_headers = {'Authorization': 'Bearer ' + token} # HTTP Authentication required for HOBOlink
        api_call_response = requests.get(hobolink_api_url, headers=api_call_headers, verify=True) # requests a representation of the specified resource
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%Z") # timestamp to use for alerts
        # Create a new token incase it expires
        # Token from Hobolink will expire after 10 minutes, or if another one is expired
        if api_call_response.status_code == 200: 
            # Convert data to dict
            data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
            if len(data["observation_list"]) > 0 :
                check_data = parse_data(data, file_csv)
                t2 = check_data.Dataframe # true amount of values that were recorded (may include duplicates)
                t1 = int((check_data.End_Timestamp - check_data.Start_Timestamp).total_seconds() / 300 + 1) # refer to Note 1 above in the script - this is the expected values
                if t1 == t2:
                    site_logger.info("Data is complete.")
                elif t1 > t2:
                    site_logger.warning("Data is incomplete.",
                                    "Data recorded for the following timestamp ranges: %s - %s\n" %(check_data.Start_Timestamp, check_data.End_Timestamp) +
                                    "Expected data for the following timestamp ranges: %s - %s" %(start_dt, current_dt))
                    send_message(service, 
                                    email_list,
                                    "HOBOlink Data Pull - WARNING for %s logger" %(site),
                                    "%s\nData is incomplete.\nData recorded for the following timestamp ranges: %s - %s\n" %(now, check_data.Start_Timestamp, check_data.End_Timestamp) +
                                    "Expected data for the following timestamp ranges: %s - %s" %(start_dt, current_dt), 
                                    []
                                    )
                elif t1 < t2:
                    site_logger.warning('The data packet is greater than what is expected and duplicates may exist for some timestamps.\n'+
                                    'Data recorded for the following timestamp ranges: %s - %s' %(check_data.Start_Timestamp, check_data.End_Timestamp))
                    send_message(service, 
                                    email_list,
                                    'HOBOlink Data Pull - WARNING for %s logger' %(site),
                                    '%s\nThe data packet is greater than what is expected and duplicates may exist for some timestamps.\n' %(now) +
                                    'Data recorded for the following timestamp ranges: %s - %s' %(check_data.Start_Timestamp, check_data.End_Timestamp), 
                                    []
                                    )
            elif len(data["observation_list"]) == 0:
                site_logger.warning('No new data since the last recorded timestamp.')
                if t1 >= 24 and t1 < 36: # send alert if this is the first occurence within a 2 hour period
                    send_message(service, 
                                    email_list,
                                    "HOBOlink Data Pull - Warning for %s logger" %(site),
                                    "%s\nNo data has been recorded within the last 2 hours.\n" %(now) +
                                    "Expected data for the following timestamp ranges: %s - %s" %(start_dt, current_dt), 
                                    []
                                    )
                elif t1 >= 288 and t1 < 300: # send alert if things have not updated by the following day (24 hours)
                    send_message(service, 
                                    email_list,
                                    "HOBOlink Data Pull - Warning for %s logger" %(site),
                                    "%s\nNo data has been recorded within the last day.\n" %(now) +
                                    "Expected data for the following timestamp ranges: %s - %s" %(start_dt, current_dt), 
                                    []
                                    )
                elif t1 >= 2016 and t1 < 2028: # send alert at the end of the week if this has not resolved
                    send_message(service, 
                                    email_list,
                                    "HOBOlink Data Pull - Warning for %s logger" %(site),
                                    "%s\nNo data has been recorded within the last week.\n" %(now) +
                                    "Expected data for the following timestamp ranges: %s - %s" %(start_dt, current_dt), 
                                    []
                                    )
                elif t1 >= 8640 and t1 < 8652: # send alert if things have not updated after 30 days
                    send_message(service,
                                    email_list,
                                    "HOBOlink Data Pull - Warning for %s logger" %(site),
                                    "%s\nNo data has been recorded within the last 30 days.\n" %(now) +
                                    "Expected data for the following timestamp ranges: %s - %s" %(start_dt, current_dt),
                                    []
                                    )                  
            break
        elif api_call_response.status_code == 401: #http 401 code will appear if token is expired
            token = get_new_token(auth_server_url, client_id, client_secret)
        elif api_call_response.status_code == 400 or api_call_response.status_code == 500 or api_call_response.status_code == 509: 
            # Failures have occured - Record error code and error description in log file
            data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
            site_logger.error('error: %s\nmessage: %s\nerror_description: %s' %(data["error"], data["message"], data["error_description"]))
            send_message(service,
                            email_list,
                            'HOBOlink Data Pull - ERROR for %s logger' %(site),
                            '%s\nerror: %s\nmessage: %s\nerror_description: %s' %(now, data["error"], data["message"], data["error_description"]),
                            []
                            )
        else:
            # record status code and response in log file
            data = api_call_response.json() # data from HOBOlink will be in JSON JavaScript Object Notation
            site_logger.error('Unexpected status code: %s\n Unexpected Response: %s' %(api_call_response.status_code, data))
            send_message(service,
                            email_list,
                            'HOBOlink Data Pull - ERROR for %s logger' %(site),
                            '%s\nUnexpected status code: %s\n Unexpected Response: %s' %(now, api_call_response.status_code, data),
                            []
                            )
        break

# End of script

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
import numpy as np
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
end_time = previous_hour_datetime.strftime("&end_date_time=%Y-%m-%d+%H") + "%3A59%3A59" # end of the hour

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
    # will output the desired data specifed in the hobolink_api_url date ranges
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

# Parse through data to save to a CSV file
def listToString(s):
 
    # initialize an empty string
    str1 = ""
 
    # traverse in the string
    for ele in s:
        str1 += ele
 
    # return string
    return str1

s = listToString(data)

# Parse string and store
substrings = []
split_str = s.split("{")
 
for u in split_str[1:]:
    split_s = u.split("}")
    if len(split_s) > 1:
        substrings.append(split_s[0])
 
substrings_str = "".join(substrings)

print(substrings_str)
print(type(substrings_str))


# water pressure
a_split = substrings_str.split('"logger_sn": "21667527", "sensor_sn": "21638273-1", "timestamp": ')
a_split = "".join(a_split)

b_split = a_split.split('"data_type_id": "1", "si_value": ')
b_split = "".join(b_split)

c_split = b_split.split('"si_unit": "kPa", "us_value": ')
c_split = "".join(c_split)

d_split = c_split.split('"us_unit": "psi", "scaled_value": 0.0, "scaled_unit": null, ')
d_split = "".join(d_split)

e_split = d_split.split('"sensor_key": 1995867, "sensor_measurement_type": "Water Pressure"')
e_split = "".join(e_split)

# diff water pressure
f_split = e_split.split('"logger_sn": "21667527", "sensor_sn": "21638273-2", "timestamp": ')
f_split = "".join(f_split)

g_split = f_split.split('"sensor_key": 1995865, "sensor_measurement_type": "Diff Pressure"')
g_split = "".join(g_split)

# water temperature
h_split = g_split.split('"logger_sn": "21667527", "sensor_sn": "21638273-3", "timestamp": ')
h_split = "".join(h_split)

i_split = h_split.split('"si_unit": "\\u00b0C", "us_value": ')
i_split = "".join(i_split)

j_split = i_split.split('"us_unit": "\\u00b0F", "scaled_value": 0.0, "scaled_unit": null, "sensor_key": 1995866, "sensor_measurement_type": "Water Temperature"')
j_split = "".join(j_split)

# water level
k_split = j_split.split('"logger_sn": "21667527", "sensor_sn": "21638273-4", "timestamp": ')
k_split = "".join(k_split)

l_split = k_split.split('"si_unit": "meters", "us_value": ')
l_split = "".join(l_split)

m_split = l_split.split('"us_unit": "feet", "scaled_value": 0.0, "scaled_unit": null, "sensor_key": 1995863, "sensor_measurement_type": "Water Level"')
m_split= "".join(m_split)

# Baraometric Pressure
n_split = m_split.split('"logger_sn": "21667527", "sensor_sn": "21667527-1", "timestamp": ')
n_split= "".join(n_split)

o_split = n_split.split('"sensor_key": 1962157, "sensor_measurement_type": "Barometric Pressure"')
o_split= "".join(o_split)

p_split = o_split.split('"logger_sn": "21667527", "sensor_sn": "21667527-S", "timestamp": ')
p_split= "".join(p_split)

q_split = p_split.split('"si_unit": "V", "us_value": ')
q_split= "".join(q_split)

r_split = q_split.split('"us_unit": "V", "scaled_value": 0.0, "scaled_unit": null, "sensor_key": 1962156, "sensor_measurement_type": "Battery"')
r_split= "".join(r_split)

# split empty spaces and uneeded characters
lst = r_split.split(", ")
#print(lst)
#print(type(lst))
#print(len(lst))

# Yield successive n-sized
# chunks from l.
def divide_chunks(l, n):
      
    # looping till length l
    for i in range(0, len(l), n): 
        yield l[i:i + n]
  
# How many elements each
# list should have
n = 18

# data rows of csv file 
res = list(divide_chunks(lst, n))
#print(res)

# Remove empty List from List
# using list comprehension
rows = [ele for ele in res if ele != ['']]
#print(rows)
#print(len(rows))

# convert list to array
arr = np.array(rows)
#print(arr)

#create new matrix that removes duplicate columns
data_arr,ind= np.unique(arr, axis=1, return_index=True)
#print(data_arr)

data_sort = data_arr[:,np.argsort(ind)]
print(data_sort)

# Use numpy.savetxt() method to save the list as a CSV file
fields="Timestamp, Water Pressure [kPa], Water Pressure [psi], Diff Pressure [kPa], Diff Pressure [psi], Water Temperature [Celsius], Water Temperature [Fahrenheit], Water Level [m], Water Level [ft], Barometric Pressure [kpa], Barometric Pressure [psi], Battery [V]"
csv_file = site_id + previous_hour_datetime.strftime("_%Y-%m-%d") + ".csv"
np.savetxt(csv_file, 
           data_sort,
           delimiter =", ",  # Set the delimiter as a comma followed by a space
           header=fields,
           fmt ='% s',
           comments="")  # Set the format of the data as string
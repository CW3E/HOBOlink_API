# HOBOlink API
HOBOlink is web-based software for configuring and monitoring RX3000 Remote Monitoring Stations and RX2100 MicroRX & MicroRX Water Level Stations. HOBOlink.py is a Python script that will pull data directly from [HOBOlink](https://hobolink.com/). The python script follows the [HOBOlink® Web Services V3 Developer’s Guide](https://www.onsetcomp.com/sites/default/files/resources-documents/25113-B%20HOBOlink%20Web%20Services%20V3%20Developer%27s%20Guide.pdf). The guide walks you through the steps to use the REST API and OAuth to grant access to users to view and retrieve data from loggers remotely. The following will go through the same steps described in the guide while and the python script.

## Access to a HOBOlink account and a Remote Monitoring Station
It is neccessary to have access to a HOBOlink account and a Remote Monitoring station that is operational.
To create an account go to [HOBOlink](https://hobolink.com/), and register your device (the serial number and device key is required to register a device). Keep a record of the device is serial number as it will be used in the python script.

Also, make note of your username and email address (can be found under User Settings > Account Info)

Your HOBOlink account will assign you a user ID. The user ID can be easily found in the url when logged into HOBOlink. For example, if you are on your devices dashboard the url will look similar to this: *https://www.hobolink.com/users/XXXXX/devices/XXXXXX*

The digits following *users/* will be your user ID. Make sure to record that user ID.
## Retrieve credentials from Onset to use API
The next step of using this API requires obtaining credentials (client_id, client_secret) from Onset. Reach out to [Technical Support] (https://www.onsetcomp.com/contact/support) either by phone, or by filling out the form and request your credentials to use the HOBOlink API.

Technical Support will ask you to confirm the following:
1. Web development experience
2. REST web services client development
3. OAuth familiarity, particularly client credentials grants  
4. Access to a HOBOlink account and a Remote Monitoring Station and/or an MX series logger
5. [HOBOlink® Web Services V3 Developer’s Guide](https://www.onsetcomp.com/sites/default/files/resources-documents/) is fully understood

Once this is confirmed you will be asked to provide your HOBOlink account username and email address. Technical Support will then go and make your credentials to use the API, and send them over to you when complete.

# HOBOlink.py
The data will be pulled with the python script: HOBOlink.py.
The script will require the info collected from HOBOlink and Onset technical support. 

There are place holders for this info in the script. Edit the script and enter the correct information for the following variables:
    
    user_id - line 15
    logger_id - line 16
    site_id - line 17
    client_id - line 24
    client_secret - line 25

# CSV File Format:

    Header: Timestamp [UTC], Water Pressure [kPa], Water Pressure [psi], Diff Pressure [kPa], Diff Pressure [psi], Water Temperature [Celsius], Water Temperature [Fahrenheit], Water Level [m], Water Level [ft], Barometric Pressure [kpa], Barometric Pressure [psi], Battery [V]
 
    Column  1: Timestamp [UTC]
	Column  2: Water Pressure [kPa]
	Column  3: Water Pressure [psi]
	Column  4: Diff Pressure [kPa]
	Column  5: Diff Pressure [psi]
	Column  6: Water Temperature [Celsius]
	Column  7: Water Temperature [Fahrenheit]
	Column  8: Water Level [m]
	Column  9: Water Level [ft]
	Column 10: Barometric Pressure [kpa]
	Column 11: Barometric Pressure [psi]
	Column 12: Battery [V]
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

# Clone repository and Get Started
Go ahead and clone the HOBOlink_API repository with git, GitHub desktop, or download ZIP file.
`Note: Scripts will need to be made executeable if repo was cloned into Skyriver.`

## Skyriver walkthrough
1. SSH into Skyriver with login credentials
2. Clone repo
	$ git clone https://github.com/CW3E/HOBOlink_API
3. Make files executable(`HOBOlink.py`,`HOBOlink_parse.py`,`email_fcns.py`)

## Create .env file to store environement variables
Create a new `.env` file in the root directory where `HOBOlink.py` is located.
Add the following lines into the `.env` file and input your user ID, the loggers SN, the site ID (used for naming log files, CSV, etc.), and credentials.

	# Input your info for user ID, SN for logger, and client credentials
	HOBOlink account and device info
	USER_ID='XXXXX'
	LOGGER_ID='XXXXXXXX' 
	STREAM_SITE_ID='XXX'

	# credentials provided by Onset Tech support
	CLIENT_ID='XXXXXX'
	CLIENT_SECRET='XXXXXXXXXXXXXXX'


The variables stored in the `.env` can now be called on with the `dotenv` and `os` python module within the `HOBOlink.py` script. `.gitignore` has been set up to avoid any potential risk of accidentally pushing it to git repo. All of your sensitive information is now safely stored.

# HOBOlink.py and HOBOlink_parse.py
`HOBOlink.py` will be the main script, and uses a number of functions from `HOBOlink_parse.py`
The following will breakdown each of the scripts further:


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

# Log File:
`HOBOlink.py` will create a log file and record important events.
The default name of this file is `streams.log` and will account for all the sites listed in the `.env` file.

# Notification system
There is an option to be able to recieve notifications via a Gmail account. The notfication option will send an email with the information when important events occured (same information is recorded in the `streams.log` file). 

## Gmail API for notifications

1. Create or login into Gmail account that you plan to use. Emails will be sent from this account.
2. [Create a Google Cloud project](https://console.cloud.google.com/projectcreate)
3. Add info for the email that will send alerts and emails that are on the email list to the `.env`
## Add email info to recieve alerts
	# Email info to recieve alerts
	EMAIL='XXXXX'
	EMAIL_LIST='XXXXXX,XXXXXX,XXXXX'

# Run script and helpful notes
The script is setup to run and create csv files for all the loggers listed in the `.env` file. Once all info has been inputted the script is ready to run. The script will pull data from a default start time (on the initial run) and will pull any new available data for that logger since that default time. After the first time the script is ran for a site, it will then grab the start time from the last timestamp recorded in the csv file for each site.

There are limitattions to pulling data for large time periods since the API is only capable of proving up to 100,000 data points at any given time. This will require the script to be ran multiple times until all available data is recorded into its csv file. Pulling large amounts of data points at any given time is not advised with the API, and can result in missing values. 
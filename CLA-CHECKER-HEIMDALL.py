# CLA-CHECKER-HEIMDALL
# Version 0.1
# Required Python libraries: requests google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pandas

from datetime import datetime
import re
import subprocess
import requests
import os
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Format current timestamp
dt = datetime.now()
ts = dt.strftime('%Y-%m-%d %H:%M:%S')

# Heimdall Matrix bot data
ACCESS_TOKEN = "MATRIX-TOKEN"
ROOM_ID = "!sPlzDlGooZRMXzAVKw:ubuntu.com"

# Matrix server URL and endpoint
MATRIX_SERVER_URL = "https://chat-server.ubuntu.com"
url = f"{MATRIX_SERVER_URL}/_matrix/client/r0/rooms/{ROOM_ID}/send/m.room.message?access_token={ACCESS_TOKEN}"

# Path to the Google project json
SERVICE_ACCOUNT_FILE = 'canonical-heimdall.json'

# The ID and sheet range for CLA Sheet
SPREADSHEET_ID = '1bkp5Ed7wJTZvxHzAPj2pmkaSxAE2rW6_-aaadYG5o4I'
RANGE_NAME = 'Revision 10'

# Column name or index to extract (Use either one, not both)
COLUMN_NAME = 'GitHub Username'  # Replace with your column name
# COLUMN_INDEX = 1  # Replace with your column index (0-based)

# Authenticate using credentials json
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)

# Connect to Google Sheets API
service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()

result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                            range=RANGE_NAME).execute()

values = result.get('values', [])

if not values:
    print('HEIMDALL: No CLA usernames found. Please check credentials.')
    MESSAGE = (ts + " - HEIMDALL: CLA sync failed. No CLA usernames found. Please check credentials. @room")
else:
    # Convert the values to a pandas DataFrame
    try:
        df = pd.DataFrame(values[1:], columns=values[0])
    except Exception as e:
        print(f"HEIMDALL: Unable to create dataframe: {e}")
        MESSAGE = (ts + " - HEIMDALL: Unable to generate user list. Please check credentials. @room")
        exit()

    # Extract the Github username column
    if COLUMN_NAME:
        if COLUMN_NAME in df.columns:
            column_data = df[COLUMN_NAME].dropna().astype(str).tolist()
        else:
            print('HEIMDALL: No CLA usernames found. Please check credentials.')
            MESSAGE = (ts + " - HEIMDALL: CLA sync failed. No CLA usernames found. Please check credentials. @room")
            exit()
    # elif COLUMN_INDEX is not None:
    #     column_data = df.iloc[:, COLUMN_INDEX].dropna().astype(str).tolist()
    else:
        print('HEIMDALL: Incorrect COLUMN_NAME or COLUMN_INDEX.')
        MESSAGE = (ts + " - HEIMDALL: CLA sync failed. Incorrect COLUMN_NAME or COLUMN_INDEX. @room")
        exit()

    # Check for valid Github username
    def is_valid_username(text):
        return re.match(r'^[\w-]+$', text) is not None

    # Filter out empty cells and non valid usernames
    try:
        column_data = [item for item in column_data if item.strip() and is_valid_username(item.strip())]
    except Exception as e:
        print(f"HEIMDALL: Unable to filter usernames: {e}")
        MESSAGE = (ts + " - HEIMDALL: CLA sync failed. Unable to filter usernames. @room")
        exit()

    # Check if there are at least 500 users in list
    if len(column_data) < 500:
        print('HEIMDALL: The sheet must contain at least 500 rows of data.')
        MESSAGE = (ts + " - HEIMDALL: CLA sync failed. Invalid user count. @room")
        exit()

    # Set user count to variable
    user_count = len(column_data)
    print(f"HEIMDALL: Total CLA signed users - {user_count}")

    # Format for json list
    try:
        formatted_data = ' , '.join(f'"{item}"' for item in column_data)
    except Exception as e:
        print(f"HEIMDALL: Unable to format user list: {e}")
        MESSAGE = (ts + " - HEIMDALL: Unable to format user list. @room")
        exit()

# Assign the formatted data to a string
formatted_string = formatted_data
print('HEIMDALL: Column data has been saved to cla_users')
# print(f'Formatted string: {formatted_string}')

# Set Heimdall bot message
MESSAGE = (ts + " - HEIMDALL: CLA sync successful! - Total CLA users: " + str(user_count))

# Execute juju config command with exported usernames
command = ("""juju config charmed-cla-checker signed-cla-json='{"signed_cla": [""" + formatted_data + """]}'""")
# For debugging juju config command
# print(command)
try:
    result = subprocess.run([command], shell=True, capture_output=True, text=True)
    print("HEIMDALL: CLA sync successfu!")
except:
    MESSAGE = (ts + " - HEIMDALL: CLA sync failed. Could not execute juju config command. @room")

# Send the Heimdall bot message
bot_msg = {
    "msgtype": "m.text",
    "body": MESSAGE
}
response = requests.post(url, json=bot_msg)

# Check the bot message response
if response.status_code == 200:
    print("HEIMDALL: Matrix message sent successfully!")
else:
    print(f"HEIMDALL: Failed to send Matrix message: {response.status_code} - {response.text}")

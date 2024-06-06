# CLA-CHECKER-HEIMDALL
# Version 0.1
# Required libraries: requests google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pandas

from datetime import datetime
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
ACCESS_TOKEN = "INSERT-MATRIX-TOKEN-HERE"
ROOM_ID = "!sPlzDlGooZRMXzAVKw:ubuntu.com"

# Matrix server URL and endpoint
MATRIX_SERVER_URL = "https://chat-server.ubuntu.com"
url = f"{MATRIX_SERVER_URL}/_matrix/client/r0/rooms/{ROOM_ID}/send/m.room.message?access_token={ACCESS_TOKEN}"

# Path to the Google project json
SERVICE_ACCOUNT_FILE = 'cla-checker-heimdall.json'

# The ID and sheet range for CLA Sheet
SPREADSHEET_ID = '1hhnr16H2uuaDvdKmHE6ZrHIVuDW-SRt9bZRYlgMAsoI'
RANGE_NAME = 'Sheet1'

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
    print('No CLA usernames found. Please check credentials.')
    # Set Heimdall bot message
    MESSAGE = (ts + " - HEIMDALL: CLA sync failed. @room")
else:
    try:
        # Convert the values to a Pandas DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])

        # Extract the specific column
        if COLUMN_NAME:
            column_data = df[COLUMN_NAME]
        # elif COLUMN_INDEX is not None:
        #     column_data = df.iloc[:, COLUMN_INDEX]
        else:
            print('Incorrect COLUMN_NAME or COLUMN_INDEX.')
            exit()

        # Format for json
        formatted_data = ' , '.join(f'"{item}"' for item in column_data)

        # Save list to a local file
        with open('cla_users.txt', 'w', encoding='utf-8') as file:
            file.write(formatted_data)

        # Assign the formatted data to a string
        formatted_string = formatted_data
        print('* Column data has been saved to cla_users.txt')
        #print(f'Formatted string: {formatted_string}')

        # Set Heimdall bot message
        MESSAGE = (ts + " - HEIMDALL: CLA sync successful.")

        # Execute juju config command with exported usernames
        command = ("""juju config charmed-cla-checker signed-cla-json='{"signed_cla": [""" + formatted_data + """]}'""")
        # For debugging juju config command
        # print(command)
        try:
            result = subprocess.run([command], shell=True, capture_output=True, text=True)
        except:
            MESSAGE = (ts + " - HEIMDALL: CLA sync failed. Could not execute juju config command. @room")
    except:
        MESSAGE = (ts + " - HEIMDALL: CLA sync failed. Check Google Sheet format or permissions. @room")

# Send the Heimdall bot message
bot_msg = {
    "msgtype": "m.text",
    "body": MESSAGE
}
response = requests.post(url, json=bot_msg)

# Check the bot message response
if response.status_code == 200:
    print("* Message sent successfully!")
else:
    print(f"Failed to send message: {response.status_code} - {response.text}")

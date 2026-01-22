import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("APS_CLIENT_ID")
CLIENT_SECRET = os.getenv("APS_CLIENT_SECRET")

AUTH_URL = "https://developer.api.autodesk.com/authentication/v2/token"

def get_access_token():
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "data:read data:write bucket:create bucket:read"
    }

    response = requests.post(AUTH_URL, headers=headers, data=data)

    if response.status_code == 200:
        print("SUCCESS: Token retrieved")
        print(response.json())
    else:
        print("ERROR:", response.status_code)
        print(response.text)

if __name__ == "__main__":
    get_access_token()

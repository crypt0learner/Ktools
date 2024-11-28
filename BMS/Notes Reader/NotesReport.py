import requests
import json
import csv
from datetime import datetime, timedelta, timezone
import pytz
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# User Authentication Details
username = os.getenv("API_USERNAME", input("Enter your API username: "))
password = os.getenv("API_PASSWORD", input("Enter your API password: "))
tenant = os.getenv("COMPANY_NAME", input("Enter your Company Name: "))
server_url = os.getenv("SERVER_URL", input("Enter your server URL Example: https://api.bms.kaseya.com : "))

# Authenticate the user and get the token
def authenticate():
    url = f"{server_url}/v2/security/authenticate"
    payload = {
        'UserName': username,
        'Password': password,
        'Tenant': tenant,
        'GrantType': 'Password'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("success", False):
            token = response_data["result"]["accessToken"]
            logging.info("Authentication successful.")
            return token
        else:
            logging.error("Authentication failed. Please check your credentials.")
            return None
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None

token = authenticate()
if not token:
    raise SystemExit("Exiting due to failed authentication.")

# Constants
BASE_URL = f"{server_url}/v2/servicedesk/tickets"
HEADERS = {
    'Content-Type': 'application/json-patch+json',
    'Authorization': f'Bearer {token}'
}

# Calculate LastActivityUpdateFrom dynamically as now - 30 days in UTC
utc = pytz.UTC
now = datetime.now(utc)
last_activity_date = now - timedelta(days=30)

# Fetch all tickets updated in the last 30 days
all_ticket_ids = []
tickets_with_details = []

def fetch_tickets():
    page_number = 1
    page_size = 100
    session = requests.Session()
    while True:
        url = f"{BASE_URL}/search"
        payload = json.dumps({
            "filter": {
                "LastActivityUpdateFrom": last_activity_date.isoformat()
            },
            "pageNumber": page_number,
            "pageSize": page_size
        })
        try:
            response = session.post(url, headers=HEADERS, data=payload)
            response.raise_for_status()
            data = response.json()

            if not data.get("success", False):
                logging.error("Failed to fetch tickets.")
                break

            for ticket in data["result"]:
                ticket_id = ticket["id"]
                all_ticket_ids.append(ticket_id)
                tickets_with_details.append({
                    "id": ticket_id,
                    "ticketNumber": ticket.get("ticketNumber", "Unknown"),
                    "assigneeName": ticket.get("assigneeName", "Unassigned"),
                    "queueName": ticket.get("queueName", "Unknown"),
                    "accountName": ticket.get("accountName", "Unknown")
                })

            if len(data["result"]) < page_size:
                break
            page_number += 1
        except requests.RequestException as e:
            logging.error(f"Request failed: {e}")
            break

fetch_tickets()

# Fetch notes for each ticket and filter them by date
filtered_notes = []

def fetch_notes():
    session = requests.Session()
    for ticket in tickets_with_details:
        ticket_id = ticket["id"]
        url = f"{BASE_URL}/{ticket_id}/notes"
        try:
            response = session.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            if not data.get("success", False):
                logging.error(f"Failed to fetch notes for ticket ID {ticket_id}")
                continue

            for note in data["result"]:
                try:
                    created_on = datetime.fromisoformat(note["createdOn"].replace("Z", "+00:00"))
                except ValueError:
                    logging.warning(f"Skipping invalid createdOn format for note in ticket {ticket_id}")
                    continue

                created_on = created_on.astimezone(utc)
                if created_on >= last_activity_date:
                    filtered_notes.append({
                        "ticket_id": ticket_id,
                        "ticketNumber": ticket["ticketNumber"],
                        "details": note["details"],
                        "assigneeName": ticket["assigneeName"],
                        "queueName": ticket["queueName"],
                        "accountName": ticket["accountName"],
                        "createdByName": note["createdByName"],
                        "createdOn": note["createdOn"]
                    })
        except requests.RequestException as e:
            logging.error(f"Request failed: {e}")

fetch_notes()

# Export the data to a CSV file
csv_file = "filtered_notes.csv"
csv_headers = ["ticket_id", "details", "ticketNumber", "assigneeName", "queueName", "accountName", "createdByName", "createdOn"]

with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=csv_headers)
    writer.writeheader()
    writer.writerows(filtered_notes)

logging.info(f"Filtered notes exported to {csv_file}")

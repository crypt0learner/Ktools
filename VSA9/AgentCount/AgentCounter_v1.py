import requests
import json


# Get the bearer token and server URL from the user
bearer_token = input("Please enter the API token: ")
server_url = input("Please enter the server URL (Example: https://saas44.kaseya.net)")

base_url = ":443/api/v1.0/assetmgmt/assets"

payload = {}
headers = {
  'Authorization': f'Bearer {bearer_token}'
}



count_computer_agents = 0
skip = 0
top = 100

# Initialize an empty list to store all results
all_results = []

## Loop through all the records - Pagination##

while True:
    params = {'$skip': skip, '$top': top}
    full_url = server_url + base_url + f"?$skip={skip}&$top={top}"
    print("Request URL:", full_url)
    response = requests.get(full_url, headers=headers)
    data = response.json()
    
    total_records = data.get('TotalRecords', 0)
    results = data.get('Result', [])
    
    # Add the results from this page to all_results
    all_results.extend(results)
    
    ## Iterates over a list of results counting the number of results where the field IsComputerAgent is True##
    for result in results:
        if result.get('IsComputerAgent', False):
            count_computer_agents += 1
    
    skip += top
    if skip >= total_records:
        break

# Write the data to a JSON file
with open('response.json', 'w') as f:
    json.dump(all_results, f)

## Prints the total number of computer agents##

print("Total computer agents:", count_computer_agents)

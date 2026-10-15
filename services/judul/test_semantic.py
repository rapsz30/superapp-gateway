import requests
import json
# f712fab0d58ae6492e3cdfc1933dae103ec12d5d
# pdf 649def34f8be52c8b66281af98ae884c09aef38b
paperId = "649def34f8be52c8b66281af98ae884c09aef38b"
# Define the API endpoint URL
url = f"http://api.semanticscholar.org/graph/v1/paper/{paperId}"

# Define the query parameters
query_params = {"fields": "title,year,abstract,citationCount"}

# Directly define the API key (Reminder: Securely handle API keys in production environments)
# Replace with the actual API key
api_key = "69gKQxzKgg9lBYQMr8rbX65mdMkguSut4C8WTAgK"

# Define headers with API key
headers = {"x-api-key": api_key}

# Send the API request
response = requests.get(url, params=query_params, headers=headers)

# Check response status
if response.status_code == 200:
    response_data = response.json()
    # Process and print the response data as needed
    print(response_data)
    # print(json.dumps(response, indent=4))
else:
    print(
        f"Request failed with status code {response.status_code}: {response.text}")

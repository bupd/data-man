import requests
import time
import random
import json

def get_spreadsheet_data(web_app_url):
    """Fetches data from a Google Apps Script web app (GET request)."""
    try:
        response = requests.get(web_app_url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except json.JSONDecodeError as e:
        return None


def post_data_to_spreadsheet(web_app_url, data):
    """Posts data to a Google Apps Script web app (POST request)."""

    try:
        headers = {'Content-Type': 'application/json'}  # Important: Set the content type
        json_data = json.dumps(data)  # Convert data to JSON string
        response = requests.post(web_app_url, data=json_data, headers=headers)
        response.raise_for_status()
        response_data = response.json()  # parse the JSON response
        return response_data
    except requests.exceptions.RequestException as e:
        print(f"Error posting data: {e}")
        return None
    except json.JSONDecodeError as e:
        return None


# # Example usage (replace with your actual URL):
# web_app_url = "https://script.google.com/macros/s/AKfycbwyw9XXxT1Zh4YHy5w0Z6cS1i9Tpbt_yRXhLG_qObIzRMqhf9zFiR5Xq76Eg2v78x46iw/exec"  # The /exec URL of your deployed web app
#
# # 1. Get data (GET request):
# spreadsheet_data = get_spreadsheet_data(web_app_url)

# if spreadsheet_data:
#     print("Data retrieved successfully:")
#     print(json.dumps(spreadsheet_data, indent=2))  # Print with indentation for readability
#
#     # 2. Example of how to modify the data and post it back (POST request):
#     if isinstance(spreadsheet_data, list) and len(spreadsheet_data) > 0:  # Check if it is an array and has data
#         # Example modification (add a new field to each row and set rowIndex):
#         for idx, row in enumerate(spreadsheet_data):
#             row['Views'] = random.randint(1, 1000)  # Modify the row data as needed
#             row['Timestamp'] = time.time()  # Modify the row data as needed
#             time.sleep(1) # wait for every second to update the timestamp
            # row['rowIndex'] = idx + 2  # Add the row index (1-based index)
#
#         # Post the modified data back:
#         post_response = post_data_to_spreadsheet(web_app_url, spreadsheet_data)
#
#         if post_response:
#             print("\nData posted successfully:")
#             print(json.dumps(post_response, indent=2))
#         else:
#             print("\nData post failed")
#     else:
#         print("\nNo data or data is not in the expected format")
# else:
#     print("Failed to retrieve data.")

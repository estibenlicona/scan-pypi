import requests

# Test API endpoint
url = "http://127.0.0.1:8000/scan/"
data = {"libraries": ["requests"]}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

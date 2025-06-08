import requests
import time

url = "http://localhost:8505/api/analyze/summary"
headers = {
    "accept": "application/json",
    "Authorization": "Basic ZGVtbzpkZW1vQDQxNTA=",
    "Content-Type": "application/x-www-form-urlencoded"
}
data = {
    "ticker": "AMZN"
}

start_time = time.time()
response = requests.post(url, headers=headers, data=data)
end_time = time.time()

print("Status Code:", response.status_code)
print("Response Time Summary(seconds):", round(end_time - start_time, 3))
#print("Response JSON:", response.json())
#---------------------------------

url = "http://localhost:8505/api/analyze/topics"
headers = {
    "accept": "application/json",
    "Authorization": "Basic ZGVtbzpkZW1vQDQxNTA=",
    "Content-Type": "application/x-www-form-urlencoded"
}
data = {
    "ticker": "AMZN"
}

start_time = time.time()
response = requests.post(url, headers=headers, data=data)
end_time = time.time()

print("Status Code:", response.status_code)
print("Response Time Topics(seconds):", round(end_time - start_time, 3))
#print("Response JSON:", response.json())
#---------------------------------
url = "http://localhost:8505/api/analyze/sentiment"
headers = {
    "accept": "application/json",
    "Authorization": "Basic ZGVtbzpkZW1vQDQxNTA=",
    "Content-Type": "application/x-www-form-urlencoded"
}
data = {
    "ticker": "AMZN"
}

start_time = time.time()
response = requests.post(url, headers=headers, data=data)
end_time = time.time()

print("Status Code:", response.status_code)
print("Response Time Sentiment(seconds):", round(end_time - start_time, 3))
#print("Response JSON:", response.json())
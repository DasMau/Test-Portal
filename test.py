import json
import requests
from datetime import date
import pandas as pd



with open("plex_api.json") as data:
    data_lines = data.read()
with open("plex_api2.json") as data:
    data_lines2 = data.read()


data_json = json.loads(data_lines)
data_list = data_json["tables"]

data_dict = data_json["tables"][0]

print((data_json["tables"][0]))
print(type(data_json["tables"]))
print(data_list[0])
for key in data_json.values():
    print (key)
print(data_dict["rows"])

data_json2 = json.loads(data_lines2)
data_dict2 = data_json2["tables"][0]

print(data_dict2["rows"])


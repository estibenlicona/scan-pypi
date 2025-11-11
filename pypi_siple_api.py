from pypi_json import PyPIJSON
from pprint import pprint

with PyPIJSON() as client:
    requests_metadata = client.get_metadata("clyent")
##pkg = requests_metadata.urls[0]
pprint(requests_metadata.urls[0])

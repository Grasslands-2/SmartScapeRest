#!/usr/bin/env python3
"""
Methods to ensure rasters are download to geoserver cache before downloading from geoserver
-------------------------------------------------
Author: Matthew Bayles
Date Created: 2025-08-28
Description:
    -
"""
from urllib.parse import urlencode
import requests
from typing import List
import logging
logger = logging.getLogger(__name__)

def check_cache(region: str, file_type: str, file_list: List[str]):
    """
    Check geoserver cache for fill hits

    Parameters
    ----------
    region : str
        region of the request files
    file_type : str
        The input type, either ``"modelInputs"`` or ``"modelOutputs"``.
    file_list : list of str
        _list file names to check against the cache
    Examples
    --------

    >>> check_cache("cloverBelt", "modelInputs", ["cloverBeltWI_DEM_30m.tif"])

    """

    get_package = []
    regions = {
        "southWestWI": "ridgeValley",
        "cloverBelt": "cloverBelt",
        "northeastWI": "northeast",
        "uplandsWI": "uplands",
        "redCedarWI": "redCedar",
        "pineRiverMN": "pineRiverMN",
        "eastCentralWI": "eastCentralWI",
        "southEastWI": "southEastWI"
    }
    # inconsitent naming
    region = regions[region]
    # get rid of any duplicate files
    file_list = list(set(file_list))
    geo_type = "tif"
    for file in file_list:
        if file_type == "modelOutputs":
            if region == "eastCentralWI" or region == "northeastWI" or region == "southEastWI":
                geo_type = "tiff"
        get_package.append(f"{region}/{file_type}/{file}.{geo_type}")
    # http://localhost:5000/fetch?keys=cloverBelt/modelInputs/cloverBeltWI_DEM_30m.tif&keys=cloverBelt/modelInputs/cloverBeltWI_awc_30m.tif
    # Create query parameters
    query = urlencode([("keys", path) for path in get_package])

    # Full GET request URL
    url = f"http://localhost:5000/fetch?{query}"
    # logging.info(f"cache url {url}")
    response = requests.get("http://localhost:5000/fetch", params=query)
    logging.info(f"{response.status_code}")
    # logging.info(f"{response.text['status']}")

if __name__ == "__main__":
    region = 'cloverBelt'
    file_type = "modelInputs"
    file_list = ["cloverBeltWI_DEM_30m", "cloverBeltWI_awc_30m"]
    check_cache(region, file_type, file_list)

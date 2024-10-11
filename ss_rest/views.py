"""
Main file for controlling SmartScape views
Author: Matthew Bayles
Created: November 2021
Python Version: 3.9.2
"""
import uuid
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ss_rest.raster_data_smartscape import RasterDataSmartScape
from ss_rest.smart_scape import SmartScape
# from grazescape.db_connect import *
import traceback
from django.http import FileResponse
from django.views.decorators.csrf import csrf_protect
import time
import requests
import json as js
import threading
import shutil
from osgeo import gdal
import math
import ss_rest.helper_base
import numpy as np
from osgeo import gdalconst as gc
import os
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


@api_view(['POST', 'GET'])  # Adjust HTTP methods as needed
def api(request):
    # Return the processed data as JSON
    response = JsonResponse({'message': 'CORS is working!'})
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    return response



def offline(request):
    return render(request, 'offline.html')


def createNewDownloadThread(link, filelocation):
    download_thread = threading.Thread(target=download, args=(link, filelocation))
    download_thread.start()
    return download_thread


def download(link, filelocation):
    r = requests.get(link, stream=True)
    with open(filelocation, 'wb') as f:
        for chunk in r.iter_content(1024):
            if chunk:
                f.write(chunk)

@csrf_exempt
@api_view(['POST', 'GET', 'OPTIONS'])
def get_selection_raster(request):
    """
    Download input rasters in background
    Parameters
    ----------
    request : request object
        The request object from the client

    Returns
    -------
    JsonResponse
        Contains output parameters needed for client

    """
    print(request)
    data = {}
    field_coors_formatted = []
    error = ""
    start = time.time()
    print("downloading rasters in background")
    request_json = js.loads(request.body)
    folder_id = request_json["folderId"]
    extents = request_json["geometry"]["extent"]
    field_coors = request_json["geometry"]["field_coors"]
    region = request_json["region"]
    for val in field_coors:
        field_coors_formatted.append(val[0][0])
    print("downloading base raster")

    try:
        geo_data = RasterDataSmartScape(
            extents, field_coors_formatted,
            folder_id,
            region)
        print("loading layers")
        geo_data.load_layers()
        print("create clip #######################################")
        geo_data.create_clip()
        print("Clip raster ", time.time() - start)

        geo_data.clip_rasters(True)
        print("Downloading ", time.time() - start)
        print("Layer loaded ", time.time() - start)
        data = {
            "get_data": "success",
            "folder_id": folder_id
        }

    except KeyError as e:
        error = str(e)
    except ValueError as e:
        error = str(e)
    except TypeError as e:
        print("type error")
        error = str(e)
    except FileNotFoundError as e:
        error = str(e)
    except Exception as e:
        error = str(e)
        print(type(e).__name__)
        print(traceback.format_exc())
        traceback.print_exc()
    print(error)
    return JsonResponse(data, safe=False)

@api_view(['POST', 'GET'])
def download_base_rasters(request):
    request_json = js.loads(request.body)
    geo_folder = request_json["folderId"]
    ss_rest.helper_base.download_base_rasters_helper(request, geo_folder)
    return JsonResponse({"download": "started"}, safe=False)


# get the raster with selection criteria applied
@api_view(['POST', 'GET'])
def get_phos_fert_options(request):
    """
    Calculate p manure and avialable p fert options for each transformation and base case
    Parameters
    ----------
    request : request object
        The request object from the client

    Returns
    -------
        return_data : JsonResponse
            Contains the trans/base id and the p values
    """
    request_json = js.loads(request.body)
    # print(request_json)
    base_calc = request_json['base_calc']
    region = request_json["region"]
    print("doing base calc for phos fert options", base_calc)
    return_data = ss_rest.helper_base.get_phos_fert_options(request, base_calc, region)
    print("done getting phos fert options !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    return JsonResponse({"response": return_data}, safe=False)

@api_view(['POST', 'GET'])
def get_selection_criteria_raster(request):
    """
    Takes user transformation and creates a selection raster and png indicating which cells are selected given
    the transformation criteria.
    Parameters
    ----------
    request : request object
        The request object from the client

    Returns
    -------
    JsonResponse
        Contains output parameters needed for client
    """
    start = time.time()
    request_json = js.loads(request.body)
    folder_id = request_json["folderId"]

    trans_id = request_json["transId"]
    extents = request_json["geometry"]["extent"]
    field_coors = request_json["geometry"]["field_coors"]
    region = request_json["region"]
    field_coors_formatted = []

    for val in field_coors:
        field_coors_formatted.append(val[0][0])
    # try:
    print("intitaling rasters")
    geo_data = RasterDataSmartScape(extents, field_coors_formatted, folder_id, region)
    print("Create clipping boundary ", time.time() - start)
    # geo_data.create_clip()
    print("Clip created ", time.time() - start)
    # geo_data.clip_rasters(False)
    print("done clipping rasters", time.time() - start)

    clipped_rasters, bounds = geo_data.get_clipped_rasters()
    # geo_data.clean()
    # time.sleep(5)
    model = SmartScape(request_json, trans_id, folder_id)

    model.bounds["x"] = geo_data.bounds["x"]
    model.bounds["y"] = geo_data.bounds["y"]
    print(model.bounds)
    model.raster_inputs = clipped_rasters
    # loop here to build a response for all the model types
    return_data = []
    print("Creating png", time.time() - start)
    cell_ratio = model.get_model_png()
    print("Done ", time.time() - start)

    data = {
        "extent": extents,
        "url": os.path.join(model.file_name, "selection.png"),
        "transId": trans_id,
        "cellRatio": cell_ratio
    }
    print("return data", data)
    return_data.append(data)
    return JsonResponse(return_data, safe=False)
    # except KeyError as e:
    #     error = str(e) + " while running models for field " + f_name
    # except ValueError as e:
    #     error = str(e) + " while running models for field " + f_name
    # except TypeError as e:
    #     print("type error")
    #     error = str(e) + " while running models for field " + f_name
    # except FileNotFoundError as e:
    #     error = str(e)
    # except Exception as e:
    #     error = str(e) + " while running models for field " + f_name
    #     print(type(e).__name__)
    #     print(traceback.format_exc())
    #     traceback.print_exc()
    #     # error = "Unexpected error:", sys.exc_info()[0]
    #     # error = "Unexpected error"
    # print(error)

@api_view(['POST', 'GET'])
def get_transformed_land(request):
    """
    This function will output model results for transformed land
    Parameters
    ----------
    request : request object
        The request object from the client

    Returns
    -------
    JsonResponse
        Contains output parameters needed for client
    """
    print("running models")
    # print(request.POST)
    # print(request.body)
    request_json = js.loads(request.body)
    # create a new folder for the model outputs
    trans_id = str(uuid.uuid4())
    folder_id = request_json["folderId"]

    geo_folder = os.path.join(settings.SCRATCH_DIR, 'smartscape', 'data_files',
                              'raster_inputs', folder_id, "base")

    ss_rest.helper_base.check_base_files_loaded(geo_folder, request_json['region'])

    model = SmartScape(request_json, trans_id, folder_id)
    return_data = model.run_models()
    # return_data = []
    print("done running models")

    return JsonResponse(return_data, safe=False)

@api_view(['POST', 'GET'])
def get_image(response):
    """
    Handle requests to get png stored on server

    Parameters
    ----------
    response : request object
        The request object from the client

    Returns
    -------
    FileResponse
        The image object
    """
    file_name = response.GET.get('file_name')
    file_path = os.path.join(settings.SCRATCH_DIR, 'smartscape', 'data_files',
                             'raster_inputs', file_name)
    print(file_path)
    img = open(file_path, 'rb')
    # FileResponse takes care of closing file
    response = FileResponse(img)

    return response

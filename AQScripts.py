# Data4Good Micro-Project Script for real time air quality data
# This script will be used to write methods to then call in jupyter notebook to display the map
# @Author: Gustavo Bravo
# Date: March 20th, 2022

import requests
import pandas as pd
import json
from shapely.geometry import shape
from geopy.distance import distance
import plotly.express as px


# This function is a support two functions that will run in the main function
# This will return the station data to pass on to the Jupyternotebook
def get_stations():
    # Get the city data
    city = requests.get("https://website-api.airvisual.com/v1/routes/canada/alberta/calgary")

    # Get the stations data
    stations = requests.get \
        (f"https://website-api.airvisual.com/v1/stations/by/cityID/{city.json().get('id')}?sortBy=aqi&sortOrder=asc&units.temperature=celsius&units.distance=kilometer&units.pressure=millibar&AQI=US&language=en")

    return stations


## This method is used to get the data using request and then returns a pandas datafram
# No Formal parameters, and the return type is a pandas dataframe, as well as a dictionary
# containing all of the station names
def get_latest_data(stations: json):
    # Main dataframe that will store and the data to be returned
    data_df = pd.DataFrame()

    # Get all of the stations AQ data and add them to one dataframe
    for count, station in enumerate(stations.json()):
        # Get data for station and convert to data frame
        station_data = requests.get \
            (f"https://website-api.airvisual.com/v1/stations/{stations.json()[count].get('id')}/measurements?units.temperature=celsius&units.distance=kilometer&units.pressure=millibar&AQI=US&language=en")
        stations_tempdf = pd.json_normalize(station_data.json()['measurements']['hourly'])

        # Add a name column
        stations_tempdf.loc[:, 'station_name'] = station['name']

        # Use Forward fill to fill in missing data
        stations_tempdf['aqi'] = stations_tempdf['aqi'].fillna(method='ffill')

        # Replace the NaN that did not get filled in with 0
        stations_tempdf['aqi'] = stations_tempdf['aqi'].replace(pd.NA, 0)

        # Get the latest data only
        stations_df_row = pd.DataFrame(stations_tempdf.iloc[-1][['aqi', 'station_name']].copy())
        stations_df_column = stations_df_row.transpose()

        data_df = pd.concat([data_df, stations_df_column], ignore_index=True)

    return data_df


# This function is used to find all the coordinates for the stations from the Air-Visual API
# Return: Dictionary with all stations in the request {station name : (latitude, longitude)}
def get_station_coords(stations: json):
    # The coordinate data will be stored in here
    stations_with_coordinates = {}

    for count in range(len(stations.json())):
        # Get all the info for stations
        station_info = requests.get \
            (f"https://website-api.airvisual.com/v1/stations/{stations.json()[count]['id']}").json()

        stations_with_coordinates[station_info['name']] = \
            (station_info['coordinates']['latitude'], station_info['coordinates']['longitude'])

    return stations_with_coordinates


# This function will get the data from the json file,
# Returns: dictionary with all the sectors in the file {sector name: (latitude, longitude)}
def get_city_sectors(sectors_json: json):
    sectors_with_coordinates = {}

    for sector in sectors_json['features']:
        if sector['properties']['comm_structure'] != 'UNDEVELOPED':
            myShape = shape(sector['geometry'])
            sectors_with_coordinates[sector['properties']['name']] = (myShape.centroid.y, myShape.centroid.x)

    return sectors_with_coordinates


# This function will return the the IDW weight to then map our aqi to
# @params: A sectoctors with coordinates dictionary
# returns: A dictionary
def get_idw(sectors_with_coordinates: dict):
    for sectors, coor


import numpy as np
# Source of this algorithm
# https://www.geodose.com/2019/09/creating-idw-interpolation-from-scratch-python.html
def idw_npoint(xz,yz,n_point,p):
    r=10 #block radius iteration distance
    nf=0
    while nf<=n_point: #will stop when np reaching at least n_point
        x_block=[]
        y_block=[]
        z_block=[]
        r +=10 # add 10 unit each iteration
        xr_min=xz-r
        xr_max=xz+r
        yr_min=yz-r
        yr_max=yz+r
        for i in range(len(x)):
            # condition to test if a point is within the block
            if ((x[i]>=xr_min and x[i]<=xr_max) and (y[i]>=yr_min and y[i]<=yr_max)):
                x_block.append(x[i])
                y_block.append(y[i])
                z_block.append(z[i])
        nf=len(x_block) #calculate number of point in the block
    
    #calculate weight based on distance and p value
    w_list=[]
    for j in range(len(x_block)):
        d=distance(xz,yz,x_block[j],y_block[j])
        if d>0:
            w=1/(d**p)
            w_list.append(w)
            z0=0
        else:
            w_list.append(0) #if meet this condition, it means d<=0, weight is set to 0
    
    #check if there is 0 in weight list
    w_check=0 in w_list
    if w_check==True:
        idx=w_list.index(0) # find index for weight=0
        z_idw=z_block[idx] # set the value to the current sample value
    else:
        wt=np.transpose(w_list)
        z_idw=np.dot(z_block,wt)/sum(w_list) # idw calculation using dot product
    return z_idw


# This function will find the shortest distance between two points
# Input: two dictionaries {location: (lat, lon)}
# Return: dictionary {sector: closest station}
def map_closest_station(sectors: dict, stations: dict):
    map_sector_station = {}

    for sec_name, sec_coords in sectors.items():
        shortest_dist = float('inf')
        closest_station = ""
        for station_name, station_coords in stations.items():
            # Store distance b/t points in kilometers
            current_dist = distance(station_coords, sec_coords).km

            # Store the current distance as shortest if it's less than the current shortest
            # As well as the station name
            if current_dist < shortest_dist:
                shortest_dist = current_dist
                closest_station = station_name

        map_sector_station[sec_name] = closest_station

    return map_sector_station


# This function will create a master dataframe to throw on the plotly map
# Return: merged pandas dataframe
def merge_sector_data(sectors_mapped: dict, data_df: pd.DataFrame):
    # Convert Dictionary to dataframe
    sectors_df = pd.DataFrame.from_dict(
        sectors_mapped,
        orient='index',
        columns=['station_name'])

    # Fix indexes and column names
    sectors_df = sectors_df.reset_index().rename(columns={'index': 'name'}).copy()

    # merge and return df
    main_df = sectors_df.merge(data_df, on='station_name').sort_values('aqi')

    return main_df




def runner():
    stations = get_stations()

    data_df = get_latest_data(stations=stations)

    stations_with_coords = get_station_coords(stations=stations)

    calgary_sectors = json.load(open("Community District Boundaries.geojson"))

    sectors_with_coords = get_city_sectors(sectors_json=calgary_sectors)

    sectors_mapped = map_closest_station(
        sectors=sectors_with_coords,
        stations=stations_with_coords
    )

    main_df = merge_sector_data(
        sectors_mapped=sectors_mapped,
        data_df=data_df)

    fig = px.choropleth_mapbox(main_df,
                               locations='name',
                               featureidkey='properties.name',
                               geojson=calgary_sectors,
                               color='aqi',
                               mapbox_style='carto-positron',
                               center={'lat': 51.033639, 'lon': -114.059655},
                               zoom=8.2,
                               opacity=0.7,
                               title="Calgary's Air Quality By Sector Using Air Quality Index (AQI)")
    fig.update_geos(fitbounds='locations')
    fig.write_json("input/aiq_map.json")


if __name__ == '__main__':
    runner()


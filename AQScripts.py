# Data4Good Micro-Project Script for real time air quality data
# This script will be used to write methods to wrangle the aqi 
# data from the Air-Visual AQI, to then export a json map to the html
# @Author: Gustavo Bravo
# Date: March 20th, 2022

import requests
import pandas as pd
import json
from shapely.geometry import shape
import numpy as np
from scipy.interpolate import RBFInterpolator
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.express as px


def runner():
    stations = get_stations().json()

    data_df = get_latest_data(stations=stations)

    stations_with_coords = get_station_coords(stations=stations)

    # Map the coordinates of each station into the dataframe
    data_df['coords'] = data_df['station_name'].map(stations_with_coords)

    calgary_sectors = json.load(open("Community District Boundaries.geojson"))

    sectors_with_coords = get_city_sectors(sectors=calgary_sectors)

    sectors_df = sector_to_df(
        sectors_with_coords=sectors_with_coords,
    )

    interpolated_dict = get_aqi_with_RBF(
        aqi_df=data_df, 
        sectors_with_coordinates=sectors_with_coords
    )

    sectors_df['aqi'] = sectors_df['name'].map(interpolated_dict)

    main_df = sectors_df.copy()

    # Get the current data and time to show when the graph refreshed
    # Uses edmonton because calgary is not within the key
    current_dt = datetime.now(tz=ZoneInfo("America/Edmonton"))\
                    .strftime("%m/%d/%Y %I:%M %p")

    fig = px.choropleth_mapbox(main_df,
                    locations='name',
                    featureidkey='properties.name',
                    geojson=calgary_sectors,
                    color='aqi',
                    color_continuous_scale=[
                        (0, "green"), 
                        (0.1667, "yellow"), 
                        (0.33, "orange"), 
                        (0.5, "red"), 
                        (0.667, "purple"), 
                        (1, "maroon")
                    ],
                    range_color=[0, 150],
                    mapbox_style='carto-darkmatter',
                    center={'lat':51.033639, 'lon':-114.059655},
                    zoom=8.8,
                    opacity=0.5,
                    title="Calgary's Real-Time Air Quality " +\
                        "By Sector Using Air Quality Index (AQI)" +\
                        f"<br><sup>Last Refresh: {current_dt} Calgary Time</sup>",
                    width=1200,
                    height=550,
                    template='plotly_dark',
                    labels=dict(aqi='AQI'),
                    hover_data=['aqi']
        )

    fig.update_layout(
        margin=dict(l=20, r=20, t=80, b=20),
        coloraxis_colorbar=dict(
            tickvals=[0, 25, 50, 75, 100, 125, 150],
            ticktext=[
                '0',
                '0 - 50: Good',
                '50',
                '51 - 100: Moderate',
                '100',
                '101 - 150: Unhealthy for Sentive Individuals',
                '150 or More: Unhealthy for All'
            ]
        )
    )

    fig.update_traces(
        hovertemplate="%{properties.name}: <br>Air Quality Index: %{text}",
        text=main_df['aqi']
    )

    # fig.show()

    fig.write_json("input/aiqmap.json")
    fig.write_image("input/aiqmap.png")


# This is a support function used to get the json 
# file from the API that contains the properties of 
# the aqi measuring stations for the city of calgary
# Returns: stations properties in a nested json
def get_stations():
    # Get the city data
    city = requests.get("https://website-api.airvisual.com/v1/routes/canada/alberta/calgary")

    # Get the stations data
    stations = requests.get \
        (f"https://website-api.airvisual.com/v1/stations/by/cityID/{city.json().get('id')}?sortBy=aqi&sortOrder=asc&units.temperature=celsius&units.distance=kilometer&units.pressure=millibar&AQI=US&language=en")

    return stations


# This function requests the data per aqi measuring station
# which then stores it in a dataframe
# @param: station data in a json format from get_stations()
# Returns: pandas dataframe containing the station data
# containing all of the station names
def get_latest_data(stations: json):
    # Main dataframe that will store and the data to be returned
    data_df = pd.DataFrame()

    # Get all of the stations AQ data and add them to one dataframe
    for count, station in enumerate(stations):
        # Get hourly data for station and convert to data frame
        station_data = requests.get \
            (f"https://website-api.airvisual.com/v1/stations/{stations[count].get('id')}/measurements?units.temperature=celsius&units.distance=kilometer&units.pressure=millibar&AQI=US&language=en")
        stations_tempdf = pd.json_normalize(station_data.json()['measurements']['hourly'])

        if "aqi" in stations_tempdf:
            # Add a name column
            stations_tempdf.loc[:, 'station_name'] = station['name']

            # Use Forward fill to fill in missing data
            stations_tempdf['aqi'] = stations_tempdf['aqi'].fillna(method='ffill')

            # Replace the NaN that did not get filled in with 0
            stations_tempdf['aqi'] = stations_tempdf['aqi'].replace(pd.NA, 0)

            # Get the latest data only
            stations_df_row = pd.DataFrame(stations_tempdf.iloc[-1][['ts', 'aqi', 'station_name']].copy())
            stations_df_column = stations_df_row.transpose()

            # Concat to our dataframe that contains all of the stations
            data_df = pd.concat([data_df, stations_df_column], ignore_index=True)

    return data_df


# This function is used to find all the coordinates 
# for the stations from the Air-Visual API
# @params: station data in a list from get_stations()
# Returns: Dictionary with all stations in the request 
#   format {station name : (latitude, longitude)}
def get_station_coords(stations: list):
    # The coordinate data will be stored in here
    stations_with_coordinates = {}

    for count in range(len(stations)):
        # Get all the info for stations
        station_info = requests.get \
            (f"https://website-api.airvisual.com/v1/stations/{stations[count]['id']}").json()

        stations_with_coordinates[station_info['name']] = \
            (station_info['coordinates']['latitude'], station_info['coordinates']['longitude'])

    return stations_with_coordinates


# This function retrieves the nested data from the 
# list only for the developed sections of the city,
# Returns: dictionary with all the sectors in the file 
#   format {sector name: (latitude, longitude)}
def get_city_sectors(sectors: list):
    sectors_with_coordinates = {}

    for sector in sectors['features']:
        if sector['properties']['comm_structure'] != 'UNDEVELOPED':
            myShape = shape(sector['geometry'])
            sectors_with_coordinates[sector['properties']['name']] = (myShape.centroid.y, myShape.centroid.x)

    return sectors_with_coordinates


# This function will create a df based on the 
# dictionary passed, fixes their indexes, and 
# changes the column names to improve readability
# Return: pandas dataframe
def sector_to_df(sectors_with_coords: dict):
    # Convert Dictionary to dataframe
    sectors_df = pd.DataFrame.from_dict(
        sectors_with_coords,
        orient='index'
    )

    # Fix indexes and column names
    sectors_df = sectors_df.reset_index().rename(columns={
        'index': 'name',
        '0': 'y_coord',
        '1': 'x_coord' 
    })
    
    return sectors_df


# This function converts the dataframe containing the data for 
# each sector into a 2D List to be used by the SciPy method to 
# estimate the aqi of a sector using a linear, radial based function
# @param: pd.DataFrame containing aqi for all stations
# @param: dictionary containing coordinate data for all stations
#   format {sector_name: (lat, lon)}
# Returns: dictionary containing interpolated data
#   format {sectors_name: interpolated aqi rounded to 2 decimal places}
def get_aqi_with_RBF(aqi_df: pd.DataFrame, sectors_with_coordinates: dict):
    sector_aqi_interpolated_dict = {}
    
    # Stations x, y coordinate
    y = [np.array(tup) for idx, tup in aqi_df['coords'].items()]
    z = aqi_df['aqi'].to_numpy() # aqi value

    # Create the interpolation function
    interp = RBFInterpolator(y, z, kernel='linear')
    
    # Call the interpolation function for all sector coordinate values
    coords_np = [np.array(coords) for k, coords in sectors_with_coordinates.items()]
    sector_aqi_interpolated = interp.__call__(coords_np)

    # Store in dictionary
    for count, sector in enumerate(sectors_with_coordinates.keys()):
        if sector_aqi_interpolated[count] < 0: sector_aqi_interpolated[count] = 0

        sector_aqi_interpolated_dict[sector] = round(sector_aqi_interpolated[count], 2)

    return sector_aqi_interpolated_dict


if __name__ == '__main__':
    runner()

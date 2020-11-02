from flask import Flask, request
import sqlite3
import requests
import json
import config
import docs
from datetime import datetime, timezone, timedelta


app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()


@app.route('/')
def index():
    return docs.documentation


# Returns coordinates provided and the AQI measurement according to IQAir (AirVisual)
@app.route('/aqi')
def aqi():

    args = request.args

    # Validate coordinates and round
    try:
        round(float(args['latitude']), 2)
        round(float(args['longitude']), 2)
    except:
        return "Invalid request"

    # Request from API
    r = requests.get('http://api.airvisual.com/v2/nearest_city?lat=%s&lon=%s&key=%s' %
                     (args['latitude'], args['longitude'], config.aqi_api_key))
    r = r.json()

    # Compose response
    response = {
        "location": args['latitude'] + ',' + args['longitude'],
        "aqi": r["data"]["current"]["pollution"]["aqius"]
    }

    return response


# Searches cached city/state for query (intended to save MapQuest queries)
@app.route('/cache')
def cache():
    args = request.args
    # Validate search query
    try:
        args["query"]
        # Replace spaces and commas with wildcards for SQL query
        query = args["query"].replace(" ", "%")
        query = query.replace(',', '_')
    except:
        # TODO Handle errors
        return "Invalid search query"

    c.execute(
        "SELECT * FROM cache WHERE city || ' ' || state LIKE '%"+query+"%'")

    response = {}

    # Fill out JSON for each city selected
    for city in enumerate(c.fetchall()):
        response[city[0]] = {
            "city": city[1][4],
            "state": city[1][5],
            "coords": city[1][1],
        }

    return response


# Returns 25 hour forecast of temperature, apparent temperature, wind speed, wind
#   direction, dewpoint, relative humidity, and precipitation chance
# Takes flags 'imperial' for degrees F and MPH rather than degrees C and KPH
#   and 'cardinal' to return wind direction in cardinal rather than degrees out of 360
@app.route('/hourly')
def hourly():
    args = request.args
    # Stores the coords given as arguments in the coords object, plus the 'string' concatenation
    try:
        coords = {}
        coords['latitude'] = round(float(args['latitude']), 2)
        coords['longitude'] = round(float(args['longitude']), 2)
        coords['string'] = str(coords['latitude']) + \
            ',' + str(coords['longitude'])
    except:
        # TODO Create error message here
        return "no"

    # If the supplied coordinates do not exist, create a new entry in the db
    c.execute('SELECT * FROM cache WHERE coords=?', (coords['string'],))
    if c.fetchone() == None:
        r = requests.get('https://api.weather.gov/points/%s' %
                         coords['string'])
        r = r.json()

        gridPoints = str(r["properties"]["gridX"]) + "," + \
            str(r["properties"]["gridY"])
        gridID = str(r["properties"]["gridId"])
        city = r["properties"]["relativeLocation"]["properties"]["city"]
        state = r["properties"]["relativeLocation"]["properties"]["state"]
        timeZone = r["properties"]["timeZone"]

        c.execute("INSERT INTO cache (coords, gridPoints, gridID, city, state, timeZone) VALUES (?,?,?,?,?,?)",
                  (coords["string"], gridPoints, gridID, city, state, timeZone),)
        conn.commit()

    # Use the gridpoints and gridid to process forecast information
    c.execute("SELECT gridPoints, gridID FROM cache WHERE coords=?",
              (coords["string"],))

    grid = c.fetchone()
    r = requests.get('https://api.weather.gov/gridpoints/%s/%s' %
                     (grid[1], grid[0]))
    r = r.json()

    hourData = {}

    # Signals to return imperial if requested
    imperialBool = False
    try:
        args['imperial']
        imperialBool = True
    except:
        imperialBool = False

    # Each block adds their respective property for 25 hours starting at current hour
    # Temperature C
    i = 0
    if not imperialBool:
        for value in enumerate(r["properties"]["temperature"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                hourData[i] = {
                    "temperature": round(value[1]["value"], 0)
                }
                i += 1
                if i == 25:
                    break

            if i == 25:
                break
    # Temperature F
    else:
        for value in enumerate(r["properties"]["temperature"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                hourData[i] = {
                    "temperature": (float(value[1]["value"]) * 9/5) + 32
                }
                i += 1
                if i == 25:
                    break

            if i == 25:
                break

    # Dewpoint C
    i = 0
    if not imperialBool:
        for value in enumerate(r["properties"]["dewpoint"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                hourData[i]["dewpoint"] = round(value[1]["value"], 0)
                i += 1
                if i == 25:
                    break

            if i == 25:
                break
    # Dewpoint F
    else:
        for value in enumerate(r["properties"]["dewpoint"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                hourData[i]["dewpoint"] = (float(value[1]["value"]) * 9/5) + 32
                i += 1
                if i == 25:
                    break

            if i == 25:
                break

    # Relative Humidity %
    i = 0
    for value in enumerate(r["properties"]["relativeHumidity"]["values"]):

        if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
            continue

        for _ in range(int(value[1]["validTime"][-2])):
            hourData[i]["relativeHumidity"] = value[1]["value"]
            i += 1
            if i == 25:
                break

        if i == 25:
            break

    # Apparent Temperature C
    i = 0
    if not imperialBool:
        for value in enumerate(r["properties"]["apparentTemperature"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                hourData[i]["apparentTemperature"] = round(
                    value[1]["value"], 0)
                i += 1
                if i == 25:
                    break

            if i == 25:
                break
    # Apparent Temerature F
    else:
        for value in enumerate(r["properties"]["apparentTemperature"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                hourData[i]["apparentTemperature"] = (
                    float(value[1]["value"]) * 9/5) + 32
                i += 1
                if i == 25:
                    break

            if i == 25:
                break

    # Wind Direction (cardinal)
    i = 0
    try:
        args['cardinal']
        for value in enumerate(r["properties"]["windDirection"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                degreesToCardinal = ['N', 'NE',
                                     'E', 'SE', 'S', 'SW', 'W', 'NW', 'N']
                hourData[i]["windDirection"] = degreesToCardinal[round(
                    int(value[1]["value"]) / 45)]

                i += 1
                if i == 25:
                    break

            if i == 25:
                break
    # Wind Direction (degrees out of 360)
    except:
        for value in enumerate(r["properties"]["windDirection"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                hourData[i]["windDirection"] = value[1]["value"]
                i += 1
                if i == 25:
                    break

            if i == 25:
                break

    # Wind Speed kph
    i = 0
    if not imperialBool:
        for value in enumerate(r["properties"]["windSpeed"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                hourData[i]["windSpeed"] = value[1]["value"]
                i += 1
                if i == 25:
                    break

            if i == 25:
                break
    # Wind Speed mph
    else:
        for value in enumerate(r["properties"]["windSpeed"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            for _ in range(int(value[1]["validTime"][-2])):
                hourData[i]["windSpeed"] = (
                    float(value[1]["value"]) / 1.609)
                i += 1
                if i == 25:
                    break

            if i == 25:
                break

    # Probability of Precipitation %
    i = 0
    for value in enumerate(r["properties"]["probabilityOfPrecipitation"]["values"]):

        if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
            continue

        for _ in range(int(value[1]["validTime"][-2])):
            hourData[i]["probabilityOfPrecipitation"] = value[1]["value"]
            i += 1
            if i == 25:
                break

        if i == 25:
            break

    return hourData


# Takes series of coordinate pairs separated by '+'
# Returns current temperature for each pair in order composed
# Can take 'imperial' flag to convert to degrees F
@app.route('/locations')
def locations():

    args = request.args

    try:
        coords = args['coords'].split()
    except:
        # TODO error handling
        return "Invalid Request"

    response = {}

    for coord in coords:
        # Validate provided coordinate and round values
        try:
            pair = coord.split(',')
            pair[0] = round(float(pair[0]), 2)
            pair[1] = round(float(pair[1]), 2)
            pair = str(pair[0]) + ',' + str(pair[1])
        except:
            # TODO error handling
            return "Invalid Request"

        # Check if coord pair exists in database, create new record if not
        c.execute('SELECT * FROM cache WHERE coords=?', (pair,))
        if c.fetchone() == None:
            r = requests.get('https://api.weather.gov/points/%s' %
                             pair)
            r = r.json()

            gridPoints = str(r["properties"]["gridX"]) + "," + \
                str(r["properties"]["gridY"])
            gridID = str(r["properties"]["gridId"])
            city = r["properties"]["relativeLocation"]["properties"]["city"]
            state = r["properties"]["relativeLocation"]["properties"]["state"]
            timeZone = r["properties"]["timeZone"]

            c.execute("INSERT INTO cache (coords, gridPoints, gridID, city, state, timeZone) VALUES (?,?,?,?,?,?)",
                      (pair, gridPoints, gridID, city, state, timeZone),)
            conn.commit()

        # Use the gridpoints and gridid to process forecast information
        c.execute("SELECT gridPoints, gridID FROM cache WHERE coords=?",
                  (pair,))

        grid = c.fetchone()
        r = requests.get('https://api.weather.gov/gridpoints/%s/%s' %
                         (grid[1], grid[0]))
        r = r.json()

        # Fills temperature (default degrees C) for each lat/long requested
        for value in enumerate(r["properties"]["temperature"]["values"]):

            if datetime.now(timezone.utc) - datetime.fromisoformat(value[1]["validTime"][:25]) > timedelta(hours=int(value[1]["validTime"][-2])):
                continue

            response[value[0]] = value[1]["value"]
            break

    # Converts to degrees F when imperial flag is called
    try:
        args['imperial']
        for row in response:
            response[row] = (response[row] * 9/5) + 32
    except:
        return response

    return response


# Takes a search query and uses the MapQuest geocoding API to return US locations
#   that fit the parameter
@app.route('/search')
def search():
    args = request.args
    try:
        args["query"]
    except:
        # TODO Handle errors
        return "Invalid search query"

    # Request MapQuest data
    r = requests.get('http://open.mapquestapi.com/geocoding/v1/address?key=%s&location=%s' %
                     (config.geocode_api_key, args['query']))
    r = r.json()

    response = {}

    # Compose response
    for hit in enumerate(r["results"][0]["locations"]):

        # Omit non US locations
        if hit[1]["adminArea1"] != "US":
            continue

        response[hit[0]] = {
            "city": hit[1]["adminArea5"],
            "county": hit[1]["adminArea4"],
            "state": hit[1]["adminArea3"],
            "latitude": hit[1]["latLng"]["lat"],
            "longitude": hit[1]["latLng"]["lng"],
        }

    return response

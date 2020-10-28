# weather-api

"context": "Welcome to Run Weather US API",
"/aqi": [
"Returns coordinates provided and the AQI measurement according to IQAir (AirVisual)",
{
"parameters": {
"latitude": "Latitude",
"longitude": "Longitude",
},
"ex.": {
"uri": "/aqi?latitude=40&longitude=-77",
"response": {
"location": "provided latitude/longitude pair",
"aqi": "US EPA Air Quality Index (out of 500)"
}
}
}
],
"/cache": [
"Searches cache for city/state to save MapQuest queries",
{
"parameters": {
"query": "Any string containing city name and/or state code, commas not necessary but accepted"
},
"ex.": {
"uri": "/cache?query=Bloomfield, MO",
"response": {
"city": "City",
"state": "State Code",
"coords": "Latitude/Longitude pair, rounded to .01"
}
}
}
],
"/hourly": [
"Returns 25 hour forecast of temperature, apparent temperature, wind speed, wind direction, dewpoint, relative humidity, and precipitation chance",
{
"ex.": {
"uri": "/hourly?latitude=39&longitude=-110&cardinal",
"response": {
"#": "hours from current time",
},
"flags": {
"imperial": "Converts default degrees C to Fahrenheit and KPH to MPH",
"cardinal": "Converts default wind direction in 360 degrees to cardinal directions"
}
}
}
],
"/locations": [
"Takes series of coordinate pairs separated by '+'. Returns current temperature for each pair in order composed",
{
"ex.": {
"uri": "/locations?coords=37,-90.0123+32,-90+39.74,-105&imperial",
"response": {
"lat,long": "current temperature",
},
"flags": {
"imperial": "Converts default degrees C to Fahrenheit"
}
}
}
],
"/search": [
"Takes a search query and uses the MapQuest geocoding API to return US locations that fit the parameter",
{
"ex.": {
"uri": "/search?query=86001",
"response": {
"#": "ordered by distance from query",
}
}
}
],

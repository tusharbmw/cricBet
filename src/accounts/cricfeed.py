import os
import urllib.request
import json
import re
from datetime import datetime, timezone

CRIC_API_KEY = os.environ.get('CRIC_API_KEY')
CRIC_TOURNAMENT_ID = os.environ.get('CRIC_TOURNAMENT_ID')


# method with optional parameter tournament id
def get_series_info(tournament_id=None):
    if tournament_id is None:
        tournament_id = CRIC_TOURNAMENT_ID
    CRIC_SERIES_INFO_URL = "https://api.cricapi.com/v1/series_info?apikey=" + CRIC_API_KEY + "&id=" + tournament_id
    # open url and save json output into a file
    urllib.request.urlretrieve(CRIC_SERIES_INFO_URL, filename="series_info.json")

    # open url and save json output into json object
    with urllib.request.urlopen(CRIC_SERIES_INFO_URL) as url:
        data = json.loads(url.read().decode())
    #     print(data)

    # open json file into json object
    #with open('series_info.json') as json_file:
    #    data = json.load(json_file)
    out_match = []
    for match in data["data"]['matchList']:
        tmp_match = {}
        if match["teams"][0] == "Tbc" or match["teams"][1] == "Tbc":
            continue
        tmp_match["match_id"] = match["id"]
        tmp_match["Team1"] = match["teams"][0]
        tmp_match["Team2"] = match["teams"][1]
        if re.findall('(\d+)', match["name"]) is not None:
            tmp_match["Description"] = "Match " + str(re.findall('(\d+)', match["name"])[0])
        else:
            tmp_match["Description"] = match["name"]
        tmp_match["venue"] = match["venue"].split(",")[-1].strip()
        tmp_match["datetime"] = match["dateTimeGMT"]
        tmp_match["tournament"] = tournament_id
        if match["status"] == "Match not started":
            tmp_match["result"] = "TBD"
        elif "won" in match["status"] and match["matchEnded"] == True:
            if tmp_match["Team1"] in match["status"]:
                tmp_match["result"] = "team1"
            elif tmp_match["Team2"] in match["status"]:
                tmp_match["result"] = "team2"
        else:
            tmp_match["result"] = "NR"
        out_match.append(tmp_match)

    return out_match


get_series_info()

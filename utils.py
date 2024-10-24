import os
import json
import time
from datetime import datetime, timedelta

PATH = os.path.dirname(os.path.abspath(__file__)) + '/content/'#"H:/.scraper/content/"
PATH_TITLES = PATH + 'titles/'
PATH_VIDEOS = PATH + 'videos/'
PATH_SHORTS = PATH + 'shorts/'

def init():
    global CREDENTIALS
    # Making sure all directories are present
    os.makedirs(PATH_SHORTS, exist_ok=True)
    os.makedirs(PATH_TITLES, exist_ok=True)
    os.makedirs(PATH_VIDEOS, exist_ok=True)
    os.makedirs(PATH_VIDEOS + "dupes", exist_ok=True)

    credentialsFile = PATH + 'credentials.json'

    if not os.path.isfile(credentialsFile):
        with open(credentialsFile, 'w') as j:
            j.write('{"credentials": {"openai": {"organization": "yourorganization","project":"yourproject"}}}')
        raise ValueError('ERROR: credentials.json is empty')

    with open(credentialsFile, 'r') as j:
        CREDENTIALS = json.load(j)["credentials"]
    # credentials["credentials"]["openai"]["organization"]
    # credentials["credentials"]["openai"]["project"]

def isDuplicates():
    """
    Scans the /videos directory for duplicates and removes them if found.
    """
    dupe_path = PATH_VIDEOS + 'dupes/'
    
    # Checking for duplicate videos, if found move to dupes folder
    cmd = 'cbird -use ' + PATH_VIDEOS + ' -update -p.alg video -p.types v -p.eg 1 -similar -dups -select-result -first -move ' + dupe_path
    os.system(cmd)

    time.sleep(4)

    # Removing the dupes
    files = os.listdir(dupe_path)
    if not len(files) == 0: 
        print("Dupes found, removing...") 
        for f in files:
            os.remove(dupe_path + f)
        return True

    return False    

def canContinue(r):
    """
    Handles different status codes, returns true if can continue.
    """
    if r.status_code == 403:
        print("code 403")
        return True
    if r.status_code == 429:
        print("code 429, waiting for 60 seconds")
        time.sleep(60)
        return True
    return False

def hour_rounder(t):
    """
    Rounds to nearest hour by adding a timedelta hour if minute >= 30.
    """
    return (t.replace(second=0, microsecond=0, minute=0, hour=t.hour)
               +timedelta(hours=t.minute//30))
        


import requests
import os
import time
import shutil
import math
import random
import csv
import json
from datetime import datetime, timedelta
from enum import Enum
from openai import OpenAI
from youtube_uploader_selenium import YouTubeUploader

# Making sure all directories are present
os.makedirs("H:/.scraper/content/videos", exist_ok=True)
os.makedirs("H:/.scraper/content/shorts", exist_ok=True)
os.makedirs("H:/.scraper/content/titles", exist_ok=True)
os.makedirs("H:/.scraper/content/dupes", exist_ok=True)

credentialsFile = 'H:/.scraper/content/credentials.json'

if not os.path.isfile(credentialsFile):
    with open(credentialsFile, 'w') as j:
        j.write('{"credentials": {"openai": {"organization": "yourorganization","project":"yourproject"}}}')
    raise ValueError('ERROR: credentials.json is empty')

with open(credentialsFile, 'r') as j:
    credentials = json.load(j)

class CredentialsOpenAI(Enum):
    ORGANIZATION = credentials["credentials"]["openai"]["organization"]
    PROJECT = credentials["credentials"]["openai"]["project"]

def isDuplicates():
    path = 'H:/.scraper/content/videos/'
    dupePath = 'H:/.scraper/content/dupes/'
    
    # Checking for duplicate videos, if found move to dupes folder
    cmd = 'cbird -use ' + path + ' -update -p.alg video -p.types v -p.eg 1 -similar -select-result -first -move ' + dupePath
    os.system(cmd)

    # Removing the videos from the dupes folder
    files = os.listdir(dupePath)
    if not len(files) == 0: 
        print("Dupes found, removing...") 
        for f in files:
            os.remove(dupePath + f)
        return True

    return False    

# Checking if process is able to continue
def canContinue(r):
    if r.status_code == 403:
        print("code 403")
        return True
    if r.status_code == 429:
        print("code 429, waiting for 60 seconds")
        time.sleep(60)
        return True
    return False

def fetchContent(redditUrl, postCount):
    save_path = 'H:/.scraper/content/videos/'
    short_path = 'H:/.scraper/content/shorts/'
    title_path = 'H:/.scraper/content/titles/'
    vidList = os.listdir(save_path)
    shortList = os.listdir(short_path)
    vidCount = len(vidList) + 1

    r = requests.get(redditUrl)

    if r.status_code != 200:
        return r

    content = r.json()
    try:
        # Going through the top <postCount> posts
        x = -1
        while(x < postCount):
            x += 1

            # Removing oldest file if overflowing
            if (vidCount > 100):  
                oldest_file = sorted([save_path + f for f in vidList ], key=os.path.getctime)[0]
                os.remove(short_path + oldest_file)
                os.remove(save_path + oldest_file)

            # Checking for a video
            if not content["data"]["children"][x]["data"]["is_video"]:
                postCount+=1 # Adding to the number of loops if post is not a video
                continue

            duration = content["data"]["children"][x]["data"]["media"]["reddit_video"]["duration"]

            if (duration > 179.95):
                postCount+=1 # Adding to the number of loops if video is too long
                continue

            url = content["data"]["children"][x]["data"]["media"]["reddit_video"]["fallback_url"]
            videoUrl = url[:-16] # removing the fallback url modifier
            audioUrl = content["data"]["children"][x]["data"]["url"] + "/DASH_AUDIO_128.mp4"

            height = content["data"]["children"][x]["data"]["media"]["reddit_video"]["height"]
            width = content["data"]["children"][x]["data"]["media"]["reddit_video"]["width"]
            
            description = content["data"]["children"][x]["data"]["title"].encode('cp1252', errors='replace').decode('cp1252')
            title = str(random.getrandbits(128))

            print(videoUrl)
            rVideo = requests.get(videoUrl)
            if rVideo.status_code != 200:
                if canContinue(rVideo):
                    postCount+=1 # Adding to the number of loops if skipped
                    continue
                return
            
            # Saving video file to disk
            rVideoName = save_path + "temp.mp4"
            with open(rVideoName, "wb") as f:
                f.write(rVideo.content)

            if isDuplicates():
                postCount+=1 # Adding to the number of loops if duplicate
                continue

            rAudio = requests.get(audioUrl)
            if rAudio.status_code != 200:
                os.remove(rVideoName)
                if canContinue(rAudio):
                    postCount+=1 # Adding to the number of loops if skipped
                    continue
                return
            
            # Saving audio file to disk
            rAudioName = save_path + "temp.mp3"
            with open(rAudioName, "wb") as f:
                f.write(rAudio.content)

            videoOutput = save_path + title + ".mp4"
            shortOutput = short_path + title + ".mp4"
            shortTemp = short_path + "temp.mp4"

            # Merging separate audio and video tracks
            cmd = "ffmpeg -y -i " + rVideoName + " -i " + rAudioName + " -c:v copy -c:a aac " + videoOutput
            os.system(cmd)

            # Also copying to the shorts folder
            shutil.copy(videoOutput, shortOutput)

            # Changing aspect ratio to 9:16 for shorts
            if (width/height != 0.5625):
                wantedHeight = math.ceil(width/0.5625)
                if (height > wantedHeight):
                    wantedHeight = height

                os.rename(shortOutput, shortTemp)
                cmd = "ffmpeg -y -i " + shortTemp + " -vf pad=h=" + str(wantedHeight) + ":y=(oh-ih)/2 " + shortOutput
                os.system(cmd)
                os.remove(shortTemp)

            # Also saving the original title so it can be used later
            with open(save_path + "titles.csv", "a",  newline='') as f:
                csvwriter = csv.writer(f)
                field = [title, description]
                csvwriter.writerow(field)

            if os.path.exists(rAudioName):
                os.remove(rAudioName)

            if os.path.exists(rVideoName):
                os.remove(rVideoName)

            vidCount+=1

            # Extra timer to prevent spamming
            time.sleep(8)
    except:
        print("Exception! The reddit page probably ran out of posts. Continuing...")

# Using ChatGPT to revamp the titles to suit the short form better
def fetchTitles():
    path = "H:/.scraper/content/videos/"

    client = OpenAI(
        organization=CredentialsOpenAI.ORGANIZATION.value,
        project=CredentialsOpenAI.PROJECT.value
    )

    with open(path + "titles.csv", "r") as file:
        prompt = file.read()
    os.remove(path + "titles.csv")

    # Creating the API call
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
            {
                "role": "user",
                "content": "In this input there are a series of id's and descriptions separated with ','. Can you reword the descriptions to be more like tiktok titles but not over the top? Please respond in the format titles: [{id: ...,title: ...}] "
                + prompt
            }
        ],
        response_format={ "type": "json_object" }
    )

    val = completion.choices[0].message.content

    with open(path + "titles.json", "w", encoding="utf-8") as outfile:
        outfile.write(val)

# Giving each title it's own file, used when uploading.
def createTitleFiles():
    path = "H:/.scraper/content/"

    with open(path + 'videos/titles.json', 'r', encoding="utf-8") as j:
        jsonTitles = json.load(j) 
    os.remove(path + "videos/titles.json")

    for f in jsonTitles["titles"]:
        with open(path + "titles/" + f["id"] + ".json", "w", encoding="utf-8") as file:
            file.write('{"title":"' + f['title'] + '","schedule": "01/01/2001, 00:00"}')

def hour_rounder(t):
    # Rounds to nearest hour by adding a timedelta hour if minute >= 30
    return (t.replace(second=0, microsecond=0, minute=0, hour=t.hour)
               +timedelta(hours=t.minute//30))

# Uploading videos!
def uploadContent():
    path = "H:/.scraper/content/shorts/"
    list = os.listdir(path)

    currentDate = datetime.now() + timedelta(hours=1)
    currentDate = hour_rounder(currentDate)

    for video in list:
        with open('H:/.scraper/content/last_date.txt', 'r+') as f:
                lastDate = f.read()
                newDate = datetime.strptime(lastDate, '%m/%d/%Y, %H:%M') + timedelta(hours=1)

                # Can't schedule to the past, updating date to future if that is the case.
                if newDate < currentDate:
                    newDate = currentDate

                f.seek(0)
                f.write(newDate.strftime("%m/%d/%Y, %H:%M"))
                f.truncate()
        
        handleYoutube(video)
        handleTiktok()

        # Deleting the short + title files after uploading, leaving the main one for comparing dupes.
        os.remove(path + video)
        os.remove("H:/.scraper/content/titles/" + video[:-3] +'json')
        time.sleep(5)

# Uploading to Youtube and scheduling
def handleYoutube(videoName):
    try:
        with open('H:/.scraper/content/last_date.txt', 'r') as f:
            date = f.read()

        with open('H:/.scraper/content/titles/'+ videoName[:-3] +'json', 'r+', encoding="utf-8") as j:
            jsonData = json.load(j)
            jsonData['schedule'] = date
            j.seek(0)
            json.dump(jsonData, j, ensure_ascii=False)
            j.truncate()
        
        video_path = 'H:/.scraper/content/shorts/' + videoName
        metadata_path = 'H:/.scraper/content/titles/' + videoName[:-3] +'json'

        uploader = YouTubeUploader(video_path, metadata_path, profile_path=os.getenv('PROFILE_PATH'))
        was_video_uploaded, video_id = uploader.upload()
        if was_video_uploaded:
            print(video_id + " uploaded!")
    except:
        print("Error while uploading")

def handleTiktok():
    print("Tiktok no implemented")

# List of subreddits to scrape
subReddits = ["https://www.reddit.com/r/interestingasfuck/top/.json",
               "https://www.reddit.com/r/oddlysatisfying/top/.json",
                 "https://www.reddit.com/r/Damnthatsinteresting/top/.json",
                 "https://www.reddit.com/r/CrazyFuckingVideos/top/.json",
                 "https://www.reddit.com/r/Unexpected/top/.json",
                 "https://www.reddit.com/r/AnimalsBeingDerps/top/.json",
                 "https://www.reddit.com/r/Whatcouldgowrong/top/.json",
                 "https://www.reddit.com/r/CatastrophicFailure/top/.json"]
                 
for x in subReddits:
    r = fetchContent(x, 5)
    try:
        if canContinue(r):
            r = fetchContent(x, 5)
        else:
            print("Error code " + r.status_code)
    except:
        print("Continuing...")

fetchTitles()
createTitleFiles()

uploadContent()
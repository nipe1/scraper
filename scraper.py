import requests
import os
import time
import shutil
import math
import random
import csv
import json
from openai import OpenAI
import utils

def getContent(subreddits, amount):
    """
    Handle video scraping and formatting, also fetch titles.
    """
    for x in subreddits:
        r = fetchContent(x, amount)
        try:
            if utils.canContinue(r):
                r = fetchContent(x, amount)
            else:
                print("Error code " + r.status_code)
        except:
            print("Continuing...")

    fetchTitles()
    createTitleFiles()

def fetchContent(redditUrl, postCount):
    """
    Fetch 'postCount' videos from 'redditUrl' and process them.
    """
    vidList = os.listdir(utils.PATH_VIDEOS)
    vidCount = len(vidList) + 1
    vidFlair = ""
    useFlair = False

    r = requests.get(redditUrl[0])

    if len(redditUrl) > 1:
        vidFlair = redditUrl[1]
        useFlair = True

    if r.status_code != 200:
        return r

    content = r.json()["data"]["children"]
    try:
        # Going through the top <postCount> posts
        x = -1
        while(x < postCount):
            x += 1

            # Removing oldest file if overflowing
            if (vidCount > 100): 
                oldest_file = sorted([utils.PATH_VIDEOS + f for f in vidList], key=os.path.getctime)[0]
                if (oldest_file[-3:] == "mp4"):
                    os.remove(utils.PATH_VIDEOS + oldest_file)

            # Checking for a video
            if not content[x]["data"]["is_video"]:
                postCount+=1 # Adding to the number of loops if post is not a video
                continue

            if content[x]["data"]["over_18"]:
                postCount+=1 # Adding to the number of loops if post is NSFW
                continue

            if useFlair and content[x]["data"]["link_flair_richtext"]["0"]["t"] != vidFlair:
                postCount+=1 # Adding to the number of loops if flair doesn't match
                continue

            duration = content[x]["data"]["media"]["reddit_video"]["duration"]

            if (duration > 59.95):
                postCount+=1 # Adding to the number of loops if video is too long
                continue

            height = content[x]["data"]["media"]["reddit_video"]["height"]
            width = content[x]["data"]["media"]["reddit_video"]["width"]

            if (width >= 720):
                postCount+=1 # Adding to the number of loops if video isn't high enough resolution
                continue

            if (width/height > 1):
                postCount+=1 # Adding to the number of loops if video isn't suitable for vertical viewing
                continue

            url = content[x]["data"]["media"]["reddit_video"]["fallback_url"]
            videoUrl = url[:-16] # removing the fallback url modifier
            audioUrl = content[x]["data"]["url"] + "/DASH_AUDIO_128.mp4"
            
            description = content[x]["data"]["title"].encode('cp1252', errors='replace').decode('cp1252')
            title = str(random.getrandbits(128))

            print(videoUrl)
            rVideo = requests.get(videoUrl)
            if rVideo.status_code != 200:
                if utils.canContinue(rVideo):
                    postCount+=1 # Adding to the number of loops if skipped
                    continue
                return
            
            # Saving video file to disk
            rVideoName = utils.PATH_VIDEOS + "temp.mp4"
            with open(rVideoName, "wb") as f:
                f.write(rVideo.content)

            if utils.isDuplicates():
                postCount+=1 # Adding to the number of loops if duplicate
                continue

            rAudio = requests.get(audioUrl)
            if rAudio.status_code != 200:
                os.remove(rVideoName)
                if utils.canContinue(rAudio):
                    postCount+=1 # Adding to the number of loops if skipped
                    continue
                return
            
            # Saving audio file to disk
            rAudioName = utils.PATH_VIDEOS + "temp.mp3"
            with open(rAudioName, "wb") as f:
                f.write(rAudio.content)

            videoOutput = utils.PATH_VIDEOS + title + ".mp4"
            shortOutput = utils.PATH_SHORTS + title + ".mp4"
            shortTemp = utils.PATH_SHORTS + "temp.mp4"

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
            with open(utils.PATH_TITLES + "titles.csv", "a",  newline='') as f:
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

def fetchTitles():
    """
    Use ChatGPT to revamp the titles to suit the short form better.
    """
    client = OpenAI(
        organization=utils.CREDENTIALS["openai"]["organization"],
        project=utils.CREDENTIALS["openai"]["project"]
    )

    with open(utils.PATH_TITLES + "titles.csv", "r") as file:
        prompt = file.read()
    os.remove(utils.PATH_TITLES + "titles.csv")

    # Creating the API call
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
            {
                "role": "user",
                "content": "In this input there are a series of id's and descriptions separated with ','. Can you reword the descriptions to be more like tiktok titles but not over the top? Emojis can be used. Also add 3 relevant topics as lowercase hashtags to the end of each title. Please respond in the format titles: [{id: ...,title: ...}] "
                + prompt
            }
        ],
        response_format={ "type": "json_object" }
    )

    val = completion.choices[0].message.content

    with open(utils.PATH_TITLES + "titles.json", "w", encoding="utf-8") as outfile:
        outfile.write(val)

def createTitleFiles():
    """
    Give each title it's own file which is used when uploading.
    """
    with open(utils.PATH_TITLES + 'titles.json', 'r', encoding="utf-8") as j:
        jsonTitles = json.load(j) 
    os.remove(utils.PATH_TITLES + "titles.json")

    for f in jsonTitles["titles"]:
        with open(utils.PATH_TITLES + f["id"] + ".json", "w", encoding="utf-8") as file:
            file.write('{"title":"' + f['title'] + '","schedule": "01/01/2001, 00:00"}') 
                 
# for x in CONST_SUBREDDITS:
#     r = fetchContent(x, CONST_VIDEO_AMOUNT)
#     try:
#         if canContinue(r):
#             r = fetchContent(x, CONST_VIDEO_AMOUNT)
#         else:
#             print("Error code " + r.status_code)
#     except:
#         print("Continuing...")

# fetchTitles()
# createTitleFiles()

# uploadContent()
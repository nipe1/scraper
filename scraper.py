import requests
import os
import time
import shutil
import math
from videohash import VideoHash

def isDuplicate(videoPath):
    # Going through directory to check for duplicates
    path = 'H:/.scraper/content/'
    list = os.listdir(path)

    hash1 = VideoHash(path=videoPath)

    for x in list:
        if x == "temp.mp4":
            continue
        print("Comparing with " + x)
        hash2 = VideoHash(path = path + x)
        if hash2.is_similar(hash1):
            print("Dupe found! Skipping...")
            os.remove(videoPath)
            return True
        
    print("No dupe found, continuing...")
    return False

def fetchContent(redditUrl, postCount):
    save_path = 'H:/.scraper/content/'
    short_path = 'H:/.scraper/shorts/'
    vidList = os.listdir(save_path)
    shortList = os.listdir(short_path)
    vidCount = len(vidList) + 1

    r = requests.get(redditUrl)

    if r.status_code != 200:
        return r.status_code

    content = r.json()
    
    # Going through the top <postCount> posts
    x = 0
    while(x < postCount):
        x += 1

        # Removing oldest file if overflowing
        if (vidCount > 65):  
            oldest_file = min(vidList, key=os.path.getctime)
            os.remove(os.path.abspath(oldest_file))
            oldest_short = min(shortList, key=os.path.getctime)
            os.remove(os.path.abspath(oldest_short))

        # Checking for a video
        if not content["data"]["children"][x]["data"]["is_video"]:
            postCount+=1 # Adding to the number of loops if post is not a video
            continue

        url = content["data"]["children"][x]["data"]["media"]["reddit_video"]["fallback_url"]
        videoUrl = url[:-16] # removing the fallback url modifier
        audioUrl = content["data"]["children"][x]["data"]["url"] + "/DASH_AUDIO_128.mp4"

        height = content["data"]["children"][x]["data"]["media"]["reddit_video"]["height"]
        width = content["data"]["children"][x]["data"]["media"]["reddit_video"]["width"]
        duration = content["data"]["children"][x]["data"]["media"]["reddit_video"]["duration"]
        title = content["data"]["children"][x]["data"]["title"].replace(" ", "_")

        print(videoUrl)
        rVideo = requests.get(videoUrl)
        if rVideo.status_code != 200:
            return rVideo.status_code
        
        # Saving video file to disk
        rVideoName = save_path + "temp.mp4"
        with open(rVideoName, "wb") as f:
            f.write(rVideo.content)

        if isDuplicate(rVideoName):
            continue

        rAudio = requests.get(audioUrl)
        if rAudio.status_code != 200:
            return rAudio.status_code
        
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
            os.rename(shortOutput, shortTemp)
            cmd = "ffmpeg -y -i " + shortTemp + " -vf pad=h=" + str(math.ceil(width/0.5625)) + ":y=(oh-ih)/2 " + shortOutput
            os.system(cmd)
            os.remove(shortTemp)

        # Cutting to under a minute for shorts
        if (duration > 59):
            os.rename(shortOutput, shortTemp)
            cmd = "ffmpeg -y -ss 00:00:00 -to 00:00:59 -i " + shortTemp + " -c copy " + shortOutput
            os.system(cmd)
            os.remove(shortTemp)

        if os.path.exists(rAudioName):
            os.remove(rAudioName)

        if os.path.exists(rVideoName):
            os.remove(rVideoName)

        vidCount+=1

        # Extra timer to prevent spamming
        time.sleep(2)

subReddits = ["https://www.reddit.com/r/interestingasfuck/top/.json",
               "https://www.reddit.com/r/oddlysatisfying/top/.json",
                 "https://www.reddit.com/r/Damnthatsinteresting/top/.json",
                 "https://www.reddit.com/r/Unexpected/top/.json",
                 "https://www.reddit.com/r/AnimalsBeingDerps/top/.json"]

for x in subReddits:
    val = fetchContent(x, 5)
    print(val)
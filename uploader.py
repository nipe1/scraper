import os
import time
import json
from datetime import datetime, timedelta
from youtube_uploader_selenium import YouTubeUploader
from tiktok_uploader.upload import upload_video
import utils

def uploadContent():
    """
	Handle video uploading
	"""
    list = os.listdir(utils.PATH_SHORTS)

    currentDate = datetime.now() + timedelta(hours=1)
    currentDate = utils.hour_rounder(currentDate)

    for video in list:
        with open(utils.PATH + 'last_date.txt', 'r+') as f:
            lastDate = f.read()
            # Adding 8 hours to the last date
            newDate = datetime.strptime(lastDate, '%m/%d/%Y, %H:%M') + timedelta(hours=8)

            # Can't schedule to the past, updating date to future if that is the case.
            if newDate < currentDate:
                newDate = currentDate

            if newDate > currentDate + timedelta(days=9, hours= 20):
                print("Upload cap of 10 days reached, try another day.")
                break

            f.seek(0)
            f.write(newDate.strftime("%m/%d/%Y, %H:%M"))
            f.truncate()
        
        handleYoutube(video)
        handleTiktok(video)

        # Deleting the short + title files after uploading, leaving the main one for comparing dupes.
        os.remove(utils.PATH_SHORTS + video)
        os.remove(utils.PATH_TITLES + video[:-3] +'json')
        time.sleep(5)

def handleYoutube(videoName):
    """
	Handle uploading to Youtube and scheduling
	"""
    try:
        with open(utils.PATH + 'last_date.txt', 'r') as f:
            date = f.read()

        with open(utils.PATH_TITLES + videoName[:-3] +'json', 'r+', encoding="utf-8") as j:
            jsonData = json.load(j)
            jsonData['schedule'] = date
            j.seek(0)
            json.dump(jsonData, j, ensure_ascii=False)
            j.truncate()
        
        short_path = utils.PATH_SHORTS + videoName
        metadata_path = utils.PATH_TITLES + videoName[:-3] +'json'

        uploader = YouTubeUploader(short_path, metadata_path, profile_path=os.getenv('PROFILE_PATH'))
        was_video_uploaded, video_id = uploader.upload()
        if was_video_uploaded:
            print(video_id + " uploaded!")
    except:
        print("Error while uploading to Youtube")

def handleTiktok(videoName):
    """
	Handle uploading to Tiktok and scheduling
	"""
    try:
        with open(utils.PATH + 'last_date.txt', 'r') as f:
            date = datetime.strptime(f.read(), '%m/%d/%Y, %H:%M')
        
        with open(utils.PATH_TITLES + videoName[:-3] +'json', 'r', encoding="utf-8") as j:
            title = json.load(j)['title'] 

        upload_video(utils.PATH + 'shorts/' + videoName,
            description=title,
            cookies=utils.PATH + 'cookies.txt',
            schedule=date,
            browser='firefox')
    except:
        print("Error while uploading to Tiktok")
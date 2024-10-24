"""Reddit scraper entry point script"""

import scraper
import uploader
import utils

def main():
	"""
	Main loop for scraper
	"""
	utils.init()
	
	# List of subreddits, in format ['subreddit','tags']. Tags are optional.
	subreddits = [["https://www.reddit.com/r/lifehacks/top/.json"],
                ["https://www.reddit.com/r/WatchPeopleDieInside/top/.json"],
                ["https://www.reddit.com/r/CrazyFuckingVideos/top/.json","Funny/Prank"],
                ["https://www.reddit.com/r/Satisfyingasfuck/top/.json"]]
	
    # Amount of videos to get per subreddit
	video_amount = 3
	
	scraper.getContent(subreddits, video_amount)
	uploader.uploadContent()


if __name__ == '__main__':
	main()
import time
import pandas as pd
import re
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# add options to keep driver open until closing command
options = Options()
options.add_experimental_option("detach", True)

# start webdriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

# open youtube in chrome driver and search for videos according to the below search string
search_string = "lufthansa review"
url = "https://www.youtube.com/results?search_query={" + search_string +"}"
driver.get(url)
# wait for page to load
time.sleep(5)

# decline all cookies
button = driver.find_elements(By.XPATH, "//*[@id='content']/div[2]/div[6]/div[1]/ytd-button-renderer[1]/yt-button-shape/button")
button[0].click()

# load all videos (by scrolling down) until a number of videos has been loaded
nbr_videos = 500
last_height = driver.execute_script("return document.documentElement.scrollHeight")
while True:
    # scroll to the bottom
    driver.execute_script("window.scrollTo(0, arguments[0]);", last_height)
    # wait for page to load
    time.sleep(3)

    # calculate new scroll height and compare with last scroll height
    new_height = driver.execute_script("return document.documentElement.scrollHeight")
    if new_height == last_height:
        break
    titles = driver.find_elements(By.XPATH, "//a[@id='video-title']")
    # check if enough videos have been loaded
    if len(titles) >= nbr_videos:
        break
    last_height = new_height

# for all videos: get their number of views, upload time, and the author channel
views = driver.find_elements(By.XPATH, '//ytd-video-renderer/div/div/div/ytd-video-meta-block/div[@id="metadata"]/div[@id="metadata-line"]/span[1]')
upload_time = driver.find_elements(By.XPATH, '//*[@id="metadata-line"]/span[2]')
author = driver.find_elements(By.XPATH, '//ytd-video-renderer/div[1]/div/div[2]/ytd-channel-name/div/div/yt-formatted-string/a')

# gather the data in a dataframe
data = []
for i, j, k, l in zip(titles, author, views, upload_time):
    data.append([i.get_attribute("title"), i.get_attribute("href"), j.get_attribute('innerHTML'), k.text, l.text])
# create pandas dataframe
df = pd.DataFrame(data, columns=["Title", "Reference", "Author", "Views", "Upload_time"])

# get the transcripts
transcripts = []
CRED = "\033[91m"
CEND = "\033[0m"
print(CRED + "Loading transcripts for videos:" + CEND)
for ind, video in enumerate(tqdm(df["Reference"])):
    # exclude shorts (no transcripts available)
    x = re.search("com/watch", video)
    if x:
        if not video is None:
            # navigate to video
            driver.get(video)
            # wait for page to load
            time.sleep(3)

            # identify the "3 dots"-button to get to the transcript
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//*[@id='button-shape']/button")))
            except:
                msg = 'could not find subtitles button'
                print(msg)

            # click the "3 dots"-button to get to the transcript
            try:
                element.click()
            except:
                msg = 'could not click'
                print(msg)
            # wait for selection box to open
            time.sleep(1)

            # click "Transkript anzeigen" from the selection box
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//*[@id='items']/ytd-menu-service-item-renderer[last()]")))
                element.click()
            except:
                pass
            # wait for transript to load
            time.sleep(1)

            # extract and gather all text from the transcript
            full_text = ""
            try:
                text = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "segments-container")))
                true_text = text.find_elements(By.XPATH, "//ytd-transcript-segment-renderer/div/yt-formatted-string")
                # combine single transcript lines to full text
                for line in true_text:
                    full_text = full_text + " " + line.text
            except:
                pass
        else:
            full_text = ""

    # empty string as placeholder for shorts
    else:
        full_text = ""
    transcripts.append(full_text)

    # print counter to show progress
    #if ind % 10 == 0:
    #    print(ind)

# add the transcripts to the dataframe as a new column
df['Transcript'] = transcripts
df.to_csv("youtube_video_transcripts.csv")

# close chrome driver
driver.close()
driver.quit()

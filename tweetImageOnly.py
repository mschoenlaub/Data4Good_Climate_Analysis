import os

import tweepy

dirname = os.path.dirname(__file__)

consumer_key = os.environ["CONSUMER_KEY"]
consumer_secret = os.environ["CONSUMER_SECRET"]
access_token = os.environ["ACCESS_TOKEN"]
access_token_secret = os.environ["ACCESS_TOKEN_SECRET"]

auth = tweepy.OAuth1UserHandler(
    consumer_key=consumer_key, consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)

api = tweepy.API(auth)
client = tweepy.Client(consumer_key=consumer_key, consumer_secret=consumer_secret,
                       access_token=access_token,
                       access_token_secret=access_token_secret)

# the name of the media file
graph_filename = os.path.join(dirname, "input/aiqmap.png")

# upload the file
media = api.media_upload(graph_filename)

# printing the information
print("The media ID is : " + media.media_id_string)
print("The size of the file is : " + str(media.size) + " bytes")
client.create_tweet(media_ids=[media.media_id_string])

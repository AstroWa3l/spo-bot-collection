import tweepy
import pandas as pd
import koios_python as koios
import os
from dotenv import load_dotenv
load_dotenv()
import datetime

# Twitter API credentials
consumer_api_key = os.getenv("PIADA_KEY")
consumer_secret_key = os.getenv("PIADA_KEY_N_SECRET")
consumer_token = os.getenv("PIADA_BEARER_TOKEN")
access_token = os.getenv("PIADA_ACCESS_TOKEN")
access_token_secret = os.getenv("PIADA_ACCESS_TOKEN_SECRET")


auth = tweepy.OAuthHandler(consumer_api_key, consumer_secret_key)
auth.set_access_token(access_token, access_token_secret)

client = tweepy.Client(consumer_key= consumer_api_key,consumer_secret= consumer_secret_key,
                       access_token= access_token,
                       access_token_secret= access_token_secret)


api = tweepy.API(auth)

try:
    api.verify_credentials()
    print("Authentication OK")
except:
    print("Error during authentication")
    
# Create a new instance of the API class
kp = koios.URLs()

piada = 'pool1hrv8gtrm0dgjg6zyss5uwa4nkruzfnh5vrdkr2sayj7x2nw6mjc'

# Get the current tip of the chain
tip = kp.get_tip()[0]

# Get the current epoch
current_epoch = tip['epoch_no']
previous_epoch = current_epoch - 1
summary_epoch = current_epoch - 2
comparison_epoch = current_epoch - 3

piada_summary_epoch = pd.DataFrame(kp.get_pool_history(piada, summary_epoch))
piada_comparison_epoch = pd.DataFrame(kp.get_pool_history(piada, comparison_epoch))

piada_summary_epoch['active_stake'] = piada_summary_epoch['active_stake'].astype(int)/1000000
piada_comparison_epoch['active_stake'] = piada_comparison_epoch['active_stake'].astype(int)/1000000
piada_summary_epoch['pool_fees'] = piada_summary_epoch['pool_fees'].astype(int)/1000000
piada_comparison_epoch['pool_fees'] = piada_comparison_epoch['pool_fees'].astype(int)/1000000
piada_summary_epoch['deleg_rewards'] = piada_summary_epoch['deleg_rewards'].astype(int)/1000000
piada_comparison_epoch['deleg_rewards'] = piada_comparison_epoch['deleg_rewards'].astype(int)/1000000

# Convert POSIXtime to human readable time
posix_time = kp.get_epoch_info(epoch_no=current_epoch)[0]['start_time']


def convert_posix_time(posix_time):
    dt_object = datetime.datetime.fromtimestamp(posix_time)
    time_string = dt_object.strftime('%Y-%m-%d %H:%M:%S')
    return time_string

def check_valid_range(posix_time):
    valid_range = range(posix_time, posix_time + 90)
    current_time = int(datetime.datetime.now().timestamp())
    if current_time in valid_range:
            return True
    else:
            return False
    
def find_word(text, search):

   result = re.findall('\\b'+search+'\\n', text, flags=re.IGNORECASE)
   if len(result)>0:
      return True
   else:
      return False    

    
def tweet_with_media(text, filename, media_category):
        
        # make sure inputs are strings if not tell the user
        if type(text) != str or type(filename) != str or type(media_category) != str:
                print("inputs must be strings")
                return
        
        # get our path for working directory and filename
        here = os.path.dirname(os.path.abspath('__file__'))
        media_filename = os.path.join(here, filename)
        
        # Check that the last tweet made is not the same as the current one
        # If it is the same then we do not want to make a new tweet
        # If it is not the same then we want to make a new tweet

        # get the last tweet made
        last_ten_tweets = client.get_home_timeline()
        recent_tweet = last_ten_tweets.data[0].text
        recent_tweet = recent_tweet.strip()
        
        if find_word(recent_tweet, str(summary_epoch)):
                print("Tweet already made")
                return
               
        
        # get chunked media for twitter API upload
        chunked_media = api.chunked_upload(filename=media_filename, media_category=media_category)
        
        # If upload of data successful we will have a media_id
        print(chunked_media.media_id)
        
        # update status with our text and media and print the tweet id
        update_status = client.create_tweet(text=text, media_ids=[chunked_media.media_id])
        
if check_valid_range(posix_time) == True:
        text = f"""Epoch's end Summary:
        Epoch: {summary_epoch}
	Active Stake: {format(piada_summary_epoch['active_stake'][0].round(2), ',')} ADA 👩‍🚀
	Total Blocks Forged: {piada_summary_epoch['block_cnt'][0]} 🧱
	Total Delegate Rewards: {piada_summary_epoch['deleg_rewards'][0]} ADA 🤑
	Total Fees: {piada_summary_epoch['pool_fees'][0]} ADA 💸
	Epoch ROA: {piada_summary_epoch['epoch_ros'][0]}% 📈
	"""
        tweet_with_media(text, 'aalogo.gif', 'tweet_gif')
        

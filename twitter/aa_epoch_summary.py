import tweepy
import pandas as pd
import koios_python as koios
import os
from dotenv import load_dotenv
load_dotenv()
import datetime
import re
from github import Github
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

#increase the number of rows that can be displayed in the console and columns
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)


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
                       access_token_secret= access_token_secret, bearer_token= consumer_token)


user = client.get_user(username='Piada_stakePool')


api = tweepy.API(auth)

try:
    api.verify_credentials()
    print("twitter Authentication OK")
except:
    print("Error during authentication")
    
# Get our block frost api key from the file .env
block_api_key = os.getenv('WAEL_BLOCKFROST_API_KEY')

from blockfrost import BlockFrostApi, ApiError, ApiUrls

block_api = BlockFrostApi(
	project_id=block_api_key,
	base_url=ApiUrls.mainnet.value,
)

try:
    health = block_api.health()
    print(health)   # prints object:    HealthResponse(is_healthy=True)
    health = block_api.health(return_type='json') # Can be useful if python wrapper is behind api version
    print(health)   # prints json:      {"is_healthy":True}
    health = block_api.health(return_type='pandas')
    print(health)   # prints Dataframe:         is_healthy
                    #                       0         True
except ApiError as e:
    print(e)


# Get our github api key from the file .env
# Then check login to github

personal_access_token = os.getenv('WAEL_PERSONAL_TOKEN')
# using an access token
g = Github(personal_access_token)

# Check that we can access the github api and returns correct user
try:   
    user = g.get_user()
    print(f'The github user is {user.name}')
except ApiError as e:
    print(e)
    
# Let's get the armada-alliance repo
repo = g.get_repo('armada-alliance/armada-alliance')

# Get contents of a file in the repo
contents = repo.get_contents("/services/website/content/en/stake-pools")
stake_pools = [x.name for x in contents]
stake_pool_ids = [x.replace('.md', '') for x in stake_pools]


# We have to use blockfrost for now since the hex values I can not convert to bech32 without cli..

# Use the blockfrost api to get the stake pools data

def get_stake_pool_data(hex_pool_id):
        
        if len(hex_pool_id) == 0:
                return "Please enter a non empty list of hex pool ids"
        pool_data_df = pd.DataFrame()
        
        for i in hex_pool_id:
                try:
                        pool_data = block_api.pool(pool_id=i, return_type='pandas')
                        pool_data_df = pd.concat([pool_data_df, pool_data], axis=0, join='outer')
                
                except ApiError as e:
                        print(e)
                
        index = pd.Index(range(0,len(pool_data_df)))
        pool_data_df.set_index(index, inplace=True)
        return pool_data_df


pool_data_df = get_stake_pool_data(stake_pool_ids)

armada_pool_ids = list(pool_data_df.pool_id)

# Create a new instance of the API class
kp = koios.URLs()
kp_test = koios.URLs(network='preview')

# Get the current tip of the chain
tip = kp.get_tip()[0]
tip_test = kp_test.get_tip()[0]

# Get the current epoch
current_epoch = tip['epoch_no']
current_epoch_test = tip_test['epoch_no']
previous_epoch = current_epoch - 1
summary_epoch = current_epoch - 2
comparison_epoch = current_epoch - 3

# Let's make a function that will get the epoch summary for a given epoch for all stake pools in the armada alliance
def get_stake_pool_hist(pool_ids, epoch_no):
        stake_pools_df = pd.DataFrame()
        # pool_ids is a list of stake pool ids
        for pool_id in pool_ids:
                # Get the historical data for the pool
                stake_pool_hist = pd.DataFrame(kp.get_pool_history(pool_id, epoch_no))
                pool_info = kp.get_pool_info(pool_id)[0]
                if pool_info['meta_json'] is not None:
                        pool_ticker = pool_info['meta_json']['ticker']
                else:
                        pool_ticker = 'None'
                stake_pool_hist['ticker'] = pool_ticker
                stake_pool_hist['pool_id'] = pool_id
                stake_pools_df = pd.concat([stake_pools_df, stake_pool_hist], axis=0, join='outer')
        return stake_pools_df

aa_summary_epoch = get_stake_pool_hist(armada_pool_ids, summary_epoch)
aa_current_epoch = get_stake_pool_hist(armada_pool_ids, current_epoch)
aa_comparison_epoch = get_stake_pool_hist(armada_pool_ids, comparison_epoch)

aa_summary_epoch['active_stake'] = aa_summary_epoch['active_stake'].astype(int)/1000000
aa_comparison_epoch['active_stake'] = aa_comparison_epoch['active_stake'].astype(int)/1000000
aa_summary_epoch['pool_fees'] = aa_summary_epoch['pool_fees'].astype(int)/1000000
aa_comparison_epoch['pool_fees'] = aa_comparison_epoch['pool_fees'].astype(int)/1000000
aa_summary_epoch['deleg_rewards'] = aa_summary_epoch['deleg_rewards'].astype(int)/1000000
aa_comparison_epoch['deleg_rewards'] = aa_comparison_epoch['deleg_rewards'].astype(int)/1000000

# Convert POSIXtime to human readable time
posix_time = kp.get_epoch_info(epoch_no=current_epoch)[0]['start_time']
posix_test_time = kp_test.get_epoch_info(epoch_no=171)[0]['start_time']

def convert_posix_time(posix_time):
    dt_object = datetime.datetime.fromtimestamp(posix_time)
    time_string = dt_object.strftime('%Y-%m-%d %H:%M:%S')
    return time_string

def check_valid_range(posix_time):
    valid_range = range(posix_time, posix_time + 1800)
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

def find_pattern(pattern, text):
        if re.search(pattern, text):
                return True
        else:
                return False
        
def tweet_with_media(text, filename, media_category):
        
        # make sure inputs are strings if not tell the user
        if type(text) != str or type(filename) != str or type(media_category) != str:
                print("inputs must be strings")
                return
        
        # get our path for working directory and filename
        # here = os.path.dirname(os.path.abspath('__file__'))
        # media_filename = os.path.join(here, filename)
        here = os.path.dirname(os.path.abspath('__file__'))
        media_filename = os.path.join(here, 'assets', filename)
        

        # Check that the last tweet made is not the same as the current one
        # If it is the same then we do not want to make a new tweet
        # If it is not the same then we want to make a new tweet
        tweets = client.get_users_tweets(id=user_id)
        tweets_text = [text.data['text'] for text in tweets.data]
        
        if check_valid_range(posix_time):
                for tweet in tweets_text[0:1]:
                        if find_pattern(r"Epoch:\s*" + str(summary_epoch), tweet):
                                print("We have already made a post for this epoch")
                                return
                # get chunked media for twitter API upload
                chunked_media = api.chunked_upload(filename=media_filename, media_category=media_category)
        
                # If upload of data successful we will have a media_id
                print(chunked_media.media_id)
        
        
                # update status with our text and media and print the tweet id
                update_status = client.create_tweet(text=text, media_ids=[chunked_media.media_id])
                
# epoch ros but only count the pools that have made blocks?
producing_pools = aa_summary_epoch[aa_summary_epoch['block_cnt'] > 0]
ros = round(producing_pools['epoch_ros'].mean(), 2)

# Let's get the data points we need for the tweet
total_blocks = aa_summary_epoch['block_cnt'].sum()
total_delegators = aa_summary_epoch['delegator_cnt'].sum()
total_delegator_rewards =round(aa_summary_epoch['deleg_rewards'].sum())
total_active_stake = round(aa_summary_epoch['active_stake'].sum())
total_pool_fees = round(aa_summary_epoch['pool_fees'].sum())
avg_pool_fees = round(aa_summary_epoch['pool_fees'].mean())
avg_epoch_ros = aa_summary_epoch['epoch_ros'].mean()

# format for numbers should be 1,000,000

text = f"""
Armada Alliance Epoch {summary_epoch} Summary
Active Stake 💰: {total_active_stake:,.0f} ₳
Blocks 🧱: {total_blocks:,.0f}
Delegators 👥: {total_delegators:,.0f}
Pool Fees 💵: {total_pool_fees:,.0f} ₳
Delegate Rewards 🤑: {total_delegator_rewards:,.0f} ₳
Epoch ROS 📈: {ros:,.2f}%
Website: https://armada-alliance.com
"""

data = aa_summary_epoch.sort_values(by='epoch_ros', ascending=False)[0:5]

plot = sns.barplot(x='ticker', y='epoch_ros', data=data)

# need to fix labels on x axis to be vertical
plot.set_xticklabels(plot.get_xticklabels(), rotation=90)

# change the y axis label name to epoch_roa %
plot.set(ylabel='epoch ROA %')

# Need a title at top of plot
plot.set_title(f'Top 5 Pools by Epoch ROA %')

# save the plot as a png
plot.figure.savefig(f'epoch_{summary_epoch}_roa.png')

tweet_with_media(text, f'epoch_{summary_epoch}_roa.png', 'tweet_image') 
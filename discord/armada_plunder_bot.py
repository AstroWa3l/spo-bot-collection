# bot.py
from email import message
import os
from webbrowser import get
import discord
import pandas as pd
from discord.ext import tasks
from dotenv import load_dotenv
from github import Github
load_dotenv()
import koios_python

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

# Get our block frost api key from the file .env
api_key = os.getenv('WAEL_BLOCKFROST_API_KEY')

from blockfrost import BlockFrostApi, ApiError, ApiUrls

api = BlockFrostApi(
	project_id=api_key,
	base_url=ApiUrls.mainnet.value,
)

# Koios Client
kp = koios_python.URLs()


# Get our github api key from the file .env
# Then check login to github

personal_access_token = os.getenv('WAEL_PERSONAL_TOKEN')
# using an access token
g = Github(personal_access_token)

# Check that we can access the github api and returns correct user
try:   
    user = g.get_user()
    print(user.name)
except ApiError as e:
    print(e)



###################################################################################################

# Get all the pool ids from the armada alliance github repo
# Let's get the armada-alliance repo
repo = g.get_repo('armada-alliance/armada-alliance')

# Get contents of a file in the repo
contents = repo.get_contents("/services/website/content/en/stake-pools")
stake_pools = [x.name for x in contents]
stake_pools_no_extensions = [x.replace('.md', '') for x in stake_pools]

# We have to use blockfrost for now since the hex values I can not convert to bech32 without cli..

# Use the blockfrost api to get the stake pools data

def get_stake_pool_data(hex_pool_id):
        
        if len(hex_pool_id) == 0:
                return "Please enter a non empty list of hex pool ids"
        pool_data_df = pd.DataFrame()
        
        for i in hex_pool_id:
                try:
                        pool_data = api.pool(pool_id=i, return_type='pandas')
                        pool_data_df = pd.concat([pool_data_df,pool_data], axis=0, join='outer')
                
                except ApiError as e:
                        print(e)
                
        index = pd.Index(range(0,len(pool_data_df)))
        pool_data_df.set_index(index, inplace=True)
        return pool_data_df


pool_data_df = get_stake_pool_data(stake_pools_no_extensions)
armada_pool_ids = list(pool_data_df.pool_id)

df_tip = kp.get_tip()


armada_pools_df = pd.DataFrame(kp.get_pool_info(armada_pool_ids))

tickers = []
for i in range(len(armada_pools_df)):
        
        if type(armada_pools_df.meta_json[i]) != type(None):
                tickers.append(armada_pools_df.meta_json[i]['ticker']) 
                
        else:
                tickers.append('NONE{}'.format(i))
                
armada_pools_df['ticker'] = tickers

###################################################################################################

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@tasks.loop(seconds=22)
async def test():
        
        channel = client.get_channel(1025844885967868047)
        messages = [msg async for msg in channel.history(limit=1)]
        contents = [message.content for message in messages]
        
        
        # Get Data of last 3 blocks every few seconds
        latest_3_blocks = pd.DataFrame(kp.get_blocks(content_range="0-2"))
        
        if type(latest_3_blocks) == type(pd.DataFrame()):
                
                if len(latest_3_blocks) > 0:
                        print("Latest Block Hash: {}\nBlock Height No: {}\nMade By Pool: {}"
                              .format(latest_3_blocks.hash[0],latest_3_blocks.block_height[0],latest_3_blocks.pool[0]))
                
                        for block in range(len(latest_3_blocks)):
                                if latest_3_blocks.pool[block] in armada_pool_ids:
                                        print("AHOY!")
                                        
                                        ticker = armada_pools_df[armada_pools_df['pool_id_bech32'] == latest_3_blocks.pool[block]].ticker.values[0]
                                        pool_id_hex = armada_pools_df[armada_pools_df['pool_id_bech32'] == latest_3_blocks.pool[block]].pool_id_hex.values[0] 
                                        
                                        message="""
                                        **Ahoy! More Plunder** 🏴‍☠️
                                        \n**New Block** 🧱 **added to** ***{}*** **pool's treasure chest**💰
                                        \n🪪 **Pool ID:**  ***{}***
                                        \n#️⃣ **Hash:**  ***{}***
                                        \n🕰 **Epoch:**  ***{}***   🔢 **Height_No:**  ***{}***
                                        \n📏 **Size**:  ***{}*** **kB**  🔢 **Number of Tx:**  ***{}***
                                        \n🧱 **Info:** https://cexplorer.io/block/{}
                                        \n🎱 **Pool Info:** https://armada-alliance.com/stake-pools/{}
                                        """.format(ticker,
                                                   latest_3_blocks.pool[block],
                                                   latest_3_blocks.hash[block],
                                                   latest_3_blocks.epoch_no[block],
                                                   latest_3_blocks.block_height[block],
                                                   round(latest_3_blocks.block_size[block].astype(int)/1000, 2),
                                                   latest_3_blocks.tx_count[block],
                                                   latest_3_blocks.hash[block], 
                                                   pool_id_hex
                                                   )
                                        for i in contents:
                                                if i.__contains__(latest_3_blocks.hash[block]) == False:
                                                        await channel.send(message)
                                                        print("Discord Message Sent")

@client.event
async def on_ready():
        if not test.is_running():
                test.start()



client.run(TOKEN)
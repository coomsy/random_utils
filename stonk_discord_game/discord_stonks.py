import os
import discord
import vars
import stonks
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
os.mkdir('stonk_logs')
handler = logging.FileHandler(filename=f'stonk_logs/discord{datetime.now()}.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

TOKEN = vars.DISCORD_TOKEN
lock = asyncio.Lock()

img_of_the_day = ''

client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user} We Online')

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.content.startswith('!'):
        
        #await message.channel.send(f'Suck my ass {message.author.mention}')
        req = message.content.replace('!', '', 1).split(' ', 1)
        # author.name
        # author.mention == guid = '<@!297470509040533504>'
        stonk = stonks.StonkMonitor () 

        if req[0] in ['join', 'j']:
            async with lock:
                stonk.add_user(
                    userid=message.author.mention,
                    name=message.author.name
                )

            logger.info('USER_JOIN [%s]', message.author.name)
            await message.channel.send(f'Welcome to the club {message.author.mention}. {img_of_the_day}')
            
        elif req[0] in ['buy', 'b']:
            # SYMBOL:SHARE
            stonk_request = await ensure_stock_request_format(req[1])
            async with lock:
                stonk.add_user_stock(message.author.mention, stonk_request)

            await message.channel.send('Order Successful')
            logger.info('USER_BUY [%s]', message.author.name)
            
        elif req[0] in ['sell', 's']:
            stonk_request = await ensure_stock_request_format(req[1])
            async with lock:
                stonk.sell_user_stock(message.author.mention, stonk_request)

            await message.channel.send('Order Successful')
            logger.info('USER_SELL [%s]', message.author.name)
            
            
        elif req[0] in ['leaderboard', 'l']:
            async with lock:
                user_stat = stonk.calculate_leaderboard()
            msg = "`CURRENT LEADERBOARD`\n"
            for stat in user_stat:
                msg += f"- {stat[0]}: `Profit[{stat[1]}] | Cash[{stat[2]}]`\n"
            await message.channel.send(msg)

            logger.info('USER_LEADERBOARD [%s]', message.author.name)
        
        elif req[0] in ['info', 'i']:
            async with lock:
                user_stat = stonk.calculate_profit(message.author.mention)

            msg = message.author.mention 
            msg += "```json\n"
            msg += json.dumps(user_stat, indent=4)
            msg += "```"
            await message.channel.send(msg)

            logger.info('USER_INFO [%s]', message.author.name)
        
        else:
            msg = "USAGE\n"
            msg += "```md\n"
            msg += "- join,j:         Join the fun :) |   !join\n"
            msg += "- info,i:         Get Your value  |   !info\n"
            msg += "- buy,b:          Buy stonks      |   !buy STOCK1:SHARES STOCK2:SHARES\n"
            msg += "- sell,s:         Sell Stonks     |   !sell STOCK1:SHARES STOCK2:SHARES\n"
            msg += "- leaderboards,l: See leaderboard |   !leaderboard\n"
            msg += "```\n"

            await message.channel.send(msg)
            
        #await message.channel.send('Suck my ass')

async def ensure_stock_request_format(user_stock_req: str) -> list:
    user_stock_req: list = [buy_req.split(':') for buy_req in user_stock_req.split(' ') ]
    # user_stock_req == [ [STOCK: str, shares: str],... ]
    for i in range(len(user_stock_req)):
        if len(user_stock_req[i]) == 2:
            user_stock_req[i][1] = int(user_stock_req[i][1])
        else:
            user_stock_req.remove(user_stock_req[i])
            logger.info("Invalid stock request, removing [%s]", user_stock_req[i])
    return user_stock_req

"""
    valid commands
        - join / j
        - buy / b
        - sell / s
        - leaderboard / l
        - info / i
"""


client.run(TOKEN)
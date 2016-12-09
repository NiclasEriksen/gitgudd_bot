import discord
import asyncio
import os
import random
import iron_cache
import json
import urllib.request
from rss import RSSFeed

client = discord.Client()
feed = RSSFeed()    # Initialize RSS-scraper, see rss.py for config.

# CONFIG #
# If you have set your token as an environment variable
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
# Channel ID where bot will post github notifications
COMMIT_CHANNEL = "222168837490081792"
ISSUE_CHANNEL = "222168837490081792"
FORUM_CHANNEL = "222168837490081792"
# Message that bot returns on !help
HELP_STRING = """
:book: **Kommandoer:**
!help: *denne menyen*\n
*... og ingenting mer.*
"""
# Seconds to wait between checking RSS feeds and API
COMMIT_TIMEOUT = 5
FORUM_TIMEOUT = 10
ISSUE_TIMEOUT = 60
DOFFEN_COUNT = 0
# How long to wait to delete messages
FEEDBACK_DEL_TIMER = 5
# How much XP to give on each messages
BASE_XP = 1

cache = iron_cache.IronCache()


async def trump_face(msg):
    faces = [
        ":expressionless:",
        ":smirk:",
        ":weary:",
        ":relieved:",
        ":wink:",
        ":stuck_out_tongue:",
        ":hushed:",
        ":kissing:"
    ]
    face_msg = await client.send_message(msg.channel, ":slight_smile:")
    for face in faces:
        await asyncio.sleep(0.75)
        await client.edit_message(face_msg, face)
    await asyncio.sleep(1)
    await client.delete_message(face_msg)


async def delete_edit_timer(msg, time, error=False, call_msg=None):
    ws = ":white_small_square:"
    bs = ":black_small_square:"
    for i in range(time + 1):
        await client.edit_message(
            msg, msg.content + "\n" + ws * (time - i) + bs * i
        )
        await asyncio.sleep(1)
    await client.delete_message(msg)
    if call_msg:
        await client.delete_message(call_msg)


@client.event
async def on_ready():
    print("Logged in as: {0}--{1}".format(client.user.name, client.user.id))
    print("------")

async def commit_checker():
    await client.wait_until_ready()
    channel = discord.Object(id=COMMIT_CHANNEL)
    while not client.is_closed:
        try:
            cstamp = cache.get(cache="git_stamps", key="commit").value
        except:
            cstamp = "missing"
            print("No stamp found for commits.")
        c_msg, stamp = feed.check_commit(cstamp)
        # c_msg = False
        if not cstamp == stamp:
            cache.put(cache="git_stamps", key="commit", value=stamp)
        if c_msg:
            async for log in client.logs_from(channel, limit=20):
                if log.content == c_msg:
                    print("Commit already posted, abort!")
                    break
            else:
                await client.send_message(channel, c_msg)
        await asyncio.sleep(COMMIT_TIMEOUT)

async def forum_checker():
    await client.wait_until_ready()
    channel = discord.Object(id=FORUM_CHANNEL)
    while not client.is_closed:
        try:
            fstamp = cache.get(cache="git_stamps", key="forum").value
        except:
            fstamp = "missing"
            print("No stamp found for forum.")
        f_msg, stamp = feed.check_forum(fstamp)
        if not fstamp == stamp:
            cache.put(cache="git_stamps", key="forum", value=stamp)
        if f_msg:
            async for log in client.logs_from(channel, limit=20):
                if log.content == f_msg:
                    print("Forum thread already posted, abort!")
                    break
            else:
                await client.send_message(channel, f_msg)
        await asyncio.sleep(FORUM_TIMEOUT)

async def issue_checker():
    await client.wait_until_ready()
    channel = discord.Object(id=ISSUE_CHANNEL)
    while not client.is_closed:
        try:
            cstamp = cache.get(cache="git_stamps", key="issue").value
        except:
            cstamp = "missing"
            print("No stamp found for issues.")
        i_msgs, stamp = feed.check_issue(cstamp)
        if not cstamp == stamp:
            cache.put(cache="git_stamps", key="issue", value=stamp)
        if i_msgs:
            async for log in client.logs_from(channel, limit=20):
                for msg in i_msgs:
                    if log.content == msg:
                        print("Issue already posted, removing!")
                        i_msgs.remove(msg)
            for msg in i_msgs:
                await client.send_message(channel, msg)
        await asyncio.sleep(ISSUE_TIMEOUT)


async def get_quote():
    # http://quotes.stormconsultancy.co.uk/random.json
    try:
        r = urllib.request.urlopen(
            "http://quotes.stormconsultancy.co.uk/random.json"
        )
        q = r.read().decode("utf-8")
        js = json.loads(q)
    except:
        return False
    else:
        msg = "**{0}:**\n*{1}*".format(
            js["author"],
            js["quote"]
        )
        return msg


@client.event
async def on_message(message):

    if message.content.startswith("!help"):
        await client.send_message(message.channel, HELP_STRING)
        await client.delete_message(message)


    elif message.content.startswith("!revers"):
        async for msg in client.logs_from(
            message.channel, limit=1, before=message
        ):
            newmsg = "*{0}*\n{1}".format(msg.author.name, msg.content[::-1])
            await client.delete_message(msg)
        await client.send_message(message.channel, newmsg)
        await client.delete_message(message)

    elif message.content.startswith("!quote"):
        ch = message.channel
        await client.delete_message(message)
        a = await get_quote()
        if a:
            await client.send_message(ch, a)

    elif message.content.startswith("!trump"):
        await client.delete_message(message)
        await trump_face(message)

    elif "doffen" in message.content.lower():
        global DOFFEN_COUNT
        DOFFEN_COUNT += message.content.lower().count("doffen")
        if DOFFEN_COUNT >= 3:
            p = random.choice(
                [
                    "doffen1.jpg",
                    "doffen2.jpeg",
                    "doffen3.png",
                    "doffen4.jpg",
                    "doffen5.jpg",
                    "doffen6.jpg"
                ]
            )
            await client.send_file(message.channel, p)
            DOFFEN_COUNT = 0

    if message.author.id == "256823993368182785":
        await client.send_message(
            message.channel,
            "Hold kjeft {0}.".format(message.author.mention)
        )

client.loop.create_task(commit_checker())
client.loop.create_task(issue_checker())
# client.loop.create_task(forum_checker())
client.run(TOKEN)

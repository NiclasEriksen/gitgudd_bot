import discord
import asyncio
import os
import random
import iron_cache
import json
import urllib.request
from rss import RSSFeed
from snakk import Prat

client = discord.Client()
prat = Prat()
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
GDRIVE_TIMEOUT = 20
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

async def gdrive_checker():
    await client.wait_until_ready()
    channel = discord.Object(id=COMMIT_CHANNEL)
    while not client.is_closed:
        try:
            gstamp = cache.get(cache="git_stamps", key="gdrive").value
        except:
            gstamp = "missing"
            print("No stamp found for gdrive.")
        g_msg, stamp = feed.check_file(gstamp)
        # c_msg = False
        if not gstamp == stamp:
            cache.put(cache="git_stamps", key="gdrive", value=stamp)
        if g_msg:
            await client.send_message(channel, g_msg)
        await asyncio.sleep(GDRIVE_TIMEOUT)

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

def test_embed():
    e = discord.Embed(
        title="New commit to godot",
        description="Merge pull request #7680 from cbscribe/master",
        url="https://github.com/godotengine/godot/commit/36b6ba8e94d9afcb06aa2579bf627651f7ebfea0",
        color=0xFF2010,
    )
    e.set_author(
        name="Akien",
        url="https://github.com/akien-mga",
        icon_url="https://avatars1.githubusercontent.com/u/4701338?v=3&s=72"
    )
    return e
def test_embed_commit():
    EMBED_COMMIT_COLOR = 0x1E54F8
    e = discord.Embed(
        title="CollisionShape2D: Fix warning icon not updating.",
        description="`CollisionPolygon2D` also had this problem.",
        url="https://github.com/godotengine/godot/commit/16eee2f59b6d2567d7d15d9a2ff66c52e9705137",
        color=EMBED_COMMIT_COLOR,
    )
    e.set_footer(
        text="Commit | godot",
        icon_url="https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/png/512/clock.png"
    )
    e.set_author(
        name="Hinsbart",
        url="https://github.com/Hinsbart",
        icon_url="https://avatars3.githubusercontent.com/u/8281916?v=3&s=72"
    )
    return e

def test_embed_pr():
    EMBED_PR_COLOR = 0x84D430
    e = discord.Embed(
        title="corrected ClassDB::instance() return type #7681",
        description="The return type was void which is wrong, it's Variant. This caused some confusion on my part and the generated bindings for the WIP dlscript module have errors because of this.",
        url="https://github.com/godotengine/godot/commit/36b6ba8e94d9afcb06aa2579bf627651f7ebfea0",
        color=EMBED_PR_COLOR,
    )
    e.set_footer(
        text="Pull request | godot",
        icon_url="https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/png/512/pull-request.png"
    )
    e.set_author(
        name="karoffel",
        url="https://github.com/karoffel",
        icon_url="https://avatars1.githubusercontent.com/u/5209613?v=3&s=88"
    )
    return e

def test_embed_issue():
    EMBED_ISSUE_COLOR = 0xD44730
    MAX_DESC_LENGTH = 250
    e = discord.Embed(
        title="Starting the profiler freezes godot",
        description="Linux alienware 4.8.0-34-generic #36-Ubuntu SMP Wed Dec 21 17:24:18 UTC 2016 x86_64 x86_64 x86_64 GNU/Linux\nGodot v2.1.2.stable.official\n\nIssue description:\nPressing on Start Profiling make Godot use 100% processor and freezes the editor."[0, MAX_DESC_LENGTH] + "...",
        url="https://github.com/godotengine/godot/commit/36b6ba8e94d9afcb06aa2579bf627651f7ebfea0",
        color=EMBED_ISSUE_COLOR,
    )
    e.set_footer(
        text="Issue #7688 | godot",
        icon_url="https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/png/512/alert-circled.png"
    )
    e.set_author(
        name="razvanc-r",
        url="https://github.com/razvanc-r",
        icon_url="https://avatars0.githubusercontent.com/u/1177508?v=3&s=88"
    )
    return e

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

    elif message.content.startswith("!test_embed"):
        await client.send_message(message.channel, embed=test_embed())

    elif message.content.startswith("!test_commit"):
        await client.send_message(message.channel, embed=test_embed_commit())

    elif message.content.startswith("!test_pr"):
        await client.send_message(message.channel, embed=test_embed_pr())

    elif message.content.startswith("!test_issue"):
        await client.send_message(message.channel, embed=test_embed_issue())

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

    for m in message.mentions:
        if m.id == client.user.id:
            await client.send_message(
                message.channel,
                prat.klage()
            )
            break

    # if message.author.id == "256823993368182785":
    #     await client.send_message(
    #         message.channel,
    #         "Hold kjeft {0}.".format(message.author.mention)
    #     )

client.loop.create_task(commit_checker())
client.loop.create_task(gdrive_checker())
#client.loop.create_task(issue_checker())
# client.loop.create_task(forum_checker())
client.run(TOKEN)

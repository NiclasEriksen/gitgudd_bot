import discord
import asyncio
import os
import random
import iron_cache
import json
import urllib.request
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from systemd import journal
from rss import RSSFeed, GH_OBJECT, GH_COMMIT, GH_PR, GH_ISSUE, GH_QA, GH_FORUM, GH_FILE
from snakk import Prat
from models import Base, User, Stamp


client = discord.Client()
prat = Prat()
feed = RSSFeed()    # Initialize RSS-scraper, see rss.py for config.

# When running script, initialize db engine and create sqlite database
# with tables if not existing.
engine = create_engine("sqlite:///app.db")
# Session maker object, to instantiate sessions from
Session = sessionmaker(bind=engine)
# Ensure all tables are created.
print("Ensuring database scheme is up to date.")
Base.metadata.create_all(engine)

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
# Embed settings
MAX_DESC_LINES      =   4
EMBED_COMMIT_COLOR  =   0x1E54F8
EMBED_PR_COLOR      =   0x84D430
EMBED_ISSUE_COLOR   =   0xD44730
EMBED_QA_COLOR      =   0xF1E739
EMBED_FORUM_COLOR   =   0x3D81A6
EMBED_COMMIT_ICON   =   "https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/png/512/clock.png"
EMBED_PR_ICON       =   "https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/png/512/pull-request.png"
EMBED_ISSUE_ICON    =   "https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/png/512/alert-circled.png"
EMBED_QA_ICON       =   "https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/png/512/help-circled.png"
EMBED_FORUM_ICON    =   "https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/png/512/chatbubbles.png"
EMBED_GDRIVE_ICON   =   "https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/png/512/android-playstore.png"

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


async def check_duplicate_url(channel, url):
    if not url:
        print("URL is blank, won't check for duplicate.")
        journal.send("URL is blank, won't check for duplicate.")
        return False
    async for log in client.logs_from(channel, limit=20):
        for e in log.embeds:
            if "url" in e:
                if url == e["url"]:
                    return True
        else:   # No duplicates
            continue    # Continue to next log item
        break   # If there was duplicates, it reaches this
    else:
        return False


@client.event
async def on_ready():
    print("Logged in as: {0}--{1}".format(client.user.name, client.user.id))
    print("------")
    journal.send("Logged in as: {0}--{1}".format(client.user.name, client.user.id))
    journal.send("------")

async def gdrive_checker():
    await client.wait_until_ready()
    channel = discord.Object(id=COMMIT_CHANNEL)
    while not client.is_closed:
        session = Session()
        gstamp = session.query(Stamp).filter_by(descriptor="gdrive").first()
        gh_obj, stamp = feed.check_file(gstamp if gstamp else "missing")

        if gstamp:
            if not gstamp.stamp == stamp:
                gstamp.stamp = stamp
        else:
            journal.send("No stamp found for gdrive.")
            dbstamp = Stamp(descriptor="gdrive", stamp=stamp)
            session.add(dbstamp)

        if gh_obj:
            await client.send_message(channel, embed=embed_gh(gh_obj))

        session.commit()
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
            journal.send("No stamp found for commits.")
        gh_obj, stamp = feed.check_commit(cstamp)
        # c_msg = False
        if not cstamp == stamp:
            try:
                cache.put(cache="git_stamps", key="commit", value=stamp)
            except:
                print("Error putting stamps for commit.")
        if gh_obj:
            if await check_duplicate_url(channel, gh_obj["url"]):
                print("Commit already posted, abort!")
                journal.send("Commit already posted, abort!")
            else:
                print("Posting commit!")
                journal.send("Posting commit!")
                await client.send_message(channel, embed=embed_gh(gh_obj))
        await asyncio.sleep(COMMIT_TIMEOUT)

def test_embed():
    e = discord.Embed(
        title="New commit to godot",
        description="Merge pull request #7680 from cbscribe/master",
        url="https://github.com/godotengine/godot/commit/36b6ba8e94d9afcb06aa2579bf627651f7ebfea0",
        color=0xFF2010,
    )
    e.set_author(
        name="akien-mga",
        url="https://github.com/akien-mga",
        icon_url="https://avatars1.githubusercontent.com/u/4701338?v=3&s=72"
    )
    return e

def embed_gh(gh_object):
    tiny = False
    desc_text = gh_object["desc"]
    line_count = desc_text.count("\n") + 1
    if line_count > MAX_DESC_LINES:
        lbreaks = [n for n in range(len(desc_text)) if desc_text.find('\n', n) == n]
        desc_text = desc_text[0:lbreaks[MAX_DESC_LINES - 1]] + "\n....."
    issue_number = gh_object["issue_number"] + " " if gh_object["issue_number"] else ""
    post_type = icon_url = ""
    color = 0xFFFFFF
    if gh_object["type"] == GH_COMMIT:
        post_type = "Commit"
        color = EMBED_COMMIT_COLOR
        icon_url = EMBED_COMMIT_ICON
    elif gh_object["type"] == GH_PR:
        post_type = "Pull request"
        color = EMBED_PR_COLOR
        icon_url = EMBED_PR_ICON
    elif gh_object["type"] == GH_ISSUE:
        post_type = "Issue"
        color = EMBED_ISSUE_COLOR
        icon_url = EMBED_ISSUE_ICON
    elif gh_object["type"] == GH_ISSUE:
        post_type = "Issue"
        color = EMBED_ISSUE_COLOR
        icon_url = EMBED_ISSUE_ICON
    elif gh_object["type"] == GH_QA:
        post_type = "Question"
        color = EMBED_QA_COLOR
        icon_url = EMBED_QA_ICON
        tiny = True
    elif gh_object["type"] == GH_FORUM:
        post_type = "Forum thread by " + gh_object["author"]
        color = EMBED_FORUM_COLOR
        icon_url = EMBED_FORUM_ICON
        tiny = True
    elif gh_object["type"] == GH_FILE:
        post_type = "Google Drive"
        color = EMBED_PR_COLOR
        icon_url = EMBED_GDRIVE_ICON
        tiny = True
    if tiny:
        desc_text = discord.Embed.Empty

    footer_text = "{type} {issue_number}| {r}".format(
        type=post_type,
        issue_number=issue_number,
        r=gh_object["repository"]
    )

    e = discord.Embed(
        title=gh_object["title"],
        description=desc_text,
        url=gh_object["url"],
        color=color,
    )
    e.set_footer(
        text=footer_text,
        icon_url=icon_url
    )
    if not tiny:
        e.set_author(
            name=gh_object["author"],
            url=gh_object["author_url"],
            icon_url=gh_object["avatar_icon_url"]
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
            journal.send("No stamp found for forum.")
        f_msg, stamp = feed.check_forum(fstamp)
        if not fstamp == stamp:
            try:
                cache.put(cache="git_stamps", key="forum", value=stamp)
            except:
                print("Error putting stamps for forum.")
        if f_msg:
            async for log in client.logs_from(channel, limit=20):
                if log.content == f_msg:
                    print("Forum thread already posted, abort!")
                    journal.send("Forum thread already posted, abort!")
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
            journal.send("No stamp found for issues.")
        i_msgs, stamp = feed.check_issue(cstamp)
        if not cstamp == stamp:
            try:
                cache.put(cache="git_stamps", key="issue", value=stamp)
            except:
                print("Error putting stamps for issue.")
        if i_msgs:
            async for log in client.logs_from(channel, limit=20):
                for msg in i_msgs:
                    if log.content == msg:
                        print("Issue already posted, removing!")
                        journal.send("Issue already posted, removing!")
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

    elif message.content.startswith("!test_react"):
        print(message.author.nick if message.author.nick else message.author.name)

    # elif message.content.startswith("!test_react"):
    #     print("Testng reactiong")
    #     emoji = "\U0001F3BA"
    #     for e in message.server.emojis:
    #         if e.name == "angryfaic":
    #             emoji = e
    #     await client.add_reaction(message, emoji)
    #     #     if e.name == "trumpet":
    #     #         emoji = e
    #     #         break
    #     # if emoji:
    #     await client.add_reaction(message, ":trumpet:278630877330669579")

    elif message.content.startswith("!test_embed"):
        async for log in client.logs_from(message.channel, limit=20):
            for e in log.embeds:
                if "url" in e:
                    if "https://github.com/NiclasEriksen/lfm-healer/commit/1ad9e577ed60b25548061f57a5ba7df1c24f6e7a" == e["url"]:
                        print("NOT POSTING!")
                        break
            else:   # No duplicates
                continue    # Continue to next log item
            break   # If there was duplicates, it reaches this
        else:
            print("POSTING!")

    elif message.content.startswith("!test_commit"):
        gho, _s = feed.check_commit("2016-12-28T20:02:57.848229Z")
        gho["author_url"] = ""
        gho["url"] = ""
        await client.send_message(message.channel, embed=embed_gh(gho))

    elif message.content.startswith("!test_pr"):
        gh_object = dict(
            type=1,
            title="corrected ClassDB::instance() return type",
            desc="The return type was void which is wrong, it's Variant. This caused some confusion on my part and the generated bindings for the WIP dlscript module have errors because of this.",
            url="https://github.com/godotengine/godot/commit/36b6ba8e94d9afcb06aa2579bf627651f7ebfea0",
            author="karoffel",
            author_url="https://github.com/karoffel",
            avatar_icon_url="https://avatars1.githubusercontent.com/u/5209613?v=3&s=88",
            issue_number="#7681",
            repository="godot"
        )
        if await check_duplicate_url(message.channel, gh_object["url"]):
            await client.send_message(message.channel, "Nope.")
        else:
            await client.send_message(message.channel, embed=embed_gh(gh_object))

    elif message.content.startswith("!test_issue"):
        gh_object = dict(
            type=2,
            title="Starting the profiler freezes godot",
            desc="Linux alienware 4.8.0-34-generic #36-Ubuntu SMP Wed Dec 21 17:24:18 UTC 2016 x86_64 x86_64 x86_64 GNU/Linux\nGodot v2.1.2.stable.official\n\nIssue description:\nPressing on Start Profiling make Godot use 100\% processor and freezes the editor.",
            url="https://github.com/godotengine/godot/commit/36b6ba8e94d9afcb06aa2579bf627651f7ebfea",
            author="razvanc-r",
            author_url="https://github.com/razvanc-r",
            avatar_icon_url="https://avatars0.githubusercontent.com/u/1177508?v=3&s=88",
            issue_number="#7688",
            repository="godot"
        )
        if await check_duplicate_url(message.channel, gh_object["url"]):
            await client.send_message(message.channel, "Nope.")
        else:
            await client.send_message(message.channel, embed=embed_gh(gh_object))

    elif message.content.startswith("!test_qa"):
        gh_object = dict(
            type=3,
            title="Set Editor Layout as Default",
            desc="",
            url="https://godotengine.org/qa/12018/set-editor-layout-as-default",
            author="",
            author_url="",
            avatar_icon_url="",
            issue_number=None,
            repository="Engine"
        )
        await client.send_message(message.channel, embed=embed_gh(gh_object))

    elif message.content.startswith("!test_forum"):
        gh_object = dict(
            type=4,
            title="[Off-topic] Godot really feels life Delphi for games",
            desc="",
            url="https://godotdevelopers.org/forum/discussion/18209/off-topic-godot-really-feels-life-delphi-for-games",
            author="eye776",
            author_url="",
            avatar_icon_url="",
            issue_number=None,
            repository="General Chat"
        )
        await client.send_message(message.channel, embed=embed_gh(gh_object))

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

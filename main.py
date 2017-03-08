import discord
import asyncio
import os
import random
import urllib.request
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from systemd import journal
from rss import RSSFeed, GH_OBJECT, GH_COMMIT, GH_PR, GH_ISSUE, GH_QA, GH_FORUM, GH_FILE
from snakk import Prat
from models import Base, User, Stamp
from serverstatus import proxmox


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



def format_time(secs):
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    return h, m, s 


async def get_vm_list():
    msg = "```\nGjeldende virtuelle maskiner:\n" + "-" * 34
    for vm in proxmox.cluster.resources.get(type="vm"):
        desc = "{name}".format(
            name=vm["name"],
        )
        if len(desc) < 12:
            desc += " " * (12 - len(desc))
        elif len(desc) > 12:
            desc = desc[:12]

        status = vm["status"]
        if len(status) < 7:
            status += " " * (7 - len(status))
        elif len(status) > 7:
            status = status[:7]

        msg += "\n{desc} | {status}".format(
            desc=desc,
            status=status
        )
        if not vm["status"] == "stopped":
            h, m, s = format_time(int(vm["uptime"]))
            msg += " | {h}h{m}m{s}s".format(
                h=h,
                m=m,
                s=s
            )
        else:
            msg += " |"
    msg += "\n```"
    return msg


async def get_vm(vmid):
    for vm in proxmox.cluster.resources.get(type="vm"):
        if str(vm["vmid"]) == vmid or vm["name"] == vmid:
            return vm
    return False


def format_vm_msg(vm):
    return "{0} {1}".format(vm["name"], vm["vmid"])


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
        gh_obj, stamp = feed.check_file(gstamp.stamp if gstamp else "missing")

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
        session = Session()
        cstamp = session.query(Stamp).filter_by(descriptor="commit").first()
        gh_obj, stamp = feed.check_commit(
            cstamp.stamp if cstamp else "missing"
        )

        if cstamp:
            if not cstamp.stamp == stamp:
                # Updating stamp in db
                cstamp.stamp = stamp
        else:
            dbstamp = Stamp(descriptor="commit", stamp=stamp)
            session.add(dbstamp)
            journal.send("No stamp found for commits.")
            print("Adding new stamp to database for commits")

        if gh_obj:
            if await check_duplicate_url(channel, gh_obj["url"]):
                print("Commit already posted, abort!")
                journal.send("Commit already posted, abort!")
            else:
                print("Posting Commit notification.")
                journal.send("Posting commit!")
                await client.send_message(channel, embed=embed_gh(gh_obj))

        session.commit()
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


@client.event
async def on_message(message):

    id = message.author.id

    if message.author.id == client.user.id:
        journal.send("Not granting XP to bot.")
        print("Not granting XP to bot.")
    elif message.content.startswith("!"):
        # Don't give XP for bot commands.
        journal.send("Ignoring message as a command, no xp.")
        print("Ignoring message as a command, no xp.")
    else: 
        xp = 1 + len(message.content) // 80
        session = Session()
        # Check if the user exists in the database and update the xp column.
        # If user doesn't exist, create row.
        if session.query(User).filter_by(userid=id).first():
            session.query(User).filter_by(userid=id).update(
                {"xp": User.xp + xp}
            )
            journal.send("Awarded {0} xp to {1}".format(xp, message.author.name))
            print("Awarded {0} xp to {1}".format(xp, message.author.name))
        else:
            journal.send("Creating new user row for {0}".format(id))
            print("Creating new user row for {0}".format(id))
            u = User(userid=id, xp=xp)
            session.add(u)

        session.commit()

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

    elif message.content.startwith("!vm"):
        msg = ""
        if len(message.content) < 5 or message.content[3] != " ":
            msg = "Slik: !vm <navn eller id>"
        else:
            vmid = message.content[4:]
            vm = get_vm(vmid)
            if vm:
                msg = format_vm_msg(vm)
            else:
                msg = "Fant ikke den maskinen..."
        await client.send_message(message.channel, msg)

    elif message.content.startswith("!serverstatus"):
        await client.send_message(message.channel, get_vm_list())

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
# client.loop.create_task(gdrive_checker())
client.run(TOKEN)

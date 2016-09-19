import discord
import asyncio
import os
import iron_cache
from rss import RSSFeed

client = discord.Client()
feed = RSSFeed()    # Initialize RSS-scraper, see rss.py for config.

### CONFIG ###
# If you have set your token as an environment variable
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
# Uncomment this instead if you'd like to specify it here
# TOKEN = "YOUR_TOKEN"
# Roles that users can assign themselves to, must be lower case.
# AVAILABLE_ROLES = [
#     "programmer",
#     "designer",
#     "artist",
#     "sound designer"
# ]
# Default role for new members of server, must be lower case.
# DEFAULT_ROLE = "blue"
# Channel ID where bot will post github notifications
COMMIT_CHANNEL = "222168837490081792"
ISSUE_CHANNEL = "222168837490081792"
#COMMIT_CHANNEL = "225071177721184256"
#ISSUE_CHANNEL = COMMIT_CHANNEL
# Message that bot returns on !help
HELP_STRING = """
:book: **Kommandoer:**
!help: *denne menyen*\n
*... og ingenting mer.*
"""
# Seconds to wait between checking RSS feeds and API
COMMIT_TIMEOUT = 5
ISSUE_TIMEOUT = 35
# How long to wait to delete messages
FEEDBACK_DEL_TIMER = 5

cache = iron_cache.IronCache()


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

@client.event
async def on_message(message):

    if message.content.startswith("!help"):
        await client.send_message(message.channel, HELP_STRING)
        await client.delete_message(message)

    elif message.content.startswith("!revers"):
        async for msg in client.logs_from(
            message.channel, limit=1, before=message
        ):
            newmsg = msg.content[::-1]
        await client.delete_message(message)
        await client.send_message(message.channel, newmsg)

    # elif message.content.startswith("!assign"):
    #     s = message.content[8:] # remove !assign
    #     if not len(s) or not message.content[7] == " ":
    #         tmp = await client.send_message(
    #             message.channel,
    #             "Usage: !assign [role]"
    #         )
    #         await delete_edit_timer(tmp, FEEDBACK_DEL_TIMER, error=True, call_msg=message)
    #     else:
    #         newrole = s
    #         roles = message.server.roles
    #         for r in roles:
    #             if r.name.lower() == newrole.lower():
    #                 if r.name.lower() in AVAILABLE_ROLES:
    #                     if not r in message.author.roles:
    #                         await client.add_roles(message.author, r)
    #                         tmp = await client.send_message(
    #                             message.channel, ":white_check_mark: User {0} added to {1}.".format(
    #                                 message.author.name, r.name
    #                             )
    #                         )
    #                         await delete_edit_timer(tmp, FEEDBACK_DEL_TIMER, call_msg=message)
    #                     else:
    #                         tmp = await client.send_message(
    #                             message.channel,
    #                             "You already have that role."
    #                         )
    #                         await delete_edit_timer(
    #                             tmp, FEEDBACK_DEL_TIMER, error=True, call_msg=message
    #                         )
    #                 else:
    #                     tmp = await client.send_message(
    #                         message.channel,
    #                         ":no_entry: *You're not allowed to assign yourself to that role.*"
    #                     )
    #                     await delete_edit_timer(tmp, FEEDBACK_DEL_TIMER, error=True, call_msg=message)
    #                 break
    #         else:
    #             tmp = await client.send_message(
    #                 message.channel,
    #                 ":no_entry: **{0}** <- *Role not found.*".format(
    #                     newrole.upper()
    #                 )
    #             )
    #             await delete_edit_timer(tmp, FEEDBACK_DEL_TIMER, error=True, call_msg=message)
    #
    # elif message.content.startswith("!unassign"):
    #     s = message.content[10:] # remove !unassign
    #     if not len(s) or not message.content[9] == " ":
    #         tmp = await client.send_message(
    #             message.channel,
    #             "Usage: !unassign [role]"
    #         )
    #         await delete_edit_timer(tmp, FEEDBACK_DEL_TIMER, call_msg=message)
    #     else:
    #         oldrole = s
    #         roles = message.server.roles
    #         for r in message.author.roles:
    #             # print(r.name.lower())
    #             if r.name.lower() == oldrole.lower():
    #                 # print(r.name, "<-FOUND")
    #                 await client.remove_roles(message.author, r)
    #                 tmp = await client.send_message(message.channel, ":white_check_mark: Role was removed.")
    #                 await delete_edit_timer(tmp, FEEDBACK_DEL_TIMER, call_msg=message)
    #                 break
    #         else:
    #             tmp = await client.send_message(
    #                 message.channel,
    #                 ":no_entry: **{0}** <- You don't have that role.".format(
    #                     oldrole.upper()
    #                 )
    #             )
    #             await delete_edit_timer(tmp, FEEDBACK_DEL_TIMER, error=True, call_msg=message)
    # elif message.content.startswith("!roles"):
    #     s = ":scroll: **Available roles:**\n"
    #     s += "```\n"
    #     for i, r in enumerate(AVAILABLE_ROLES):
    #         s += "{0}".format(r.upper())
    #         if not i == len(AVAILABLE_ROLES) - 1:
    #             s += ", "
    #     s += "```"
    #     await client.send_message(
    #         message.channel,
    #         s
    #     )
    #     await client.delete_message(message)

#
# @client.event
# async def on_member_join(m):
#     for r in m.server.roles:
#         if r.name.lower() == DEFAULT_ROLE.lower():
#             await client.add_roles(m, r)


client.loop.create_task(commit_checker())
client.loop.create_task(issue_checker())
client.run(TOKEN)

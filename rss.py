import feedparser
import datetime
from html2text import html2text
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from time import mktime, sleep
import requests

COMMIT_URL = "https://github.com/NiclasEriksen/lfm-healer/commits/master.atom"
ISSUE_URL = "https://api.github.com/repos/NiclasEriksen/lfm-healer/issues?sort=created"
FORUM_URL = "https://godotdevelopers.org/forum/discussions/feed.rss"
FILE_ID = "0By_JUDss2hEKXzRWRVNNOUtyYmM"
GH_COMMIT           =   0
GH_PR               =   1
GH_ISSUE            =   2
GH_QA               =   3
GH_FORUM            =   4
GH_FILE             =   5
GH_OBJECT           =   dict(
    type=0,
    title="No title",
    desc="No description",
    url="",
    author="No author",
    author_url="",
    avatar_icon_url="",
    issue_number=None,
    repository=""
)

class RSSFeed:

    def __init__(self):
        self.commit_url = COMMIT_URL
        self.issue_url = ISSUE_URL
        self.forum_url = FORUM_URL
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        self.drive = GoogleDrive(gauth)

    def check_file(self, stamp):
        try:
            old_stamp = datetime.datetime.strptime(
                stamp,
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        except ValueError:
            old_stamp = datetime.datetime.utcnow()
            print("Invalid stamp (or none): {0}".format(stamp))
            stamp = datetime.datetime.strftime(
                old_stamp,
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            return None, stamp

        apk = self.drive.CreateFile({"id": FILE_ID})
        apk.FetchMetadata(fetch_all=True)
        filestamp = datetime.datetime.strptime(
            apk["modifiedDate"],
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        if filestamp > old_stamp:
            gho = GH_OBJECT.copy()
            gho["type"] = GH_FILE
            gho["title"] = "APK oppdatert"
            gho["desc"] = ""
            gho["url"] = apk["alternateLink"]
            gho["repository"] = apk["title"] + " {0}KiB".format(apk["size"] / 1024)
            return gho, apk["modifiedDate"]
        else:
            return None, stamp

    def check_forum(self, url, stamp):
        msg = None
        d = feedparser.parse(url)
        latest = d["items"][:5]
        try:
            old_stamp = datetime.datetime.fromtimestamp(float(stamp))
        except ValueError:
            print("Stamp invalid, making new from current time.")
            old_stamp = datetime.datetime.now()
            stamp = float(mktime(old_stamp.utctimetuple()))
        for thread in reversed(latest):
            th_stamp = datetime.datetime.fromtimestamp(
                mktime(thread["published_parsed"])
            )
            if th_stamp > old_stamp:
                msg = self.format_forum_message(thread)
                print("New forum thread found, posting.")
                return msg, mktime(thread["published_parsed"])
        else:
            return False, float(mktime(old_stamp.utctimetuple()))

    def parse_commit(self, stamp):
        d = feedparser.parse(self.commit_url)
        try:
            if not d.feed.updated == stamp:
                # self.save_stamp("commit", d.feed.updated)
                return d["items"][0], d.feed.updated
            else:
                return None, stamp
        except AttributeError as e:
            print("Error in feed: {0}".format(e))
        except KeyError as e:
            print("Error in feed: {0}".format(e))
        return None, stamp

    def check_commit(self, stamp):
        e, newstamp = self.parse_commit(stamp)
        if e:
            return self.format_commit_message(e), newstamp
        else:
            return False, newstamp

    def check_issue(self, stamp):
        try:
            old_stamp = datetime.datetime.strptime(
                stamp,
                "%Y-%m-%dT%H:%M:%SZ"
            )
        except ValueError:
            old_stamp = datetime.datetime.utcnow()
            stamp = datetime.datetime.strftime(
                old_stamp,
                "%Y-%m-%dT%H:%M:%SZ"
            )
        url = "{0}{1}{2}".format(
            self.issue_url, "&since=", stamp
        )
        try:
            r = requests.get(url=url)
        except:
            return [], stamp
        parsed = r.json()

        try:
            r.json()[0]
        except KeyError:
            print("Nothing recieved from API, call limit?")
            return [], stamp    # Probably went over call limit
        except IndexError:
            # No new issues.
            return [], stamp

        # 2016-09-12T20:26:12Z
        messages = []
        latest_stamp = None
        candidate_stamp = old_stamp
        for issue in parsed:
            new_stamp = datetime.datetime.strptime(
                issue["created_at"],
                "%Y-%m-%dT%H:%M:%SZ"
            )
            # print(issue["created_at"], stamp, " | ", old_stamp, new_stamp)
            if new_stamp > old_stamp:
                if new_stamp > candidate_stamp:
                    candidate_stamp = new_stamp
                    latest_stamp = issue["created_at"]
                messages.append(self.format_issue_message(issue))

        if latest_stamp:
            stamp = datetime.datetime.strftime(
                datetime.datetime.utcnow(),
                "%Y-%m-%dT%H:%M:%SZ"
            )

        messages.reverse()
        return messages, stamp

    def format_commit_message(self, entry):
        gho = GH_OBJECT.copy()
        gho["type"] = GH_COMMIT
        gho["title"] = entry["title"]
        desc = html2text(entry["summary"]).lstrip()
        desc = desc[desc.find("\n"):len(desc)].rstrip()
        gho["desc"] = desc.lstrip().replace("    ", "")
        gho["url"] = entry["link"]
        gho["author"] = entry["author"]
        if "href" in entry["author_detail"]:
            gho["author_url"] = entry["author_detail"]["href"]
        gho["avatar_icon_url"] = entry["media_thumbnail"][0]["url"]
        gho["repository"] = entry["link"].split("/")[-3]

        return gho

    def format_issue_message(self, e):
        gho = GH_OBJECT.copy()
        try:
            e["pull_request"]
        except KeyError:
            gho["type"] = GH_ISSUE
        else:
            gho["type"] = GH_PR
        gho["issue_number"] = "#" + str(e["number"])
        gho["author"] = e["user"]["login"]
        gho["author_url"] = e["user"]["html_url"]
        gho["avatar_icon_url"] = e["user"]["avatar_url"] + "&s=32"
        gho["url"] = e["html_url"]
        gho["title"] = e["title"]
        desc = e["body"].lstrip().replace("\r", "").rstrip().replace("    ", "")
        gho["desc"] = desc
        gho["repository"] = e["repository_url"].split("/")[-1]
        return gho

    def format_qa_message(self, thread):
        gho = GH_OBJECT.copy()
        gho["type"] = GH_QA
        gho["title"] = thread["title"]
        gho["url"] = thread["link"]
        gho["repository"] = thread["category"]
        return gho

    def format_forum_message(self, thread):
        gho = GH_OBJECT.copy()
        gho["type"] = GH_FORUM
        gho["title"] = thread["title"]
        gho["desc"] = html2text(thread["description"])
        gho["url"] = thread["link"]
        gho["author"] = thread["author"]
        gho["repository"] = thread["category"]

        return gho

if __name__ == "__main__":
    # For testing
    from time import sleep
    f = RSSFeed()
    f.issue_url = "https://api.github.com/repos/godotengine/godot/issues?sort=created"
    m, s = f.check_issue("2017-02-01T05:57:28Z")
    for gh in m:
        print("#################################")
        print(gh)
    d = feedparser.parse("https://github.com/godotengine/godot/commits/master.atom")
    d = d["items"][1]
    print(f.format_commit_message(d))
    d = feedparser.parse("https://godotdevelopers.org/forum/discussions/feed.rss")
    for t in d["items"][:5]:
        print(f.format_forum_message(t))

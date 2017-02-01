from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

mls = MLStripper()
mls.feed("""
&lt;pre style=&#39;white-space:pre-wrap;width:81ex&#39;&gt;Merge pull request #7680 from cbscribe/master

grammar fixes, it&amp;#39;s -&amp;gt; its
[ci skip]&lt;/pre&gt;
""")
print(mls.get_data())
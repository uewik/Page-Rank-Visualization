import sqlite3
import urllib
from urlparse import urljoin
from urlparse import urlparse
from BeautifulSoup import *

conn = sqlite3.connect('spider.sqlite')
cur = conn.cursor()
cur.execute(''' CREATE TABLE IF NOT EXISTS Pages
    (id INTEGER PRIMARY KEY, url TEXT UNIQUE, html TEXT,
     error INTEGER, old_rank REAL, new_rank REAL)''')
cur.execute(''' CREATE TABLE IF NOT EXISTS Links
    (from_id INTEGER, to_id INTEGER)''')
cur.execute(''' CREATE TABLE IF NOT EXISTS Webs (url TEXT UNIQUE)''')
#check to see if we are already in progress..
cur.execute('SELECT id, url FROM Pages WHERE html IS NULL AND error IS NULL ORDER BY RANDOM() LIMIT 1')
row = cur.fetchone()
if row is not None:
    print "Restarting existing crawl.  Remove spider.sqlite to start a fresh crawl."
else:
    starturl = raw_input("Enter web url: ")
    # After input url in terminal, press Enter anywhere not around url
    if len(starturl) < 1: starturl = 'http://python-data.dr-chuck.net/'
    if starturl.endswith('/'):  starturl = starturl[:-1]
    web = starturl
    if starturl.endswith('.htm') or starturl.endswith('.html'):
        pos = starturl.rfind('/');
        web = starturl[:pos]
    if len(web) > 1:
        cur.execute('INSERT OR IGNORE INTO Webs (url) VALUES (?)', (web, ))
        cur.execute('INSERT OR IGNORE INTO Pages (url, html, new_rank) VALUES (?, NULL, 1.0)', (web, ))
cur.execute('SELECT url FROM Webs')
webs = []
for row in cur:
    webs.append(str(row[0]))
print webs
many = 0
while True:
    if many < 1:
        sval = raw_input("How many pages: ")
        if len(sval) < 1: break
        many = int(sval)
    many = many - 1
    cur.execute('SELECT id, url FROM Pages WHERE html IS NULL AND error IS NULL ORDER BY RANDOM() LIMIT 1')
    try:
        row = cur.fetchone()
        fromid = row[0]
        url = row[1]
    except:
        print "No unretrieved HTML pages found"
        many = 0;
        break
    print fromid, url
    cur.execute('DELETE FROM Links WHERE from_id = ?', (fromid, ))  # Just make sure
    try:
        document = urllib.urlopen(url)
        html = document.read()
        if document.getcode() != 200:
            print "Error on Page: ",document.getcode()
            cur.execute('UPDATE Pages SET error = ? WHERE url = ?', (document.getcode(), url))
            cur.commit()    # added
        if 'text/html' != document.info().gettype():
            print "Ignore non text/html page"
            cur.execute('UPDATE Pages SET error = -1 WHERE url = ?', (url,))
            cur.commit()
            continue
        print "("+ str(len(html)) +")"
        soup = BeautifulSoup(html)
    except KeyboardInterrupt:
        print ""
        print "Program interrupted by user..."
        break
    except:
        print "Unable to retrieve or parse page"
        cur.execute('UPDATE Pages SET error = -1 WHERE url = ?', (url ,))
        conn.commit()
        continue
    # cur.execute('INSERT OR IGNORE INTO Pages (url, html, new_rank) VALUES ( ?, NULL, 1.0 )', (url,))
    cur.execute('UPDATE Pages SET html = ? WHERE url = ?', (buffer(html), url))

    # Retrieve all of the anchor tags
    tags = soup('a')
    count = 0
    for tag in tags:
        href = tag.get('href', None)
        if href is None: continue
        # Resolve relative references like href="/contact"
        up = urlparse(href)
        if ( len(up.scheme) < 1 ) :
            href = urljoin(url, href)
        ipos = href.find('#')
        if ( ipos > 1 ) : href = href[:ipos]
        if ( href.endswith('.png') or href.endswith('.jpg') or href.endswith('.gif') ) : continue
        if ( href.endswith('/') ) : href = href[:-1]
        if ( len(href) < 1 ) : continue
        # Check if the URL is in any of the webs
        found = False
        for web in webs:
            if href.startswith(web):
                found = True
                break
        if not found: continue
        cur.execute('INSERT OR IGNORE INTO Pages(url, html, new_rank) VALUES (?, NULL, 1.0)', (href, ))
        count = count + 1
        conn.commit()
        cur.execute('SELECT id FROM Pages WHERE url = ? LIMIT 1', (href, ))
        try:
            row = cur.fetchone()
            toid = row[0]
        except:
            print "Could not retrive id"
            continue
        cur.execute('INSERT OR IGNORE INTO Links (from_id, to_id) VALUES (?, ?)', (fromid, toid))
    print count
cur.close()




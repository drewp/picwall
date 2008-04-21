from  RSS import CollectionChannel, ns as RSS_NS
from twisted.web.client import getPage
from twisted.internet.defer import Deferred, succeed
import os, re, sys
from PIL import Image
from StringIO import StringIO

def RSS(name):
    return (RSS_NS.rss10, name)

class ThumbImage(object):
    """image data that loads first as a thumbnail, then if requested,
    as a full-size image"""
    def __init__(self, thumbUrl, fullUrl):
        self.thumbUrl, self.fullUrl = thumbUrl, fullUrl
        self.data = {} # size : deferred or data

    def getDeferred(self, size='thumb'):
        """returns deferred to the image data"""
        url = getattr(self, "%sUrl" % size)
        if url.startswith("file://"):
            return succeed(open(url[len("file://"):]).read())
        print "fetching", url
        d = getPage(url)
        d.addErrback(lambda e: [sys.stderr.write(str(e)), sys.stderr.flush()])
        return d

    def getData(self, size='thumb'):
        """returns data or None if data isn't loaded yet"""
        ret = self.data.get(size, None)
        if isinstance(ret, Deferred):
            # this test makes a race condition between the two
            # callbacks. The deferred and compressed data ought to go
            # to a different variable altogether
            return None
        if ret is None:
            d = self.data[size] = self.getDeferred(size)
            d.addCallback(self.decompress)
            d.addCallback(lambda data: self.data.__setitem__(size, data))
            return None
        return ret

    def decompress(self, jpgData):
        """get the RGB data from the results of the URL.

        (to support multiple img types, this will probably have to
        know more about the content-type from the page fetch)
        """
        f = StringIO(jpgData)
        return Image.open(f).resize((256, 256)).tostring()

def localDir(root):
    for fn in os.listdir(root):
        filename = os.path.abspath(os.path.join(root, fn))
        img = ThumbImage("file://%s" % filename, # should be in .thumbnails
                         "file://%s" % filename)
        yield img

def flickrImages(rssUrl="file:///home/drewp/projects/picwall/jimmm-sample.rss"):
    """yield ThumbImage objs from a flickr rss feed"""
    
    chan = CollectionChannel()
    chan.parse()
    # python -c "from xml.sax.sax2exts import XMLParserFactory as X; print X.get_parser_list()"
    #['xml.sax.drivers2.drv_pyexpat', 'xml.sax.drivers2.drv_xmlproc']

    for i in chan.listItems():
        item = chan.getItem(i)
        desc = item[('http://purl.org/rss/1.0/', u'description')]
        m = re.search(r"(http://.*_m.jpg)", desc)
        yield ThumbImage(m.groups(1),
                         m.groups(1) # should be the bigger version
                         )

# flickr result rss. _m is ok for thumb size. roughly 20k, width=240
{
 ('http://purl.org/rss/1.0/', u'description'):
 '<p><a href="http://www.flickr.com/people/purp/">jimmm</a> posted a photo:</p>\n<p>'
 '<a href="http://www.flickr.com/photos/purp/1063295280/" title="HPIM2240.JPG">'
 '<img src="http://farm2.static.flickr.com/1235/1063295280_16f8627d4b_m.jpg" width="180" height="240" alt="HPIM2240.JPG" /></a></p>',
 
 ('http://purl.org/rss/1.0/', u'link'): 'http://www.flickr.com/photos/purp/1063295280/',
 ('http://purl.org/rss/1.0/', u'title'): 'HPIM2240.JPG',
 ('http://purl.org/rss/1.0/modules/rss091/', u'author'): 'nobody@flickr.com (jimmm)',
 ('http://purl.org/rss/1.0/modules/rss091/', u'guid'): 'tag:flickr.com,2004:/photo/1063295280',
 ('http://purl.org/rss/1.0/modules/rss091/', u'pubDate'): 'Thu, 9 Aug 2007 10:36:04 -0800',
 (u'http://purl.org/dc/elements/1.1/', u'date.Taken'): '2007-08-04T05:58:55-08:00', (u'http://search.yahoo.com/mrss/', u'content'): '',
 (u'http://search.yahoo.com/mrss/', u'category'): 'nc barcamprdu',
 (u'http://search.yahoo.com/mrss/', u'credit'): 'jimmm',
 (u'http://search.yahoo.com/mrss/', u'thumbnail'): '',
 (u'http://search.yahoo.com/mrss/', u'title'): 'HPIM2240.JPG',
 }

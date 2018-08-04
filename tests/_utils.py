# coding: utf-8

from six.moves.urllib.request import urlopen
from fs.wrapfs import WrapFS


class HTTPDownloader(WrapFS):

    def openbin(self, path, mode='r', buffering=-1, **options):
        ftpfs, path = self.delegate_fs().delegate_path(path)
        http_url = "http://{}/{}".format(ftpfs.host, path)
        return urlopen(http_url)

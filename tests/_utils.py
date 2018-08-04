# coding: utf-8

from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import quote
from fs.wrapfs import WrapFS


class HTTPDownloader(WrapFS):
    """An `FTPFS` wrapper that downloads files using HTTP.
    """

    def openbin(self, path, mode='r', buffering=-1, **options):
        ftpfs, path = self.delegate_fs().delegate_path(path)
        http_url = "http://{}/{}".format(ftpfs.host, quote(path))
        return urlopen(http_url)

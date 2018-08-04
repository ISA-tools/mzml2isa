# coding: utf-8

import urllib.request

from fs.wrapfs import WrapFS


class HTTPDownloader(WrapFS):

    def openbin(self, path, mode='r', buffering=-1, **options):
        ftpfs, path = self.delegate_fs().delegate_path(path)
        http_url = "http://{}/{}".format(ftpfs.host, path)
        return urllib.request.urlopen(http_url)

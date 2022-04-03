#!/usr/bin/env python
"""
SocksiPy + urllib2 handler

version: 0.3
author: e<e@tr0ll.in>

This module provides a Handler which you can use with urllib2 to allow it to tunnel your connection through a socks.sockssocket socket, with out monkey patching the original socket...
"""
import ssl

try:
    import urllib.request, urllib.error, urllib.parse
    import http.client
except ImportError: # Python 3
    import urllib.request as urllib2
    from http import client as httplib

from . import socks # $ pip install PySocks

def merge_dict(a, b):
    d = a.copy()
    d.update(b)
    return d

class SocksiPyConnection(http.client.HTTPConnection):
    def __init__(self, proxytype, proxyaddr, proxyport=None, rdns=True, username=None, password=None, *args, **kwargs):
        self.proxyargs = (proxytype, proxyaddr, proxyport, rdns, username, password)
        http.client.HTTPConnection.__init__(self, *args, **kwargs)

    def connect(self):
        self.sock = socks.socksocket()
        self.sock.setproxy(*self.proxyargs)
        if type(self.timeout) in (int, float):
            self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))

class SocksiPyConnectionS(http.client.HTTPSConnection):
    def __init__(self, proxytype, proxyaddr, proxyport=None, rdns=True, username=None, password=None, *args, **kwargs):
        self.proxyargs = (proxytype, proxyaddr, proxyport, rdns, username, password)
        http.client.HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self):
        sock = socks.socksocket()
        sock.setproxy(*self.proxyargs)
        if type(self.timeout) in (int, float):
            sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file)

class SocksiPyHandler(urllib.request.HTTPHandler, urllib.request.HTTPSHandler):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kw = kwargs
        urllib.request.HTTPHandler.__init__(self)

    def http_open(self, req):
        def build(host, port=None, timeout=0, **kwargs):
            kw = merge_dict(self.kw, kwargs)
            conn = SocksiPyConnection(*self.args, host=host, port=port, timeout=timeout, **kw)
            return conn
        return self.do_open(build, req)

    def https_open(self, req):
        def build(host, port=None, timeout=0, **kwargs):
            kw = merge_dict(self.kw, kwargs)
            conn = SocksiPyConnectionS(*self.args, host=host, port=port, timeout=timeout, **kw)
            return conn
        return self.do_open(build, req)

if __name__ == "__main__":
    import sys
    try:
        port = int(sys.argv[1])
    except (ValueError, IndexError):
        port = 9050
    opener = urllib.request.build_opener(SocksiPyHandler(socks.PROXY_TYPE_SOCKS5, "localhost", port))
    print(("HTTP: " + opener.open("http://httpbin.org/ip").read().decode()))
    print(("HTTPS: " + opener.open("https://httpbin.org/ip").read().decode()))

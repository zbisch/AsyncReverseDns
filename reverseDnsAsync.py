from twisted.internet import reactor
from twisted.web.client import getPage
from twisted.internet import defer, task
from twisted.names import client

from collections import defaultdict

import twisted
import itertools
import sys, time
import IPy

class ReverseDNSer():
    def __init__(self, ips, maxRunning=1000, timeouts=[3, 3, 10]):
        self.ips = ips
        self.successes = 0
        self.failures = 0
        self.maxRunning = maxRunning
        self.timeouts = timeouts
        self.ipsToNames = {}
        self.errorCounters = defaultdict(lambda : defaultdict(int))

    def _lookupSuccess(self, (ans, auth, add), addr):
        if len(ans) == 0:
            self.failures += 1
            return

        self.ipsToNames[addr] = str(ans[0].payload.name)
        self.successes += 1 

    def _lookupError(self, failure, addr):
        self.failures += 1
        r = failure.trap(twisted.names.error.DNSNameError, 
                twisted.names.error.DNSServerError,
                twisted.internet.defer.TimeoutError,
                twisted.internet.error.ConnectionLost)
        self.errorCounters[r][addr] += 1

    def _taskGenerator(self):
        for ip in self.ips:
            addr = ip
            ptr = IPy.IP(addr).reverseName()
            d = client.lookupPointer(ptr, timeout=self.timeouts
                        ).addCallback(lambda x, addr=addr: self._lookupSuccess(x, addr)
                        ).addErrback(lambda x, addr=addr: self._lookupError(x, addr))
            yield d

    def _finish(self, ign):
        reactor.stop()

    def loadWork(self):
        deferreds = []
        coop = task.Cooperator()
        self.work = self._taskGenerator()
        for i in xrange(self.maxRunning):
            d = coop.coiterate(self.work)
            deferreds.append(d)
        self.dl = defer.DeferredList(deferreds)
        self.dl.addCallback(self._finish)

    def run(self):
        reactor.run()
        for ip,name in self.ipsToNames.items():
            print repr(ip)+","+repr(name)

if __name__ == "__main__":
    ips = set()
    for line in sys.stdin:
        if line.strip():
            ips.add(line.strip())
    r = ReverseDNSer(ips)
    r.loadWork()
    r.run()

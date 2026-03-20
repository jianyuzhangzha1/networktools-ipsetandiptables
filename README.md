### multiplexing the brook and https based on ipset, with a simple configure portal

The purpose is to allow mobile device to access brook when ip address was chaged during the travelling. If don't place ipatbles to enable whitelist, GFW will ban the ip immediately.
contains three parts:

1 iptables scripts, which redirect the network load from ip where in the predefined ipset from port 443 to port 1080. And maintain the ipset if the network load appeared in the last 5 minutes.

2 a small portal working on 80 port to receive access request and then add the source ip address to ipset, then iptables script can redirect the 443 port to brook proxy.

3 nginx configure files, expose the portal to the main site's url, make it can be accessed by domain.


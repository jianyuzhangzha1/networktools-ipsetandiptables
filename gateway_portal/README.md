### multiplexing the brook and https based on Nftable, with a simple configure portal

The purpose is to allow mobile device to access brook when ip address was chaged during the travelling. If don't place ipatbles to enable whitelist, GFW will ban the ip immediately.
contains three parts:

* 1 Iptables scripts, which redirect the network load from ip where in the predefined ipset from port 443 to port 1080. And maintain the ipset if the network load appeared in the last 5 minutes.

* 2 A small portal working on 80 port to receive access request and then add the source ip address to ipset, then iptables script can redirect the 443 port to brook proxy.

* 3 Nginx configure files, expose the portal to the main site's url, make it can be accessed by domain.


 
 Change logs
 ```
- update 20260320, for ipset and iptables are outaged, move to nftables and ip filter.
- update 20260324, done the nftable porting, deployed to http://www.bamaolog.com/fastapiPortal/
```

TODO:

* 1 Terraform, to support multi-cloud.(Due to the traffic price policy, public cloud provider is more expensive than VPS vendor such as DigitalOcan or Linode, So the multi-cloud is just a fallsafe and enmergency solution)<br>
* 2 IPv6 support

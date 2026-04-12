# project background
I've been using BROOK for network connectivity; as long as it works, that's fine. I use it in conjunction with iptables for proactive detection and blocking. I also set up a simple blog, which can also be used as a cover for proactive detection. My original idea was to create a simple interface that automatically adds legitimate IP addresses accessing web pages to the whitelist, since home dial-up IPs and mobile IPs change while on the go. Whitelisting is difficult to manage in the VPS firewall interface.

### PHRASE ONE
A simple page was implemented based on FastAPI, adding session functionality, basic Q&A, ipset display, and automatic timeout deletion.

### PHRASE TWO
However, during testing on the Raspberry Pi, I discovered that newer distributions are using nftables, which offers better performance and eliminates the need for ipset. So, I decided to switch to nftables. Furthermore, using JSON for interaction is more reliable than command-line text recognition.

### PHRASE THREE
When actually deployed on a VPS, it was found that mobile access resulted in a default IPv6 address. This was somewhat awkward, so further modifications were needed.In April, the Chinese government cracked down on VPNs and found that the Digital Ocean + Brook method was outdated, so they switched to Bandwagon Host and Hysteria2 / Reality.

In April, the Chinese government cracked down on VPNs, finding that the Digital Ocean + Brook combination was outdated. They switched to Bandwagon Host and Hysteria2/Reality. Locally, they used Sing-box for connection, and will continue to experiment with using Mikrotik's OSPF routing for automated client-side traffic routing; as well as adding performance monitoring and network auditing capabilities.

WireGuard VPN @UpCloud -- Notes

⚠️ Server is currently DOWN. Before using any commands/tools here, spin up the
instance at https://hub.upcloud.com/dashboard first.

Using WireGuard as the VPN client
Running VPN as a docker on UpCloud

Link: https://hub.upcloud.com
Username: cibermichi

Account: cibermichi@gmail.com


Ref Videos:
1. https://www.youtube.com/watch?v=G_Pv9XEzfUY
2. https://www.youtube.com/watch?v=R29YBmYxXAk

# Deployment
## Preparation
 - SSH Key must be generated in advance
 (check ~/.ssh)
## Steps
 - Connect to UpCloud
 - Create server in location;
 most basic default config
 - Initialization script "vpn_setup.sh"
 (unless it works automatically):
 - Place the "docker-compose.yaml" file in the new wireguard folder
 - Amend the file accordingly to the current server

 - Connect to the machine with linux terminal and ssh root@94.237.63.49
 - Run docker with:

```sh
# init
 docker-compose up -d
# force start (jic)
 docker-compose start
```

 - Then use "docker-compose logs" to  check the QR or navigate to peer1 to find the cfg file

 - IMPORTANT: Ensure to disable or open the firewall to allow the VPN connection as it uses an unusual port and IP

 - Finally open WireGuard and create a tunnel with the config from the peers generated.

 - Verify with https://iplocation.io/

## IMPROVED:
 - The runs automatically now: 
```sh
#! /bin/sh

cd  /root/wireguard
docker-compose start

exit 0
```

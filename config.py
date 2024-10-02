import os

from secret import server_ip, MAPS_API_KEY

mode = "local"
in_line_server = True

if mode == "local":
    server_ip = "192.168.137.1"

local_gateway = {
    "udp_gateA" : (server_ip, 50001),
    "udp_gateB" : (server_ip, 50002),

    "udp_gateA1": (server_ip, 17102),
    "udp_gateB1":  (server_ip, 50003),

    "tcp_gateA": (server_ip, 10001),
    "tcp_gateB": (server_ip, 10002)
}

video = {
    "height":720,
    "width":1280,
    "framerate": 24
}

video_cmd_datachannel = {
    "remote_host" : (server_ip, 50001)
}

telemetry_datachannel = {
    "remote_host": (server_ip, 50003)
}

tcp_gateA = (server_ip, 10001)
tcp_gateB = (server_ip, 10002)
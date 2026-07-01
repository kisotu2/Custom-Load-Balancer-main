import requests
from consistent_hash import ConsistentHash
from collections import defaultdict

# Map logical server names to their actual ports
servers = {
    "server1": "http://localhost:5001/home",
    "server2": "http://localhost:5002/home",
    "server3": "http://localhost:5003/home",
}

# Initialize scheduler (round robin inside ConsistentHash)
ch = ConsistentHash()
for server in servers.keys():
    ch.add_server(server)

distribution = defaultdict(int)

# Send 1000 requests
for i in range(10000):
    assigned_server = ch.get_server()
    try:
        res = requests.get(servers[assigned_server])
        if res.status_code == 200:
            distribution[assigned_server] += 1
    except Exception:
        print(f"Failed to connect to {assigned_server}")

# Display results
print("\nRequest Distribution:")
for server, count in distribution.items():
    print(f"{server:8}: {count} requests")

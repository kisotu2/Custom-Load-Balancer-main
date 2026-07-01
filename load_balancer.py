from flask import Flask, request, jsonify
import requests
from consistent_hash import ConsistentHash

app = Flask(__name__)


hash_ring = ConsistentHash()


servers = {
    "server1": "http://server1:5000",
    "server2": "http://server2:5000",
    "server3": "http://server3:5000"
}

for server in servers:
    hash_ring.add_server(server)


@app.route("/rep", methods=["GET"])
def replicas():
    return jsonify({
        "message": {
            "N": len(servers),
            "replicas": list(servers.keys())
        },
        "status": "successful"
    }), 200



@app.route("/add", methods=["POST"])
def add_servers():

    data = request.get_json()

    n = data.get("n", 0)
    hostnames = data.get("hostnames", [])

    if len(hostnames) != n:
        return jsonify({
            "message": "Hostnames length must equal n",
            "status": "failure"
        }), 400

    for host in hostnames:

        if host in servers:
            continue

        servers[host] = f"http://{host}:5000"
        hash_ring.add_server(host)

    return jsonify({
        "message": {
            "N": len(servers),
            "replicas": list(servers.keys())
        },
        "status": "successful"
    }), 200



@app.route("/rm", methods=["DELETE"])
def remove_servers():

    data = request.get_json()

    n = data.get("n", 0)
    hostnames = data.get("hostnames", [])

    if hostnames:

        if len(hostnames) != n:
            return jsonify({
                "message": "Hostnames length must equal n",
                "status": "failure"
            }), 400

        for host in hostnames:

            if host in servers:
                hash_ring.remove_server(host)
                servers.pop(host)

    else:

        removable = list(servers.keys())[:n]

        for host in removable:
            hash_ring.remove_server(host)
            servers.pop(host)

    return jsonify({
        "message": {
            "N": len(servers),
            "replicas": list(servers.keys())
        },
        "status": "successful"
    }), 200


@app.route("/home", methods=["GET"])
def home():

    request_id = request.args.get("id", "")

    server = hash_ring.get_server(request_id)

    if server is None:

        return jsonify({
            "message": "No available server",
            "status": "failure"
        }), 500

    try:

        response = requests.get(
            servers[server] + "/home",
            timeout=2
        )

        return jsonify({
            "forwarded_to": server,
            "response": response.json()
        }), response.status_code

    except Exception as e:

        return jsonify({
            "message": str(e),
            "status": "failure"
        }), 500


@app.route("/heartbeat", methods=["GET"])
def heartbeat():
    return jsonify({
        "status": "alive"
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=6000,
        debug=False
    )
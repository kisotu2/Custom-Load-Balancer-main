import os
import uuid
import json
import subprocess
import sys
import traceback
from flask import Flask, request, jsonify

# Import consistent hashing class from Task 2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'custom_hash')))
from consistent_hash import ConsistentHash

app = Flask(__name__)
ch = ConsistentHash()
servers = {}  # container_id → hostname

@app.route('/rep', methods=['GET'])
def replicas():
    return jsonify({
        "message": {
            "N": len(servers),
            "replicas": list(servers.values())
        },
        "status": "successful"
    }), 200

@app.route('/add', methods=['POST'])
def add_servers():
    data = request.get_json()
    n = data.get("n", 0)
    hostnames = data.get("hostnames", [])

    if len(hostnames) > n:
        return jsonify({
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }), 400

    added = []

    for i in range(n):
        name = hostnames[i] if i < len(hostnames) else f"server-{uuid.uuid4().hex[:6]}"
        cmd = f"docker run -d --rm --name {name} -e SERVER_ID={i+1} -p 0:5000 simple-server"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
        container_id = result.stdout.decode().strip()

        if container_id:
            servers[container_id] = name
            ch.add_server(name)
            added.append(name)

    return jsonify({
        "message": {
            "N": len(servers),
            "replicas": list(servers.values())
        },
        "status": "successful"
    }), 200

@app.route('/rm', methods=['DELETE'])
def remove_servers():
    data = request.get_json()
    n = data.get("n", 0)
    hostnames = data.get("hostnames", [])

    if len(hostnames) > n:
        return jsonify({
            "message": "<Error> Length of hostname list is more than removable instances",
            "status": "failure"
        }), 400

    removed = []

    if hostnames:
        for h in hostnames:
            cid = next((k for k, v in servers.items() if v == h), None)
            if cid:
                subprocess.run(f"docker stop {h}", shell=True)
                ch.remove_server(h)
                removed.append(servers.pop(cid))
    else:
        to_remove = list(servers.items())[:n]
        for cid, h in to_remove:
            subprocess.run(f"docker stop {h}", shell=True)
            ch.remove_server(h)
            removed.append(servers.pop(cid))

    return jsonify({
        "message": {
            "N": len(servers),
            "replicas": list(servers.values())
        },
        "status": "successful"
    }), 200

@app.route('/home', methods=['GET'])
def route_request():
    req_id = request.args.get("id", "")
    target_server = ch.get_server(req_id)

    if not target_server:
        return jsonify({
            "message": "<Error> No server found to handle this request",
            "status": "failure"
        }), 400

    # Find container ID and get port
    cid = next((k for k, v in servers.items() if v == target_server), None)
    if not cid:
        return jsonify({
            "message": "<Error> Target container not found",
            "status": "failure"
        }), 404

    try:
        inspect_cmd = [
            "docker", "inspect", cid,
            "--format", "{{(index (index .NetworkSettings.Ports \"5000/tcp\") 0).HostPort}}"
        ]
        port = subprocess.check_output(inspect_cmd).decode().strip()

        import requests
        res = requests.get(f"http://localhost:{port}/home", timeout=2)

        return jsonify({
            "forwarded_to": target_server,
            "handled_by_container": cid,
            "container_response": res.json()
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "message": f"<Error> {str(e)}",
            "status": "failure"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)

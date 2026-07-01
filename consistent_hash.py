import re
from collections import Counter

class ConsistentHash:
    def __init__(self, total_slots=512, num_virtual=9):
        self.total_slots = total_slots
        self.num_virtual = num_virtual
        self.servers = {}  # {slot: server_name}
        self.virtual_servers = {}  # {server_name: [virtual_slots]}
        self.round_robin_order = []  # [server1, server2, ...]
        self.rr_index = 0

    def hash_request(self, request_id):
        """Hash function for requests: H(i) = i^2 + 2i + 17 mod M"""
        if isinstance(request_id, str):
            i = sum(ord(c) for c in request_id)
        else:
            i = int(request_id)
        return (i**2 + 2*i + 17) % self.total_slots

    def hash_virtual_server(self, server_name, replica_idx):
        """Hash function for virtual server: Φ(i,j) = i^2 + j^2 + 2j + 25 mod M"""
        match = re.search(r'\d+', server_name)
        if not match:
            raise ValueError(f"No numeric ID found in server name '{server_name}'")
        i = int(match.group())  # Extract numeric part from server name
        j = replica_idx
        return (i**2 + j**2 + 2*j + 25) % self.total_slots

    def add_server(self, server_name):
        """Adds a physical server with its virtual replicas into the hash ring."""
        virtual_slots = []
        for j in range(self.num_virtual):
            slot = self.hash_virtual_server(server_name, j)
            original_slot = slot
            while slot in self.servers:
                slot = (slot + 1) % self.total_slots
                if slot == original_slot:
                    raise Exception("Hash ring is full.")
            self.servers[slot] = server_name
            virtual_slots.append(slot)
        self.virtual_servers[server_name] = virtual_slots

        if server_name not in self.round_robin_order:
            self.round_robin_order.append(server_name)

    def remove_server(self, server_name):
        """Removes a physical server and its virtual replicas from the hash ring."""
        for slot in self.virtual_servers.get(server_name, []):
            if slot in self.servers:
                del self.servers[slot]
        self.virtual_servers.pop(server_name, None)

        if server_name in self.round_robin_order:
            self.round_robin_order.remove(server_name)
            self.rr_index %= max(len(self.round_robin_order), 1)

    def get_server(self, request_id=None):
        """Returns the next server in round-robin order"""
        if not self.round_robin_order:
            return None
        server = self.round_robin_order[self.rr_index]
        self.rr_index = (self.rr_index + 1) % len(self.round_robin_order)
        return server

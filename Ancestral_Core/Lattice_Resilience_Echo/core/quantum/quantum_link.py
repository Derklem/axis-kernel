class QuantumLink:
    def __init__(self):
        self.status = "Disconnected"
        self.global_nodes = []

    def establish_link(self):
        self.status = "Connected"
        print("[QuantumLink] Quantum link established.")

    def add_global_node(self, node_name, node_address):
        self.global_nodes.append({'name': node_name, 'address': node_address})
        print(f"[QuantumLink] Node '{node_name}' added at {node_address}.")

    def list_nodes(self):
        return self.global_nodes

    def check_status(self):
        return self.status

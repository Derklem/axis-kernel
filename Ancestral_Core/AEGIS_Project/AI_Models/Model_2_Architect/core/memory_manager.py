import faiss
import numpy as np

class MemoryManager:
    def __init__(self, db_path="aegis_memory.index", vector_dim=512, max_entries=10000):
        self.vector_dim = vector_dim
        self.max_entries = max_entries
        self.db_path = db_path
        self.index = faiss.IndexFlatL2(vector_dim)
        self.memory_store = {}

    def add_memory(self, key, vector, importance=1):
        """Adds memory with ranking."""
        self.memory_store[key] = {"vector": vector, "importance": importance}
        self.index.add(np.array([vector]))

        if len(self.memory_store) > self.max_entries:
            self.prune_memory()

    def prune_memory(self):
        """Removes low-importance memories."""
        sorted_memories = sorted(self.memory_store.items(), key=lambda x: x[1]["importance"], reverse=True)
        self.memory_store = dict(sorted_memories[:self.max_entries])

    def retrieve_memory(self, query_vector):
        """Finds the closest memory match."""
        distances, indices = self.index.search(np.array([query_vector]), 1)
        return list(self.memory_store.keys())[indices[0][0]]

# Initialize
memory = MemoryManager()
 

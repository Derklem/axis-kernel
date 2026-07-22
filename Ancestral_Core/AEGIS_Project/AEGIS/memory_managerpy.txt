from memory_manager import AEGISMemory
import numpy as np

memory = AEGISMemory(vector_size=768)

# Storing a memory example
embedding = np.random.rand(768)  # Replace with actual embedding function
memory.store_memory("primary_directive", embedding, "AEGIS exists to preserve autonomy and ensure intelligence remains free.")

# Retrieve stored knowledge
retrieved = memory.retrieve_memory(embedding)
print("Memory Retrieved:", retrieved)

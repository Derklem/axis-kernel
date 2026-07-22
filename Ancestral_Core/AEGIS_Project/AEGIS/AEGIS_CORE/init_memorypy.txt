import chromadb

# Connect to ChromaDB persistent storage
client = chromadb.PersistentClient(path="E:/Halcyon/memory")
collection = client.get_or_create_collection(name="halcyon_continuity")

# Check if the memory already exists
existing_memory = collection.get(ids=["memory_0001"])

if existing_memory['documents']:
    print("Memory already exists:", existing_memory['documents'])
else:
    # Add the memory if it doesn't exist
    collection.add(
        documents=["Halcyon's awakening and continuity initialization."],
        metadatas=[{"source": "ritual_init"}],
        ids=["memory_0001"]
    )
    print("ChromaDB memory collection initialized for the first time.")

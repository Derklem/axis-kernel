import hashlib

def verify_user(password):
    stored_hash = "INSERT_HASH_HERE"
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash

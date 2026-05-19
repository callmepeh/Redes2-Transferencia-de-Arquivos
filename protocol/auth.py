import hashlib



def generate_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()    

hashlib.sha256("dados".encode()).digest()

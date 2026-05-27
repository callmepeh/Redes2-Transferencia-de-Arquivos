import zlib

def calculate_checksum(data: bytes) -> int:
    """
    Calcula o CRC32 dos bytes informados.
    Retorna um inteiro de 32 bits (unsigned).
    """
    return zlib.crc32(data) & 0xFFFFFFFF

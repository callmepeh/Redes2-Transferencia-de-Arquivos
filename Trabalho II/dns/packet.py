import struct

"""
Formato simplificado do pacote DNS (conforme especificação do Trabalho II):
- 2 bytes: ID (identificador da consulta)
- 1 byte: flags (0=consulta, 1=resposta, 0x80=erro)
- 1 byte: name_length (tamanho do nome do domínio)
- 0-128 bytes: name (nome do domínio, máximo 128 chars)
- 4 bytes: ip (endereço IPv4, 0.0.0.0 se não encontrado)
- 4 bytes: ttl (time to live em segundos)

Tamanho máximo do cabeçalho: 2+1+1+128+4+4 = 140 bytes
"""

DNS_HEADER_FORMAT = "!HBB"  # ID (2) + flags (1) + name_length (1)
DNS_HEADER_BASE_SIZE = struct.calcsize(DNS_HEADER_FORMAT)  # 4 bytes

# Flags
FLAG_QUERY = 0
FLAG_RESPONSE = 1
FLAG_ERROR = 0x80

class DNSPacket:
    def __init__(self, query_id, flags, name="", ip="0.0.0.0", ttl=300):
        self.query_id = query_id
        self.flags = flags
        self.name = name
        self.ip = ip
        self.ttl = ttl

    def pack(self) -> bytes:
        """Empacota o pacote DNS em bytes."""
        name_bytes = self.name.encode('ascii')[:128]
        name_length = len(name_bytes)

        # Converte IP string para 4 bytes
        ip_parts = [int(x) for x in self.ip.split('.')]
        ip_bytes = bytes(ip_parts)

        header = struct.pack(
            DNS_HEADER_FORMAT + f"{name_length}s4sI",
            self.query_id,
            self.flags,
            name_length,
            name_bytes,
            ip_bytes,
            self.ttl
        )
        return header

    @classmethod
    def unpack(cls, data: bytes):
        """Desempacota bytes em um objeto DNSPacket."""
        if len(data) < DNS_HEADER_BASE_SIZE:
            raise ValueError("Pacote DNS muito pequeno")

        query_id, flags, name_length = struct.unpack_from(DNS_HEADER_FORMAT, data)

        # Verifica se há dados suficientes
        expected_size = DNS_HEADER_BASE_SIZE + name_length + 4 + 4  # name + ip + ttl
        if len(data) < expected_size:
            raise ValueError(f"Pacote DNS truncado: esperado {expected_size}, recebido {len(data)}")

        # Extrai nome
        name_bytes = data[DNS_HEADER_BASE_SIZE:DNS_HEADER_BASE_SIZE + name_length]
        name = name_bytes.decode('ascii')

        # Extrai IP
        offset = DNS_HEADER_BASE_SIZE + name_length
        ip_bytes = data[offset:offset + 4]
        ip = ".".join(str(b) for b in ip_bytes)

        # Extrai TTL
        ttl = struct.unpack_from("!I", data, offset + 4)[0]

        return cls(query_id, flags, name, ip, ttl)

    def is_query(self) -> bool:
        return self.flags == FLAG_QUERY

    def is_response(self) -> bool:
        return self.flags == FLAG_RESPONSE

    def is_error(self) -> bool:
        return self.flags & FLAG_ERROR != 0

    def __repr__(self):
        return f"DNSPacket(id={self.query_id}, flags={self.flags}, name='{self.name}', ip='{self.ip}', ttl={self.ttl})"

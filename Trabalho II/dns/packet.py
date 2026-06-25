import struct

"""
Formato do pacote DNS padrão (RFC 1035).

Cabeçalho (12 bytes):
  - 2 bytes: ID (identificador da consulta)
  - 2 bytes: Flags (QR, Opcode, AA, TC, RD, RA, Z, RCODE)
  - 2 bytes: QDCOUNT (número de perguntas)
  - 2 bytes: ANCOUNT (número de respostas)
  - 2 bytes: NSCOUNT (número de registros de autoridade)
  - 2 bytes: ARCOUNT (número de registros adicionais)

Seção de Pergunta (variável):
  - QNAME: nome codificado em labels com prefixo de tamanho
  - 2 bytes: QTYPE (1 = A)
  - 2 bytes: QCLASS (1 = IN)

Seção de Resposta (variável, apenas em respostas):
  - NAME: pointer (0xC00C) para o nome na pergunta
  - 2 bytes: TYPE (1 = A)
  - 2 bytes: CLASS (1 = IN)
  - 4 bytes: TTL
  - 2 bytes: RDLENGTH
  - 4 bytes: RDATA (endereço IPv4)

Referência: RFC 1035 - https://datatracker.ietf.org/doc/html/rfc1035
"""

# Flags DNS
# Query: QR=0, RD=1
FLAG_QUERY = 0x0100
# Response: QR=1, AA=1, RD=1, RA=1
FLAG_RESPONSE = 0x8580
# Response with error (NXDOMAIN): QR=1, AA=1, RD=1, RA=1, RCODE=3
FLAG_ERROR = 0x0003

# Tipos e classes
QTYPE_A = 1
QCLASS_IN = 1

DNS_HEADER_FORMAT = "!HHHHHH"
DNS_HEADER_SIZE = struct.calcsize(DNS_HEADER_FORMAT)  # 12 bytes


def encode_dns_name(name: str) -> bytes:
    """
    Codifica um nome de domínio no formato DNS (labels com prefixo de tamanho).

    Exemplo:
        "servidor.local" -> b'\\x09servidor\\x05local\\x00'
    """
    if not name:
        return b"\x00"

    encoded = b""
    labels = name.split(".")
    for label in labels:
        label_bytes = label.encode('ascii', errors='replace')
        if len(label_bytes) > 63:
            raise ValueError(f"Label DNS muito longa: '{label}' ({len(label_bytes)} > 63)")
        encoded += bytes([len(label_bytes)]) + label_bytes
    encoded += b"\x00"  # Root label (terminador)
    return encoded


def decode_dns_name(data: bytes, offset: int) -> tuple[str, int]:
    """
    Decodifica um nome de domínio no formato DNS (labels com prefixo de tamanho).

    Suporta pointers de compressão (0xC0 + 14-bit offset) conforme RFC 1035.

    Retorna:
        tuple[str, int]: (nome_do_dominio, novo_offset)
    """
    labels = []
    jumped = False
    original_offset = offset

    while True:
        if offset >= len(data):
            raise ValueError("Pacote DNS truncado ao ler nome")

        length = data[offset]

        # Label de comprimento zero = fim do nome
        if length == 0:
            if not jumped:
                offset += 1
            break

        # Pointer de compressão (0xC0 prefix)
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                raise ValueError("Pacote DNS truncado no pointer de compressão")
            pointer = struct.unpack_from("!H", data, offset)[0]
            pointer &= 0x3FFF  # Remove os bits 0xC0

            if not jumped:
                original_offset = offset + 2
                jumped = True

            offset = pointer
            continue

        offset += 1
        if offset + length > len(data):
            raise ValueError(f"Pacote DNS truncado: label de {length} bytes no offset {offset - 1}")

        label = data[offset:offset + length].decode('ascii', errors='replace')
        labels.append(label)
        offset += length

    # Se houve jump, o próximo campo está APÓS o pointer (não após o label)
    if jumped:
        offset = original_offset

    return ".".join(labels), offset


class DNSPacket:
    """
    Pacote DNS compatível com RFC 1035.

    Suporta consultas e respostas do tipo A (IPv4).
    """

    def __init__(self, query_id: int, flags: int, name: str = "",
                 ip: str = "0.0.0.0", ttl: int = 300):
        self.query_id = query_id
        self.flags = flags
        self.name = name
        self.ip = ip
        self.ttl = ttl

    def pack(self) -> bytes:
        """
        Empacota o pacote DNS em bytes (formato RFC 1035).

        Para consultas (QR=0):
            Header + Question Section (QNAME + QTYPE + QCLASS)

        Para respostas (QR=1):
            Header + Question Section + Answer Section (NAME ptr + TYPE + CLASS + TTL + RDLENGTH + RDATA)
        """
        is_response = not self.is_query()

        # Contagem de registros
        qdcount = 1  # Sempre 1 pergunta
        ancount = 1 if (is_response and self.ip != "0.0.0.0") else 0

        header = struct.pack(
            DNS_HEADER_FORMAT,
            self.query_id,
            self.flags,
            qdcount,
            ancount,
            0,  # NSCOUNT
            0,  # ARCOUNT
        )

        # --- Question Section ---
        qname = encode_dns_name(self.name)
        question = qname + struct.pack("!HH", QTYPE_A, QCLASS_IN)

        # --- Answer Section (apenas em respostas) ---
        if ancount > 0:
            # Pointer de compressão para o QNAME
            # 0xC00C = 0xC000 | 12 → aponta para offset 12 (início da seção de pergunta,
            # que fica imediatamente após o header de 12 bytes)
            answer_name = struct.pack("!H", 0xC00C)

            # Converte IP string para 4 bytes
            ip_parts = [int(x) for x in self.ip.split('.')]

            answer = answer_name + struct.pack(
                "!HHIH",
                QTYPE_A,    # TYPE = 1 (A record)
                QCLASS_IN,  # CLASS = 1 (IN)
                self.ttl,   # TTL
                4,          # RDLENGTH = 4 bytes para IPv4
            ) + bytes(ip_parts)
        else:
            answer = b""

        return header + question + answer

    @classmethod
    def unpack(cls, data: bytes):
        """
        Desempacota bytes em um objeto DNSPacket (formato RFC 1035).

        Lê o header, a seção de pergunta e, se houver, a seção de resposta.
        """
        if len(data) < DNS_HEADER_SIZE:
            raise ValueError(f"Pacote DNS muito pequeno: {len(data)} bytes (mínimo: {DNS_HEADER_SIZE})")

        query_id, flags, qdcount, ancount, nscount, arcount = \
            struct.unpack_from(DNS_HEADER_FORMAT, data)

        offset = DNS_HEADER_SIZE

        # --- Decodifica a pergunta ---
        if qdcount < 1:
            raise ValueError("Pacote DNS sem seção de pergunta")

        # Lê o QNAME
        try:
            name, offset = decode_dns_name(data, offset)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Erro ao decodificar nome DNS: {e}")

        # Pula QTYPE (2) + QCLASS (2)
        if offset + 4 > len(data):
            raise ValueError("Pacote DNS truncado: faltam QTYPE/QCLASS")
        offset += 4

        # --- Decodifica a resposta (se houver) ---
        ip = "0.0.0.0"
        ttl = 300

        if ancount > 0:
            # Lê o NAME da resposta (pode ser pointer de compressão de 2 bytes)
            if offset >= len(data):
                raise ValueError("Pacote DNS truncado: faltam registros de resposta")

            name_first_byte = data[offset]
            if name_first_byte & 0xC0 == 0xC0:
                # Pointer name → 2 bytes
                if offset + 2 > len(data):
                    raise ValueError("Pacote DNS truncado no pointer do nome da resposta")
                offset += 2
            else:
                # Nome completo → decodifica
                _, offset = decode_dns_name(data, offset)

            # Lê TYPE (2) + CLASS (2) + TTL (4) + RDLENGTH (2) = 10 bytes
            if offset + 10 > len(data):
                raise ValueError("Pacote DNS truncado: faltam campos do registro de resposta")

            rtype, rclass, ttl_rec, rdlength = struct.unpack_from("!HHiH", data, offset)
            offset += 10

            _ = rtype   # Deveria ser QTYPE_A (1)
            _ = rclass  # Deveria ser QCLASS_IN (1)

            # Lê RDATA (endereço IPv4)
            if rdlength >= 4 and offset + 4 <= len(data):
                ip_bytes = data[offset:offset + 4]
                ip = ".".join(str(b) for b in ip_bytes)
            elif rtype == QTYPE_A and rdlength == 4:
                raise ValueError("Pacote DNS truncado: faltam dados do endereço IP")

            ttl = ttl_rec

        return cls(query_id, flags, name.lower(), ip, ttl)

    def is_query(self) -> bool:
        """Retorna True se for uma consulta (QR=0)."""
        return (self.flags & 0x8000) == 0

    def is_response(self) -> bool:
        """Retorna True se for uma resposta (QR=1)."""
        return (self.flags & 0x8000) != 0

    def is_error(self) -> bool:
        """Retorna True se o código de resposta (RCODE) indicar erro."""
        return (self.flags & 0x000F) != 0

    def __repr__(self):
        return (f"DNSPacket(id={self.query_id}, flags=0x{self.flags:04x}, "
                f"name='{self.name}', ip='{self.ip}', ttl={self.ttl})")

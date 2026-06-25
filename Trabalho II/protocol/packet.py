import struct
from protocol.auth import get_auth_hash
from protocol.checksum import calculate_checksum

# Estrutura do Cabeçalho R-UDP
# 14 bytes: label (b"X-Custom-Auth:")
# 64 bytes: hash SHA-256 hex string
# 4 bytes: seq_num (unsigned int)
# 4 bytes: ack_num (unsigned int)
# 1 byte: flags (0=DATA, 1=ACK, 2=FIN)
# 2 bytes: payload_size (unsigned short)
# 4 bytes: checksum (unsigned int)

HEADER_FORMAT = "!14s64sIIBHI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_PAYLOAD_SIZE = 1024

# Flags
FLAG_DATA = 0
FLAG_ACK = 1
FLAG_FIN = 2

class RUDP_Packet:
    def __init__(self, seq_num, ack_num, flags, payload=b""):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.payload = payload
        
        self.auth_label = b"X-Custom-Auth:"
        self.auth_hash = get_auth_hash().encode('ascii')
        self.payload_size = len(payload)
        self.checksum = 0

    def pack(self) -> bytes:
        """Empacota o cabeçalho e os dados em um array de bytes."""
        # Empacota primeiro com checksum = 0 para poder calcular o checksum do pacote todo
        header_without_checksum = struct.pack(
            HEADER_FORMAT,
            self.auth_label,
            self.auth_hash,
            self.seq_num,
            self.ack_num,
            self.flags,
            self.payload_size,
            0  # Checksum provisório
        )
        packet_bytes = header_without_checksum + self.payload
        self.checksum = calculate_checksum(packet_bytes)
        
        # Agora empacota de verdade com o checksum calculado
        header = struct.pack(
            HEADER_FORMAT,
            self.auth_label,
            self.auth_hash,
            self.seq_num,
            self.ack_num,
            self.flags,
            self.payload_size,
            self.checksum
        )
        return header + self.payload

    @classmethod
    def unpack(cls, data: bytes):
        """Desempacota um array de bytes em um objeto RUDP_Packet e verifica a integridade."""
        if len(data) < HEADER_SIZE:
            raise ValueError("Pacote muito pequeno para conter o cabeçalho")
        
        header = data[:HEADER_SIZE]
        payload = data[HEADER_SIZE:]
        
        (auth_label, auth_hash, seq_num, ack_num, flags, payload_size, received_checksum) = struct.unpack(HEADER_FORMAT, header)
        
        packet = cls(seq_num, ack_num, flags, payload[:payload_size])
        
        # Validar Checksum
        header_without_checksum = struct.pack(
            HEADER_FORMAT,
            auth_label,
            auth_hash,
            seq_num,
            ack_num,
            flags,
            payload_size,
            0
        )
        packet_bytes = header_without_checksum + payload[:payload_size]
        calculated_checksum = calculate_checksum(packet_bytes)
        
        if received_checksum != calculated_checksum:
            raise ValueError("Checksum inválido! Pacote corrompido.")
            
        return packet

import socket, random, struct

transaction_id = [random.randint(0, 255) for _ in range(12)]

stun_request = bytes([
    0x00, 0x01,  # Message Type: Binding Request
    0x00, 0x00,  # Message Length: 0
    0x21, 0x12, 0xA4, 0x42,  # Magic Cookie
    *transaction_id  # Распаковываем список в байты
])

stun_servers = [
    ('stun.sipgate.net', 10000),
]

def parse_stun(data):
    magic_cookie = struct.unpack('!I', data[4:8])[0]

    port_xor = struct.unpack('!H', data[26:28])[0]
    ip_xor = struct.unpack('!I', data[28:32])[0]

    actual_port = port_xor ^ (magic_cookie >> 16)
    actual_ip = ip_xor ^ magic_cookie

    ip_bytes = struct.pack('!I', actual_ip)
    public_ip = '.'.join(str(b) for b in ip_bytes)

    return public_ip, actual_port

def get_me_addr(sock, logger):
    p_addr = None
    p_port = None
    for host, port in stun_servers:
        try:        
            # Получаем IPv4 адрес
            addr_info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)
            server_addr = addr_info[0][4]
            
            sock.sendto(stun_request, server_addr)
            
            data, addr = sock.recvfrom(4096)
            logger.info(f"Received {len(data)} bytes from stun: {addr}")
            p_addr, p_port = parse_stun(data)
            break
            
        except socket.timeout:
            logger.error(f"Timeout")
        except Exception as e:
            logger.error(f"Error: {e}")
    return p_addr, p_port
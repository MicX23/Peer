import socket, message_pb2

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('127.0.0.1',9090))
data, addr = sock.recvfrom(1024)
print(data)
msg = message_pb2.Test()
msg.ParseFromString(data)

print("Получено:")
print(f"  user_id: {msg.user_id}")
print(f"  message_id: {msg.message_id}")
print(f"  text: {msg.text}")
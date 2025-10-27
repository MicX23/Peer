import socket, message_pb2

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

msg = message_pb2.Test()
msg.user_id = 1
msg.message_id = 1
msg.text = "Hello"

data = msg.SerializeToString()

sock.sendto(data,('127.0.0.1',9090))
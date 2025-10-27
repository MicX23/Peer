import socket, random

class TestServer():
    def __init__(self):
        self.Name = "TestServer"
        self.ServerUP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM).bind(("127.0.0.1", 83094))
        self.ServerPush = socket.socket(socket.AF_INET, socket.SOCK_DGRAM).bind(("127.0.0.1", 83095))
        self.Users = []
        self.Status = True
        # user = {
        #     'id':0,
        #     "userName":"user",
        #     'UID': 123213432
        # }
        self.Messages = []
        # message = {
        #     'id': 0,
        #     'userID': 0,
        #     'userName': "User",
        #     'message':'message',
        # }

    def listen(self):
        while self.Status:
            try:
                pass
            except socket.timeout:
                pass
import socket, asyncio

import json # Временно ... 

class User():
    profiles = {
        "Name": "Anonim"
    }

class TestSpace():
    space_id = '1'

    def __init__(self, node, id):
        self.node = node
        self.space_id = str(id)
        self.private_addr = node.GetMeSock()

    async def AskToConnect(self, name):
        data = input(f"{name} хочет присоедениться\n1 - да, 2 - нет\n")
        if data == '1':
            correct = await self.ConnectTo(data)
            return True 
        else: False

    def get(self):
        return self.space_id
    
    async def ConnectTo(self, data) -> bool:
        await asyncio.get_event_loop().sock_sendto(self.private_addr ,'AscConnect', data['addr'])
        


class Node():
    Essence     = None      # User 
    SignalList  = [         # Сигнальные сервера сервера 
        ('127.0.0.1',9090)  # Test
        ]    
    Spaces       = {}       # Пространства    
    public_addr  = None     # Теперь этим занимается Networker
    Status       = False    #

    def __init__(self):
        self.load()
        self.Essence = User() # Testing
        self.Spaces[str(len(self.Spaces))] = TestSpace(self,len(self.Spaces))
        self.Status = True
        # self.private_addr = socket.socket().bind(('127.0.0.1',29292)) # TODO: Random port
        asyncio.run(self.Listen())

    async def Listen(self, addr=None): # if not addr пока нет
        self.public_addr = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.public_addr.bind(('127.0.0.1',29384))
        self.public_addr.setblocking(False)
        self.public_addr.settimeout(5)

        await self.sendNewInfoSigServer()
        return
        print(f"DEBUG:To listen Node start in {self.public_addr.getsockname()}")

        while self.Status:
            try:
                data, addr = await asyncio.get_event_loop().sock_recvfrom(self.public_addr, 1024)
                asyncio.create_task(self.SerializeUDP(data,addr))
            except TimeoutError:
                asyncio.sleep(0.1)
        
    async def sendNewInfoSigServer(self):
        data = json.dumps({
                    'spaces_id': list(self.Spaces.keys()),
                    'my_addr': self.public_addr.getsockname()
                })
        for addr in self.SignalList:
            await asyncio.get_event_loop().sock_sendto(
                self.public_addr ,
                data.encode('utf-8'), 
                addr)

        print('sendNewInfoSigServer: DONE')



    async def SerializeUDP(self, data, addr) -> bool:
        # Пока json TODO: ProtoBuf ждёт
        data = json.loads(data.encode('utf-8'))
        if not data['space_id'] and not data['verify_key'] and not data['addr']: return False
        try:
            if not self.Spaces[data['space_id']].AskToConnect('Anon'): return False
        except KeyError:
            print("Debug: Нет такого пространства")
            return False
        return True

    
    def GetMeSock(self, addr=None) -> socket.socket:
        NewSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if not addr:NewSock.bind(('127.0.0.1', 9119)) # TODO: Random port
        else: NewSock.bind(addr)
        return NewSock

        

    def load(self):
        print("Load funk")

    def save(self):
        print("Save")
    

##############################/ TESTIG /#####################################


def MainTest():
    TN = Node()
    
if __name__ == '__main__':
    MainTest()
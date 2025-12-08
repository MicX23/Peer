class TextChat:
    messages = []
    users = []
    Server = None
    MyUser = None

    def add_mesage(self, username, text):
        self.messages.append({
            'id': self.getID(),
            'UserName': username,
            'Text': text,
            "status": False
            })
        
    def getID(self) -> int:
        self.last_id = self.last_id + 1
        return self.last_id
    
    def getUnreadMessages() -> list:
        UnreadMeassages = []
        for message in self.messages:
            if not message['status']:
                message['status'] = True
                UnreadMeassages.append(message)
import asyncio

class User:

    def __init__(self, storage, logger):
        self.username       = 'Anonim'
        self.id             = None      # Verefy Key
        self.sign_key       = None      # 
        self.private_key    = None      #
        self.public_key     = None      #

        self.metadata       = None      #
        self.storage        = storage   #
        self.logger         = logger    #


    async def start(self):
        self.logger.debug('Starting user')
        if await self._load() == None: return 1 # пользываьель не загружен
        return 0 # успешно загрузился

    async def _load(self):
        # storage.user_load()
        return None

    async def get_keys_profile(self) -> list:
        return [self.private_key, self.public_key, self.sign_key, self.verify_key]
    
    async def get_metadata(self):
        pass

    async def _save(self):
        pass

    def create_user(self, private_key, public_key, verify_key, sign_key):
        self.private_key    = private_key
        self.public_key     = public_key
        self.id             = verify_key
        self.sign_key       = sign_key
        # self._save()
        return True

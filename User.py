import asyncio

class User:

    def __init__(self, storage, logger):
        self.username       = 'Anonim'
        self.id             = None      # Verefy Key
        self._sign_key      = None      # 
        self._private_key   = None      #
        self.public_key     = None      #

        self.metadata       = None      #
        self.storage        = storage   #
        self.logger         = logger    #

    @property
    def profile(self) -> dict:
        pr = {
            'id': self.id,
            'public_key': self.public_key,
            'sign_key': self._sign_key,
            'private_key': self._private_key
        }
        return pr


    async def start(self):
        self.logger.debug('Starting user')
        if await self._load() == None: return 1 # пользываьель не загружен
        return 0 # успешно загрузился

    async def _load(self):
        # storage.user_load()
        return None

    def get_keys_profile(self) -> list:
        return [self._private_key, self.public_key, self._sign_key, self.id]
    
    async def get_metadata(self):
        pass

    async def _save(self):
        pass

    def create_user(self, private_key, public_key, sign_key, verify_key, name):
        self._private_key    = private_key
        self.public_key      = public_key
        self._sign_key       = sign_key
        self.id              = verify_key
        self.username        = name
        # self._save()
        return True

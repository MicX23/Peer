profiles = {
    "indeficator" : {           # У каждого сервера свой профиль
        "name": "Anonim1",            # Имя сущьности
        "images": "1"         # Аватар
    },
    "1" : {                     # У каждого сервера свой профиль
        "name": "Anonim2",            # Имя сущьности
        "images": "2"         # Аватар
    },
    "2" : {                     # У каждого сервера свой профиль
        "name": "Anonim3",            # Имя сущьности
        "images": "3"         # Аватар
    }
}

def get_profile(id:str) -> dict:
    for i in profiles.keys():
        if i == id: return profiles[i]


print(get_profile("2"))
print("1" in profiles.keys())
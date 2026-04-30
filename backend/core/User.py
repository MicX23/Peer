# ./core/User.py
import json, nacl.signing, nacl.utils, nacl.public
from nacl.exceptions import BadSignatureError, CryptoError
from pathlib import Path


# Класс пользователя: управление ключами, подписью и шифрованием.
# Все криптографические операции выполняются синхронно (для вызова через asyncio.to_thread при необходимости).


class User:

    def __init__(self, name: str | None = None, verify_key_hex: str | None = None):
        self.is_loaded = False
        if name:
            self._signing_key = nacl.signing.SigningKey.generate()
            self._verify_key = self._signing_key.verify_key
            self._box_private = nacl.public.PrivateKey.generate()
            self._box_public = self._box_private.public_key
            # Базовый профиль без сессионного ключа
            self._profile = {
                "name": name,
                "verify_key": self._verify_key.encode().hex()
            }
            self.is_loaded = True

    # ==================== Свойства (только чтение) ====================

    @property
    def signing_key(self) -> nacl.signing.SigningKey: # Приватный ключ подписи — не передаётся.
        return self._signing_key

    @property
    def verify_key(self) -> nacl.signing.VerifyKey: # Публичный ключ проверки подписи — передаётся всем.
        return self._verify_key

    @property
    def box_key(self) -> nacl.public.PrivateKey:# Приватный ключ шифрования — не передаётся.
        return self._box_private

    @property
    def box_public_key(self) -> nacl.public.PublicKey: # Публичный ключ шифрования — передаётся для установки безопасного канала.
        return self._box_public

    @property
    def profile(self) -> dict:
        """Всегда возвращает актуальный профиль с текущими ключами сессии."""
        self._profile["verify_key"] = self._verify_key.encode().hex()
        self._profile["box_public_key"] = self._box_public.encode().hex()
        return self._profile.copy()
    
    @property
    def profile_signature(self):
        profile_bytes = json.dumps(
            self.profile,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False
        ).encode('utf-8')
        
        signed = self.signing_key.sign(profile_bytes)
        return signed.signature.hex()

    # ==================== Подпись / Проверка ====================

    def sign(self, data: bytes | str) -> dict:
        # Подписать данные.
        # param data: данные для подписи (bytes или str)
        # return: dict с исходными данными и подписью в hex

        if isinstance(data, str):
            data = data.encode('utf-8')
        
        signed = self._signing_key.sign(data)
        return {
            "data": data.decode('utf-8', errors='ignore'),
            "signature": signed.signature.hex(),
            "signer_verify_key": self._verify_key.encode().hex()
        }

    def verify(self, signed_data: dict, expected_verify_key: nacl.signing.VerifyKey | None = None) -> bool:
        # Проверить подпись.
        # :param signed_data: dict с полями 'data', 'signature', 'signer_verify_key'
        # :param expected_verify_key: ожидаемый публичный ключ (если известен заранее)
        # :return: True если подпись валидна
        try:
            data = signed_data["data"].encode('utf-8')
            signature = bytes.fromhex(signed_data["signature"])
            signer_key_hex = signed_data.get("signer_verify_key")

            # Если ключ не передан явно — берём из подписанных данных
            if expected_verify_key is None:
                if not signer_key_hex:
                    return False
                verify_key = nacl.signing.VerifyKey(bytes.fromhex(signer_key_hex))
            else:
                verify_key = expected_verify_key

            verify_key.verify(data, signature)
            return True
        except (BadSignatureError, KeyError, ValueError, CryptoError):
            return False

    # ==================== Шифрование / Расшифрование (Box) ====================

    def encrypt_for(self, data: bytes | str, recipient_public_key: nacl.public.PublicKey | str) -> str:
        """
        Зашифровать данные для получателя.
        :param data: данные для шифрования
        :param recipient_public_key: публичный ключ получателя (obj или hex-строка)
        :return: зашифрованные данные в hex-строке
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if isinstance(recipient_public_key, str):
            recipient_public_key = nacl.public.PublicKey(bytes.fromhex(recipient_public_key))
        
        box = nacl.public.Box(self._box_private, recipient_public_key)
        encrypted = box.encrypt(data)
        return encrypted.hex()

    def decrypt_from(self, encrypted_hex: str, sender_public_key: nacl.public.PublicKey | str) -> str | None:
        """
        Расшифровать данные от отправителя.
        :param encrypted_hex: зашифрованные данные в hex
        :param sender_public_key: публичный ключ отправителя (для аутентификации источника)
        :return: расшифрованная строка или None при ошибке
        """
        try:
            encrypted = bytes.fromhex(encrypted_hex)
            if isinstance(sender_public_key, str):
                sender_public_key = nacl.public.PublicKey(bytes.fromhex(sender_public_key))
            
            box = nacl.public.Box(self._box_private, sender_public_key)
            decrypted = box.decrypt(encrypted)
            return decrypted.decode('utf-8')
        except (CryptoError, ValueError, KeyError):
            return None

    # ==================== Вспомогательные методы ====================

    def export_keys(self, password: str | None = None) -> dict:
        """
        Экспорт ключей для сохранения (опционально с паролем).
        """
        # Для учебной реализации — простой экспорт в hex
        return {
            "signing_key": self._signing_key.encode().hex(),
            "box_private": self._box_private.encode().hex(),
            "profile": self._profile
        }
    # ==================== Созранение и загрузка =====================
    @classmethod
    def import_keys(cls, keys_data: dict) -> "User":
        # Импорт пользователя из сохранённых ключей.
        user = cls.__new__(cls)  # создаём экземпляр без __init__
        
        user._signing_key = nacl.signing.SigningKey(bytes.fromhex(keys_data["signing_key"]))
        user._verify_key = user._signing_key.verify_key
        
        user._box_private = nacl.public.PrivateKey(bytes.fromhex(keys_data["box_private"]))
        user._box_public = user._box_private.public_key
        
        user._profile = keys_data["profile"]
        return user
    
    def save(self, save_dir: str = "./user_save") -> bool:
        """Сохраняет только signing_key и базовый profile (без box_public_key)."""
        try:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)

            # Убираем сессионный ключ перед записью на диск
            base_profile = {k: v for k, v in self._profile.items() if k != "box_public_key"}
            save_data = {
                "signing_key": self._signing_key.encode().hex(),
                "profile": base_profile
            }

            # Имя файла = verify_key.hex()
            filename = f"{self._verify_key.encode().hex()}.json"
            with open(save_path / filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False


    @classmethod
    def load(cls, save_dir: str = "./user_save") -> "User | None":
        """Загружает единственный файл из папки. box_private генерируется заново."""
        try:
            save_path = Path(save_dir)
            if not save_path.exists(): return None
            json_files = list(save_path.glob("*.json"))
            if len(json_files) != 1: return None

            with open(json_files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)

            user = cls.__new__(cls)
            user._signing_key = nacl.signing.SigningKey(bytes.fromhex(data["signing_key"]))
            user._verify_key = user._signing_key.verify_key
            user._box_private = nacl.public.PrivateKey.generate()  # Новый каждый раз
            user._box_public = user._box_private.public_key

            # Восстанавливаем профиль и сразу подставляем актуальный box_public_key
            user._profile = data.get("profile", {})
            user._profile["verify_key"] = user._verify_key.encode().hex()
            user._profile["box_public_key"] = user._box_public.encode().hex()
            user.is_loaded = True
            return user
        except Exception:
            return None
    
if __name__ == "__main__":
    import sys
    import traceback

    def print_test_header(name: str):
        print(f"\n{'='*60}")
        print(f" ТЕСТ: {name}")
        print(f"{'='*60}")

    def print_result(success: bool, message: str = ""):
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"[{status}] {message}")
        return success

    all_passed = True

    # -------------------------------------------------------------------------
    # Тест 1: Инициализация и свойства
    # -------------------------------------------------------------------------
    print_test_header("Инициализация User и свойства")
    try:
        user = User(name="TestUser", profile_extra={"role": "admin", "dept": "IT"})
        
        # Проверка обязательных полей профиля
        assert "name" in user.profile, "Профиль должен содержать 'name'"
        assert user.profile["name"] == "TestUser", "Имя в профиле не совпадает"
        assert "verify_key" in user.profile, "Профиль должен содержать 'verify_key'"
        assert "box_public_key" in user.profile, "Профиль должен содержать 'box_public_key'"
        
        # Проверка дополнительных полей
        assert user.profile.get("role") == "admin", "Доп. поле 'role' не сохранено"
        assert user.profile.get("dept") == "IT", "Доп. поле 'dept' не сохранено"
        
        # Проверка типов ключей
        from nacl.signing import SigningKey, VerifyKey
        from nacl.public import PrivateKey, PublicKey
        
        assert isinstance(user.signing_key, SigningKey), "signing_key имеет неверный тип"
        assert isinstance(user.verify_key, VerifyKey), "verify_key имеет неверный тип"
        assert isinstance(user.box_key, PrivateKey), "box_key имеет неверный тип"
        assert isinstance(user.box_public_key, PublicKey), "box_public_key имеет неверный тип"
        
        # Проверка, что profile возвращает копию
        original_name = user.profile["name"]
        user.profile["name"] = "Hacked"
        assert user.profile["name"] == original_name, "profile не возвращает копию!"
        
        all_passed &= print_result(True, "Инициализация и свойства работают корректно")
        
    except Exception as e:
        all_passed &= print_result(False, f"Ошибка: {e}")
        traceback.print_exc()

    # -------------------------------------------------------------------------
    # Тест 2: Подпись и проверка (sign / verify)
    # -------------------------------------------------------------------------
    print_test_header("Подпись и проверка данных (Ed25519)")
    try:
        alice = User(name="Alice")
        bob = User(name="Bob")
        
        message = "Это важное служебное сообщение"
        
        # Алиса подписывает сообщение
        signed = alice.sign(message)
        assert isinstance(signed, dict), "sign() должен возвращать dict"
        assert "data" in signed and "signature" in signed and "signer_verify_key" in signed
        
        # Боб проверяет подпись с явным указанием ключа
        is_valid = bob.verify(signed, alice.verify_key)
        assert is_valid is True, "Валидная подпись не прошла проверку с ключом"
        
        # Боб проверяет подпись без явного ключа (ключ берётся из signed_data)
        is_valid_auto = bob.verify(signed)
        assert is_valid_auto is True, "Валидная подпись не прошла авто-проверку"
        
        # Проверка подделки: изменяем данные
        tampered = signed.copy()
        tampered["data"] = "Подделанное сообщение"
        is_forged = bob.verify(tampered, alice.verify_key)
        assert is_forged is False, "Подделка данных не была обнаружена!"
        
        # Проверка неверным ключом
        is_wrong_key = bob.verify(signed, bob.verify_key)
        assert is_wrong_key is False, "Проверка чужим ключом должна вернуть False"
        
        all_passed &= print_result(True, "Подпись и проверка работают корректно")
        
    except Exception as e:
        all_passed &= print_result(False, f"Ошибка: {e}")
        traceback.print_exc()

    # -------------------------------------------------------------------------
    # Тест 3: Шифрование и расшифрование (Box)
    # -------------------------------------------------------------------------
    print_test_header("Шифрование и расшифрование (Curve25519 Box)")
    try:
        sender = User(name="Sender")
        receiver = User(name="Receiver")
        
        secret = "Конфиденциальные данные: пароль123"
        
        # Шифрование: отправитель -> получатель (по публичному ключу получателя)
        encrypted = sender.encrypt_for(secret, receiver.box_public_key)
        assert isinstance(encrypted, str), "encrypt_for должен возвращать hex-строку"
        assert len(encrypted) > len(secret), "Шифротекст должен быть длиннее исходных данных"
        
        # Расшифрование: получатель -> от отправителя (по публичному ключу отправителя)
        decrypted = receiver.decrypt_from(encrypted, sender.box_public_key)
        assert decrypted == secret, f"Расшифрованные данные не совпадают: '{decrypted}' != '{secret}'"
        
        # Тест с hex-строкой ключа вместо объекта
        encrypted_hex_key = sender.encrypt_for(secret, receiver.box_public_key.encode().hex())
        decrypted_hex_key = receiver.decrypt_from(encrypted_hex_key, sender.box_public_key.encode().hex())
        assert decrypted_hex_key == secret, "Шифрование с hex-ключом не работает"
        
        # Проверка: неверный ключ отправителя не расшифрует
        wrong_decrypt = receiver.decrypt_from(encrypted, bob.verify_key if 'bob' in locals() else receiver.box_public_key)
        assert wrong_decrypt is None, "Расшифровка неверным ключом должна вернуть None"
        
        all_passed &= print_result(True, "Шифрование и расшифрование работают корректно")
        
    except Exception as e:
        all_passed &= print_result(False, f"Ошибка: {e}")
        traceback.print_exc()

    # -------------------------------------------------------------------------
    # Тест 4: Экспорт и импорт ключей
    # -------------------------------------------------------------------------
    print_test_header("Экспорт и импорт ключей")
    try:
        original = User(name="ExportTest", profile_extra={"id": 42})
        
        # Экспорт
        exported = original.export_keys()
        assert "signing_key" in exported, "Экспорт не содержит signing_key"
        assert "box_private" in exported, "Экспорт не содержит box_private"
        assert "profile" in exported, "Экспорт не содержит profile"
        
        # Импорт
        restored = User.import_keys(exported)
        
        # Проверка, что профиль восстановлен
        assert restored.profile["name"] == original.profile["name"], "Имя не восстановлено"
        assert restored.profile.get("id") == 42, "Доп. поле не восстановлено"
        
        # Проверка, что ключи работают: подписываем и проверяем
        test_msg = "Проверка после импорта"
        signed = restored.sign(test_msg)
        is_valid = restored.verify(signed, restored.verify_key)
        assert is_valid is True, "Подпись после импорта не работает"
        
        # Проверка шифрования между original и restored (должны быть одни и те же ключи)
        encrypted = original.encrypt_for("Secret", restored.box_public_key)
        decrypted = restored.decrypt_from(encrypted, original.box_public_key)
        assert decrypted == "Secret", "Шифрование между original/restored не работает"
        
        all_passed &= print_result(True, "Экспорт и импорт ключей работают корректно")
        
    except Exception as e:
        all_passed &= print_result(False, f"Ошибка: {e}")
        traceback.print_exc()

    # -------------------------------------------------------------------------
    # Тест 5: Обработка некорректных данных
    # -------------------------------------------------------------------------
    print_test_header("Обработка ошибок и некорректных входных данных")
    try:
        user = User(name="Test")
        
        # verify с невалидными данными
        assert user.verify({"data": "x", "signature": "invalid", "signer_verify_key": "abc"}) is False
        assert user.verify({}) is False  # пустой dict
        
        # decrypt_from с невалидными данными
        assert user.decrypt_from("not_hex", user.box_public_key) is None
        assert user.decrypt_from("aabbcc", user.box_public_key) is None  # слишком короткий
        
        # Инициализация без name должна вызвать ошибку
        try:
            bad_user = User(name="")
            all_passed &= print_result(False, "User('') должен вызывать ValueError")
        except ValueError:
            all_passed &= print_result(True, "Некорректные данные корректно отклоняются")
            
    except Exception as e:
        all_passed &= print_result(False, f"Ошибка в тестах ошибок: {e}")
        traceback.print_exc()

    # -------------------------------------------------------------------------
    # Итоговый отчёт
    # -------------------------------------------------------------------------
    print(f"\n{'='*60}")
    if all_passed:
        print(" ИТОГ: Все тесты пройдены успешно ✓")
    else:
        print(" ИТОГ: Некоторые тесты не пройдены ✗")
        sys.exit(1)
    print(f"{'='*60}\n")
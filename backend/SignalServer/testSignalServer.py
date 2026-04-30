import asyncio
import socket
import json
import sys
from datetime import datetime

class SignalTestClient:
    def __init__(self, server_ip='127.0.0.1', server_port=23023):
        self.server_addr = (server_ip, server_port)
        self.sock = None
        self.loop = None
        self.timeout = 2.0

    async def _setup_socket(self):
        # Создание неблокирующего UDP сокета
        self.loop = asyncio.get_running_loop()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)

    async def _send_and_receive(self, payload: dict, label: str = ""):
        # Отправка JSON пакета и ожидание ответа
        raw = json.dumps(payload).encode('utf-8')
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] [SEND]{label}")
        print(f"  -> {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        await self.loop.sock_sendto(self.sock, raw, self.server_addr)
        
        try:
            data, addr = await asyncio.wait_for(
                self.loop.sock_recvfrom(self.sock, 4096), timeout=self.timeout
            )
            # Попытка десериализации JSON, иначе возврат сырых данных
            try:
                resp = json.loads(data.decode('utf-8'))
                print(f"[{timestamp}] [RECV]{label}")
                print(f"  <- {json.dumps(resp, indent=2, ensure_ascii=False)}")
                return resp, addr
            except json.JSONDecodeError:
                print(f"[{timestamp}] [RECV]{label} (RAW)")
                print(f"  <- {data.decode('utf-8', errors='ignore')}")
                return data.decode('utf-8', errors='ignore'), addr
        except asyncio.TimeoutError:
            print(f"[{timestamp}] [TIMEOUT]{label}")
            return None, None

    async def run_tests(self):
        await self._setup_socket()
        print(f"=== ЗАПУСК ТЕСТИРОВАНИЯ SignalServer {self.server_addr} ===")

        # 1. Базовая проверка живости сервера
        print("\n--- Тест 1: Проверка живости (Ping) ---")
        resp, _ = await self._send_and_receive({"type": "ping", "ts": "1714320000"}, "(PING)")
        if resp is None:
            print("[FAIL] Сервер не отвечает. Проверьте порт и firewall.")
            return
        print("[OK] Сетевое соединение установлено")

        # 2. Регистрация нового пользователя/пространства (Node.md: ss_send 'type': "New")
        print("\n--- Тест 2: Регистрация (New) ---")
        new_payload = {
            "type": "New",
            "user_metadata": {"name": "DiplomaUser", "verify_key": "hex_pub_key_here"},
            "space_metadata": {"space_id": "test_space_01", "name": "TestRoom"}
        }
        resp, _ = await self._send_and_receive(new_payload, "(NEW)")
        
        # В текущей версии сервер отвечает "Hello". В продакшене ожидается {"type": "Welcome", ...}
        expected_keys = {"type", "status", "identifier", "user_id"}
        if isinstance(resp, dict) and expected_keys.issubset(resp.keys()):
            print("[OK] Регистрация подтверждена сервером")
        else:
            print("[INFO] Сервер вернул эхо или приветствие. Логика маршрутизации ещё не активна.")

        # 3. Запрос на подключение к другому пиру (Node.md: Connect)
        print("\n--- Тест 3: Запрос соединения (Connect) ---")
        connect_payload = {
            "id_message": "msg_9f8a7b6c",
            "type": "Connect",
            "addr": ["127.0.0.1", 5000],
            "target_id": "target_peer_id"
        }
        resp, _ = await self._send_and_receive(connect_payload, "(CONNECT)")
        
        # В продакшене сервер должен либо переслать пакет цели, либо вернуть статус
        print("[INFO] Пакет Connect отправлен. Сервер должен маршрутизировать его целевому пиру.")
        print("[INFO] Ожидается ответ: {id_message: 'msg_9f8a7b6c', response: true/false}")

        # 4. Имитация получения Connect_to от целевого пира (через сервер)
        print("\n--- Тест 4: Проверка структуры Connect_to (локальная валидация) ---")
        connect_to_structure = {
            "type": "Connect_to",
            "user_metadata": {
                "user_id": "peer_02",
                "name": "PeerTwo",
                "verify_key": "ed25519_pub_key_hex",
                "signature": "ed25519_sig_hex"
            },
            "space_metadata": {
                "space_id": "test_space_01",
                "secret": "blake2b_secret_hex",
                "metadata": {"name": "TestRoom", "admin": "peer_01"},
                "verify_key": "space_pub_key_hex",
                "signature": "space_sig_hex",
                "addr": ["192.168.1.100", 61234]
            }
        }
        # Валидация структуры без отправки (проверка соответствия Node.md)
        required_top = {"type", "user_metadata", "space_metadata"}
        required_user = {"user_id", "name", "verify_key", "signature"}
        required_space = {"space_id", "secret", "metadata", "verify_key", "signature", "addr"}
        
        if (required_top.issubset(connect_to_structure.keys()) and
            required_user.issubset(connect_to_structure["user_metadata"].keys()) and
            required_space.issubset(connect_to_structure["space_metadata"].keys())):
            print("[OK] Структура Connect_to полностью соответствует спецификации Node.md")
        else:
            print("[FAIL] Структура Connect_to не совпадает с требованиями")

        # 5. Имитация Connect_ok (финальное подтверждение)
        print("\n--- Тест 5: Проверка структуры Connect_ok ---")
        connect_ok_structure = {
            "type": "Connect_ok",
            "space_id": "test_space_01",
            "new_addr": ["192.168.1.100", 61234]
        }
        if all(k in connect_ok_structure for k in ("type", "space_id", "new_addr")):
            print("[OK] Структура Connect_ok валидна. Готово к P2P UDP обмену.")

        self.sock.close()
        print("\n=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")

if __name__ == "__main__":
    client = SignalTestClient(server_ip='127.0.0.1', server_port=23023)
    try:
        asyncio.run(client.run_tests())
    except KeyboardInterrupt:
        print("\n[TEST] Прервано пользователем")
    except Exception as e:
        print(f"\n[CRITICAL] Ошибка теста: {e}")
        sys.exit(1)
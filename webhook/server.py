import hmac
import hashlib

secret = "vS22AKhZ4CUtdcMKfBMGOX7NzsEJ0WRn-gCetwQv9FXf51x-0eh7kXNfLYPUcu7QuUzA396cwcdrOOa70o6XcLMiwto7wGSk"

with open("test.json", "rb") as f:
    body = f.read()

# Создаём HMAC SHA1
mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha1)

# Выводим в hex
signature_hex = mac.hexdigest()

print(signature_hex)
import hmac
import hashlib
import base64

secret = "vS22AKhZ4CUtdcMKfBMGOX7NzsEJ0WRn-gCetwQv9FXf51x-0eh7kXNfLYPUcu7QuUzA396cwcdrOOa70o6XcLMiwto7wGSk"
with open("test.json", "rb") as f:
    body = f.read()

mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha1)
signature_b64 = base64.b64encode(mac.digest()).decode()

print(signature_b64)
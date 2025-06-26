import secrets, base64
key = secrets.token_bytes(32)                   # 32 random bytes
print(base64.urlsafe_b64encode(key).decode())
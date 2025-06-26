import secrets, base64, os
print(secrets.token_hex(32)) # hex
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
from secrets import token_hex

import netranker.storage

HMAC_KEY = token_hex(256)
RESTFUL_JSON = {'ensure_ascii': False}
STORAGE = netranker.storage.InMemoryCardStorage()

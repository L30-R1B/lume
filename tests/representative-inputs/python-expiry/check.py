from app import is_expired
assert is_expired(10,10) and is_expired(11,10) and not is_expired(9,10)

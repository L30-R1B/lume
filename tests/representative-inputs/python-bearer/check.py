from app import bearer
assert bearer("Bearer abc")=="abc" and bearer("Bearer ") is None and bearer("Basic abc") is None and bearer("") is None and bearer("bearer abc") is None

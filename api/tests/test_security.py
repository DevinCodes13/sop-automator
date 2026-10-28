from app.security import hash_key, hash_password, new_api_key, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse battery")
    assert hashed != "correct horse battery"
    assert verify_password("correct horse battery", hashed)
    assert not verify_password("wrong password", hashed)


def test_api_keys_are_random_and_stored_hashed():
    a, b = new_api_key(), new_api_key()
    assert a != b
    assert a.startswith("sop_")
    assert hash_key(a) != a
    assert len(hash_key(a)) == 64

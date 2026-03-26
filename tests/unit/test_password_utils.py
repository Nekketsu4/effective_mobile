from app.utils.password import hash_password, verify_password


def test_hash_is_not_plaintext():
    hashed = hash_password("pass123")
    assert hashed != "pass123"


def test_same_password_give_different_hashes():
    hash1 = hash_password("pass123")
    hash2 = hash_password("pass123")
    assert hash1 != hash2


def test_correct_password_verifies():
    hashed = hash_password("pass123")
    assert verify_password("pass123", hashed) is True


def test_wrong_password_fails():
    hashed = hash_password("pass123")
    assert verify_password("wrongpass", hashed) is False


def test_empty_password_can_be_hasshed():
    hashed = hash_password("")
    assert verify_password("", hashed) is True

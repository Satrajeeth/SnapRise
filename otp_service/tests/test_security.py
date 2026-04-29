from app.services.security import OtpHasher, mask_email


def test_otp_hash_round_trip():
    code = OtpHasher.generate_code(6)
    otp_hash, salt = OtpHasher.create_hash(code)

    assert len(code) == 6
    assert OtpHasher.verify(code, otp_hash, salt) is True
    assert OtpHasher.verify("000000", otp_hash, salt) is False


def test_mask_email_masks_local_part():
    assert mask_email("snaprise@example.com").startswith("sn")
    assert mask_email("ab@example.com") == "a*@example.com"

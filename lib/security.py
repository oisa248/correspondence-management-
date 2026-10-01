import hashlib, hmac, os

def _h(p, salt): return hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(salt), 120000).hex()
def hash_pw(p):
    s = os.urandom(16).hex()
    return f"{s}${_h(p, s)}"
def check_pw(p, stored):
    s, d = stored.split("$")
    return hmac.compare_digest(_h(p, s), d)

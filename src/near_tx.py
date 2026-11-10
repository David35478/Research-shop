"""Minimal NEAR transaction construction and Ed25519 signing.

Used for the agent's restricted function-call access key: the key lives in an
env var, and every transaction is checked against a contract/method allowlist
before signing (see src/payout.py). Serialization follows NEAR's borsh schema.
"""
import base64
import hashlib

from nacl.signing import SigningKey


ED25519_PREFIX = b"\x00"  # KeyType curve byte


def _borsh_str(s: str) -> bytes:
    b = s.encode()
    return len(b).to_bytes(4, "little") + b


def _u64(n: int) -> bytes:
    return n.to_bytes(8, "little")


def _u128(n: int) -> bytes:
    return n.to_bytes(16, "little")


def encode_function_call_tx(
    signer_id: str,
    public_key_hex: str,
    nonce: int,
    receiver_id: str,
    block_hash_hex: str,
    method_name: str,
    args: bytes,
    gas: int,
    deposit_yocto: int,
) -> bytes:
    """Borsh-encode a Transaction with a single FunctionCall action."""
    out = _borsh_str(signer_id)
    pk = bytes.fromhex(public_key_hex)
    out += ED25519_PREFIX + pk
    out += _u64(nonce)
    out += _borsh_str(receiver_id)
    out += bytes.fromhex(block_hash_hex)
    out += (1).to_bytes(4, "little")  # one action
    out += (2).to_bytes(1, "little")  # FunctionCall action ordinal
    out += _borsh_str(method_name)
    out += len(args).to_bytes(4, "little") + args
    out += _u64(gas)
    out += _u128(deposit_yocto)
    return out


def decode_function_call_tx(data: bytes) -> dict:
    """Round-trip decoder used by tests to verify the serializer."""
    off = 0

    def rstr():
        nonlocal off
        n = int.from_bytes(data[off:off + 4], "little"); off += 4
        s = data[off:off + n].decode(); off += n
        return s

    def rint(n):
        nonlocal off
        v = int.from_bytes(data[off:off + n], "little"); off += n
        return v

    signer_id = rstr()
    off += 1  # curve byte
    public_key = data[off:off + 32].hex(); off += 32
    nonce = rint(8)
    receiver_id = rstr()
    block_hash = data[off:off + 32].hex(); off += 32
    assert rint(4) == 1
    assert rint(1) == 2
    method_name = rstr()
    n = rint(4); args = data[off:off + n]; off += n
    gas = rint(8)
    deposit = rint(16)
    return {
        "signer_id": signer_id, "public_key": public_key, "nonce": nonce,
        "receiver_id": receiver_id, "block_hash": block_hash,
        "method_name": method_name, "args": args, "gas": gas, "deposit": deposit,
    }


def sign_transaction(tx_bytes: bytes, private_key_hex: str) -> dict:
    """Sign with Ed25519; returns an RPC-ready signed-tx (base64)."""
    sk = SigningKey(bytes.fromhex(private_key_hex))
    sig = sk.sign(tx_bytes).signature
    pk = sk.verify_key.encode()
    signed = tx_bytes + ED25519_PREFIX + pk + sig
    return {"signed_tx": base64.b64encode(signed).decode()}


def tx_hash(tx_bytes: bytes) -> str:
    return hashlib.sha256(tx_bytes).hexdigest()

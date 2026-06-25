#!/usr/bin/env python
"""Generate a development RSA keypair for JWT (RS256) signing.

Writes ``secrets/jwt_private.pem`` and ``secrets/jwt_public.pem`` relative to the
Atom-agent repo root. The ``secrets/`` directory is gitignored — these are DEV
keys only; provision production keys through your secret manager.

Usage:
    python scripts/gen_jwt_keys.py            # 2048-bit keypair into ./secrets
    python scripts/gen_jwt_keys.py --bits 4096 --out-dir /path/to/keys

Then point the service at them (e.g. in .env):
    JWT_ALGORITHM=RS256
    JWT_PRIVATE_KEY_PATH=secrets/jwt_private.pem
    JWT_PUBLIC_KEY_PATH=secrets/jwt_public.pem

Relies on ``cryptography`` (already a transitive dep via pyjwt[crypto]).
"""
import argparse
import os
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a dev RSA keypair for JWT RS256.")
    parser.add_argument("--bits", type=int, default=2048, help="RSA key size (default 2048).")
    parser.add_argument("--out-dir", default="secrets", help="Output directory (default ./secrets).")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    private_path = os.path.join(args.out_dir, "jwt_private.pem")
    public_path = os.path.join(args.out_dir, "jwt_public.pem")

    key = rsa.generate_private_key(public_exponent=65537, key_size=args.bits)

    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(private_path, "wb") as f:
        f.write(private_pem)
    with open(public_path, "wb") as f:
        f.write(public_pem)
    # Best-effort tighten perms on POSIX; no-op on Windows.
    try:
        os.chmod(private_path, 0o600)
    except OSError:
        pass

    print(f"Wrote {private_path}")
    print(f"Wrote {public_path}")
    print("\nSet in your .env:")
    print("  JWT_ALGORITHM=RS256")
    print(f"  JWT_PRIVATE_KEY_PATH={private_path}")
    print(f"  JWT_PUBLIC_KEY_PATH={public_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

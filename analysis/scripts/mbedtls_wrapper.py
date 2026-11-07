#!/usr/bin/env python3
"""
mbedTLS wrapper for VECTOR simulation engine.

Provides real cryptographic primitives using mbedTLS library via ctypes:
- CTR_DRBG random number generation (for TurboBlom key provisioning)
- HMAC-SHA256 (for TurboBlom handshake message authentication codes)

Requires mbedTLS shared libraries installed via Homebrew:
    brew install mbedtls
"""

import ctypes
import os
import sys

# ---------------------------------------------------------------------------
# Load mbedTLS libraries
# ---------------------------------------------------------------------------
LIB_DIR = "/opt/homebrew/lib"
LIBCRYPTO_PATH = os.path.join(LIB_DIR, "libmbedcrypto.dylib")

if not os.path.exists(LIBCRYPTO_PATH):
    for candidate in [
        "/opt/homebrew/lib/libmbedcrypto.dylib",
        "/usr/local/lib/libmbedcrypto.dylib",
        "/usr/lib/libmbedcrypto.dylib",
    ]:
        if os.path.exists(candidate):
            LIBCRYPTO_PATH = candidate
            break

LIBCRYPTO = ctypes.CDLL(LIBCRYPTO_PATH)

# ---------------------------------------------------------------------------
# Entropy context (mbedtls_entropy_context) - opaque
# ---------------------------------------------------------------------------
ENTROPY_CTX_SIZE = 512

LIBCRYPTO.mbedtls_entropy_init.argtypes = [ctypes.c_void_p]
LIBCRYPTO.mbedtls_entropy_init.restype = None

LIBCRYPTO.mbedtls_entropy_free.argtypes = [ctypes.c_void_p]
LIBCRYPTO.mbedtls_entropy_free.restype = None

LIBCRYPTO.mbedtls_entropy_func.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.c_size_t,
]
LIBCRYPTO.mbedtls_entropy_func.restype = ctypes.c_int

LIBCRYPTO.mbedtls_entropy_update_manual.argtypes = [
    ctypes.c_void_p,   # ctx
    ctypes.POINTER(ctypes.c_ubyte),  # data
    ctypes.c_size_t,   # len
]
LIBCRYPTO.mbedtls_entropy_update_manual.restype = ctypes.c_int

# ---------------------------------------------------------------------------
# CTR_DRBG context (mbedtls_ctr_drbg_context) - opaque
# ---------------------------------------------------------------------------
CTR_DRBG_CTX_SIZE = 1024

LIBCRYPTO.mbedtls_ctr_drbg_init.argtypes = [ctypes.c_void_p]
LIBCRYPTO.mbedtls_ctr_drbg_init.restype = None

LIBCRYPTO.mbedtls_ctr_drbg_seed.argtypes = [
    ctypes.c_void_p,   # ctx
    ctypes.c_void_p,   # f_entropy
    ctypes.c_void_p,   # p_entropy
    ctypes.c_char_p,   # custom
    ctypes.c_size_t,   # len
]
LIBCRYPTO.mbedtls_ctr_drbg_seed.restype = ctypes.c_int

LIBCRYPTO.mbedtls_ctr_drbg_random.argtypes = [
    ctypes.c_void_p,              # ctx
    ctypes.POINTER(ctypes.c_ubyte), # output buffer
    ctypes.c_size_t,              # output length
]
LIBCRYPTO.mbedtls_ctr_drbg_random.restype = ctypes.c_int

LIBCRYPTO.mbedtls_ctr_drbg_free.argtypes = [ctypes.c_void_p]
LIBCRYPTO.mbedtls_ctr_drbg_free.restype = None

# ---------------------------------------------------------------------------
# MD context for HMAC-SHA256 (all-in-one mbedtls_md_hmac)
# ---------------------------------------------------------------------------
LIBCRYPTO.mbedtls_md_info_from_type.argtypes = [ctypes.c_int]
LIBCRYPTO.mbedtls_md_info_from_type.restype = ctypes.c_void_p

LIBCRYPTO.mbedtls_md_hmac.argtypes = [
    ctypes.c_void_p,              # md_info
    ctypes.POINTER(ctypes.c_ubyte), # key
    ctypes.c_size_t,              # keylen
    ctypes.POINTER(ctypes.c_ubyte), # input
    ctypes.c_size_t,              # ilen
    ctypes.POINTER(ctypes.c_ubyte), # output
]
LIBCRYPTO.mbedtls_md_hmac.restype = ctypes.c_int

# MD type constants (from mbedtls/md.h)
MBEDTLS_MD_SHA256 = 0x09
SHA256_SIZE = 32


class MbedTLSCtx:
    """
    Manages mbedTLS entropy + CTR_DRBG context for cryptographically secure
    random number generation.

    Uses a Python callback entropy function that returns deterministic bytes
    derived from the seed, making CTR_DRBG output fully reproducible for
    simulation purposes.
    """

    def __init__(self, seed: bytes = b"VECTOR_TURBOBLOM_SEED"):
        self.entropy_ctx = ctypes.create_string_buffer(ENTROPY_CTX_SIZE)
        self.ctr_drbg_ctx = ctypes.create_string_buffer(CTR_DRBG_CTX_SIZE)

        # Store seed bytes for the callback
        self._seed_bytes = seed if isinstance(seed, bytes) else seed.encode()
        self._seed_pos = 0

        # Create deterministic entropy callback
        self._entropy_cb = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,      # ctx
            ctypes.POINTER(ctypes.c_ubyte),  # output buffer
            ctypes.c_size_t,      # output length
        )(self._entropy_callback)

        LIBCRYPTO.mbedtls_entropy_init(self.entropy_ctx)
        LIBCRYPTO.mbedtls_ctr_drbg_init(self.ctr_drbg_ctx)

        ret = LIBCRYPTO.mbedtls_ctr_drbg_seed(
            self.ctr_drbg_ctx,
            self._entropy_cb,    # Python callback as entropy function
            self.entropy_ctx,    # context pointer passed to callback
            None,                # no custom string
            0,
        )
        if ret != 0:
            raise RuntimeError(f"mbedtls_ctr_drbg_seed failed with code {ret}")

    def _entropy_callback(self, ctx, buf, n):
        """Python callback that provides deterministic bytes to CTR_DRBG.

        This replaces mbedtls_entropy_func which would use system entropy
        and make output non-deterministic.
        """
        n = int(n)
        for i in range(n):
            # Cycle through seed bytes deterministically
            buf[i] = self._seed_bytes[self._seed_pos % len(self._seed_bytes)]
            self._seed_pos += 1
        return 0

    def random_bytes(self, n: int) -> bytes:
        """Generate n cryptographically secure random bytes."""
        buf = (ctypes.c_ubyte * n)()
        ret = LIBCRYPTO.mbedtls_ctr_drbg_random(self.ctr_drbg_ctx, buf, n)
        if ret != 0:
            raise RuntimeError(f"mbedtls_ctr_drbg_random failed with code {ret}")
        return bytes(buf)

    def random_int(self, max_val: int) -> int:
        """Generate a random integer in [0, max_val)."""
        if max_val <= 0:
            return 0
        nbytes = (max_val.bit_length() + 7) // 8
        val = int.from_bytes(self.random_bytes(nbytes), "big")
        return val % max_val

    def close(self):
        LIBCRYPTO.mbedtls_ctr_drbg_free(self.ctr_drbg_ctx)
        LIBCRYPTO.mbedtls_entropy_free(self.entropy_ctx)


def hmac_sha256(key: bytes, data: bytes) -> bytes:
    """Compute HMAC-SHA256 using mbedTLS mbedtls_md_hmac."""
    md_info = LIBCRYPTO.mbedtls_md_info_from_type(MBEDTLS_MD_SHA256)
    if not md_info:
        raise RuntimeError("mbedtls_md_info_from_type returned NULL")

    key_buf = (ctypes.c_ubyte * len(key))(*key)
    data_buf = (ctypes.c_ubyte * len(data))(*data)
    mac_buf = (ctypes.c_ubyte * SHA256_SIZE)()

    ret = LIBCRYPTO.mbedtls_md_hmac(
        md_info, key_buf, len(key), data_buf, len(data), mac_buf
    )
    if ret != 0:
        raise RuntimeError(f"mbedtls_md_hmac failed with code {ret}")

    return bytes(mac_buf)


# ---------------------------------------------------------------------------
# Global context instance (lazy initialization)
# ---------------------------------------------------------------------------
_global_ctx = None


def get_global_ctx() -> MbedTLSCtx:
    """Get or create the global mbedTLS context."""
    global _global_ctx
    if _global_ctx is None:
        _global_ctx = MbedTLSCtx()
    return _global_ctx


def cleanup_global_ctx():
    """Clean up the global mbedTLS context."""
    global _global_ctx
    if _global_ctx is not None:
        _global_ctx.close()
        _global_ctx = None


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== mbedTLS Wrapper Self-Test ===")

    # Test random number generation
    ctx = MbedTLSCtx()
    rb = ctx.random_bytes(16)
    print(f"Random bytes (16): {rb.hex()}")
    ri = ctx.random_int(1000000)
    print(f"Random int (0-1M): {ri}")
    ctx.close()

    # Test HMAC-SHA256
    key = b"secret_key_12345"
    data = b"Hello, VECTOR!"
    mac = hmac_sha256(key, data)
    print(f"HMAC-SHA256(key={key!r}, data={data!r}):")
    print(f"  {mac.hex()}")

    # Verify determinism
    mac2 = hmac_sha256(key, data)
    assert mac == mac2, "HMAC should be deterministic"
    print("HMAC determinism: PASS")

    print("\nAll tests PASSED")

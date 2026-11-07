#!/usr/bin/env python3
"""
Build script for crypto_benchmark.cpp

Builds a C++ benchmark comparing pure C++ crypto vs mbedTLS crypto.
"""

import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CPP_FILE = os.path.join(SCRIPT_DIR, "crypto_benchmark.cpp")
BIN_FILE = os.path.join(SCRIPT_DIR, "crypto_benchmark")

MBEDTLS_LIB = "/opt/homebrew/lib/libmbedcrypto.dylib"
MBEDTLS_INC = "/opt/homebrew/include"

def build():
    """Build the crypto benchmark C++ program."""
    if not os.path.exists(CPP_FILE):
        print(f"ERROR: {CPP_FILE} not found")
        return False

    cmd = [
        "g++", "-std=c++17", "-O2",
        "-I", MBEDTLS_INC,
        "-o", BIN_FILE,
        CPP_FILE,
        "-L", "/opt/homebrew/lib",
        "-lmbedcrypto",
    ]

    print(f"Building: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}")
        return False

    print(f"Build successful: {BIN_FILE}")
    return True


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)

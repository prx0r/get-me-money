#!/usr/bin/env python3
"""patala/hashing.py — UUIDv7 + DigestSet + three hash types + JCS canonicalization.

Implements the newbuild1 spec §2-5:
- UUIDv7 for entity IDs (time-ordered, distributed)
- DigestSet with algorithm-tagged digests (crypto agility)
- Three hash types: raw-byte, canonical JCS, semantic fingerprint
- RFC 8785 JCS canonicalization for structured data

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

# Use proper uuid7 library (RFC 9562)
try:
    from uuid6 import uuid7 as _uuid7
except ImportError:
    # Fallback: generate time-ordered UUID manually
    import uuid
    def _uuid7() -> uuid.UUID:
        ts_ms = int(time.time() * 1000)
        time_bits = ts_ms & 0xFFFFFFFFFFFF
        rand_bits = uuid.uuid4().int & 0x3FFFFFFFFFFFFFFFFFFFF
        int_val = (time_bits << 74) | rand_bits
        int_val = (int_val & ~(0xF << 76)) | (0x7 << 76)
        int_val = (int_val & ~(0x3 << 62)) | (0x2 << 62)
        return uuid.UUID(int=int_val)


# --- UUIDv7 (RFC 9562) ---

def uuid7() -> str:
    """Generate a UUIDv7 — time-ordered, distributed, better index locality than UUIDv4.

    RFC 9562 recommends UUIDv7 for new time-ordered UUID use cases.
    Returns full 128-bit UUID as string (no truncation).
    """
    return str(_uuid7())


def uuid7_batch(count: int) -> list[str]:
    """Generate a batch of UUIDv7s."""
    return [uuid7() for _ in range(count)]


# --- DigestSet (algorithm-tagged digests) ---

def make_digest(data: bytes, algorithm: str = "sha512",
                canonicalization: str | None = None) -> dict:
    """Create a single Digest with algorithm tag.

    Per newbuild1 §3: "Every thing that can have bytes gets a DigestSet."
    """
    if algorithm == "sha256":
        value = hashlib.sha256(data).hexdigest()
    elif algorithm == "sha512":
        value = hashlib.sha512(data).hexdigest()
    elif algorithm == "blake2b-512":
        value = hashlib.blake2b(data, digest_size=64).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    return {
        "algorithm": algorithm,
        "value": value,
        "encoding": "hex",
        "canonicalization": canonicalization,
    }


def make_digest_set(data: bytes, algorithms: list[str] | None = None) -> dict:
    """Create a DigestSet with multiple algorithm-tagged digests.

    Per newbuild1 §3: crypto agility — if SHA-512 is broken, add a new algorithm
    without changing the Artifact ID.
    """
    if algorithms is None:
        algorithms = ["sha256", "sha512"]

    digests = [make_digest(data, algo) for algo in algorithms]
    return {"digests": digests}


# --- Three hash types (newbuild1 §4) ---

def raw_byte_hash(data: bytes, algorithm: str = "sha512") -> dict:
    """A. Raw-byte hash — hash exactly what came from the provider.

    Per newbuild1 §4A: "No decoding. No NFC. No whitespace changes.
    No fixing line endings. This proves: these are the exact bytes Pāṭala observed."
    """
    return make_digest(data, algorithm, canonicalization=None)


def canonical_jcs_hash(obj: Any, algorithm: str = "sha512") -> dict:
    """B. Canonical structured-record hash — RFC 8785 JCS canonicalization.

    Per newbuild1 §4B: "JSON has multiple byte representations of the same object.
    Use RFC 8785 JCS for deterministic hashing."
    """
    import rfc8785
    canonical = rfc8785.dumps(obj)  # Returns bytes
    return make_digest(canonical, algorithm, canonicalization="jcs-rfc8785")


def semantic_fingerprint(text: str, algorithm: str = "sha256") -> dict:
    """C. Semantic/normalized text fingerprint — for duplicate detection.

    Per newbuild1 §4C: "Unicode NFC + Sanskrit punctuation normalization +
    spacing normalization + transliteration normalization."
    """
    normalized = normalize_sanskrit_text(text)
    data = normalized.encode("utf-8")
    return make_digest(data, algorithm, canonicalization="sanskrit-normalized-v3")


# --- RFC 8785 JCS Canonicalization ---

def jcs_canonicalize(obj: Any) -> str:
    """RFC 8785 JSON Canonicalization Scheme.

    Per RFC 8785:
    - No whitespace between tokens
    - Deterministic serialization of primitives (ECMAScript rules)
    - Object properties sorted lexicographically (UTF-16 code units)
    - UTF-8 output
    """
    return _jcs_serialize(obj)


def _jcs_serialize(obj: Any) -> str:
    """Serialize according to JCS rules."""
    if obj is None:
        return "null"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, (int, float)):
        return _jcs_serialize_number(obj)
    elif isinstance(obj, str):
        return _jcs_serialize_string(obj)
    elif isinstance(obj, list):
        items = [_jcs_serialize(item) for item in obj]
        return "[" + ",".join(items) + "]"
    elif isinstance(obj, dict):
        # Sort keys lexicographically (JCS requirement)
        sorted_keys = sorted(obj.keys())
        items = []
        for key in sorted_keys:
            items.append(_jcs_serialize_string(key) + ":" + _jcs_serialize(obj[key]))
        return "{" + ",".join(items) + "}"
    else:
        raise TypeError(f"Cannot JCS-serialize type {type(obj)}")


def _jcs_serialize_number(obj: int | float) -> str:
    """ECMAScript-compatible number serialization."""
    if isinstance(obj, int):
        return str(obj)
    # Float serialization per ECMAScript
    if obj != obj:  # NaN
        raise ValueError("NaN not allowed in JSON")
    if obj == float("inf"):
        raise ValueError("Infinity not allowed in JSON")
    if obj == float("-inf"):
        raise ValueError("-Infinity not allowed in JSON")
    # Use repr for deterministic output, then clean up
    s = repr(obj)
    # Ensure lowercase 'e' for scientific notation
    s = s.replace("E", "e").replace("E+", "e+").replace("E-", "e-")
    return s


def _jcs_serialize_string(s: str) -> str:
    """Serialize a string according to JCS/ECMAScript rules."""
    result = ['"']
    for ch in s:
        cp = ord(ch)
        if ch == '\\':
            result.append('\\\\')
        elif ch == '"':
            result.append('\\"')
        elif ch == '\n':
            result.append('\\n')
        elif ch == '\r':
            result.append('\\r')
        elif ch == '\t':
            result.append('\\t')
        elif ch == '\b':
            result.append('\\b')
        elif ch == '\f':
            result.append('\\f')
        elif cp < 0x20:
            # Control characters: \uhhhh
            result.append(f'\\u{cp:04x}')
        else:
            result.append(ch)
    result.append('"')
    return "".join(result)


# --- Sanskrit text normalization (newbuild1 §5) ---

def normalize_sanskrit_text(text: str) -> str:
    """Normalize Sanskrit text for semantic fingerprinting.

    Per newbuild1 §5: "Unicode NFC + Sanskrit punctuation normalization +
    spacing normalization + transliteration normalization."

    This is a deterministic transformation that leaves an inspectable trail.
    """
    import unicodedata

    # Step 1: Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", text)

    # Step 2: Strip leading/trailing whitespace
    normalized = normalized.strip()

    # Step 3: Collapse multiple whitespace to single space
    import re
    normalized = re.sub(r'\s+', ' ', normalized)

    # Step 4: Normalize common Sanskrit punctuation
    # Devanagari danda (।) and double danda (॥)
    normalized = normalized.replace('॥', '|')
    normalized = normalized.replace('।', '|')

    # Step 5: Normalize Devanagari digits to ASCII
    devanagari_digits = '०१२३४५६७८९'
    for i, d in enumerate(devanagari_digits):
        normalized = normalized.replace(d, str(i))

    return normalized


# --- Convenience functions ---

def make_artifact_id() -> str:
    """Generate an Artifact ID with prefix."""
    return f"PTART_{uuid7()}"


def make_entity_id(prefix: str = "PTW") -> str:
    """Generate an entity ID with prefix.

    Per newbuild1 §2: "Prefix = convenience. UUID = identity."
    """
    return f"{prefix}_{uuid7()}"


def make_observation_id() -> str:
    """Generate an observation ID."""
    return f"PTOBS_{uuid7()}"


def make_assertion_id() -> str:
    """Generate an assertion ID."""
    return f"PTCAS_{uuid7()}"


if __name__ == "__main__":
    # Demo
    print("=== UUIDv7 ===")
    for _ in range(3):
        print(f"  {uuid7()}")

    print("\n=== DigestSet ===")
    data = b"Hello, Patala!"
    ds = make_digest_set(data)
    for d in ds["digests"]:
        print(f"  {d['algorithm']}: {d['value'][:32]}...")

    print("\n=== Three hash types ===")
    raw = raw_byte_hash(data)
    print(f"  Raw: {raw['value'][:32]}...")

    obj = {"x": 1, "y": 2, "z": [3, 4, 5]}
    jcs = canonical_jcs_hash(obj)
    print(f"  JCS: {jcs['value'][:32]}...")

    text = "nāgārjuna's vigrahavyāvartanī"
    fp = semantic_fingerprint(text)
    print(f"  Semantic: {fp['value'][:32]}...")

    print("\n=== JCS Canonicalization ===")
    print(f"  Input:  {obj}")
    print(f"  Output: {jcs_canonicalize(obj)}")

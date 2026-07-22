import hashlib
import os

try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False


class VerifyEngine:
    """
    Verification Engine supporting MD5, XXHash64, SHA-256, and Size-only.
    """

    ALGORITHMS = ["MD5", "XXHash64", "SHA-256", "Size-only"]

    @classmethod
    def is_algorithm_available(cls, algorithm: str) -> bool:
        """Check if the requested algorithm is available on this system."""
        algo = algorithm.upper().strip()
        if algo in ("XXHASH64", "XXHASH", "XXH64", "XXH3"):
            return HAS_XXHASH
        return algo in ("MD5", "SHA-256", "SHA256", "SIZE-ONLY")

    @staticmethod
    def create_hasher(algorithm: str):
        algo = algorithm.upper().strip()
        if algo == "MD5":
            return hashlib.md5()
        elif algo in ("XXHASH64", "XXHASH", "XXH64", "XXH3"):
            if HAS_XXHASH:
                return xxhash.xxh64()
            else:
                raise ImportError(
                    f"xxhash library is required for {algorithm}. "
                    "Install it with: pip install xxhash"
                )
        elif algo in ("SHA-256", "SHA256"):
            return hashlib.sha256()
        elif algo == "SIZE-ONLY":
            return None
        else:
            raise ValueError(f"Unknown hash algorithm: {algorithm}")

    @classmethod
    def compute_file_hash(cls, filepath: str, algorithm: str = "MD5", buffer_size: int = 64 * 1024 * 1024, callback=None) -> str:
        """
        Computes hash of an existing file.
        """
        algo = algorithm.upper().strip()
        if algo == "SIZE-ONLY":
            return str(os.path.getsize(filepath))

        hasher = cls.create_hasher(algorithm)
        if not hasher:
            return str(os.path.getsize(filepath))

        with open(filepath, "rb") as f:
            while chunk := f.read(buffer_size):
                hasher.update(chunk)
                if callback:
                    callback(len(chunk))

        return hasher.hexdigest()

    @classmethod
    def verify_copy(cls, source_hash: str, dest_hash: str, algorithm: str = "MD5") -> bool:
        """
        Compares source hash against destination hash.
        """
        return source_hash.strip().lower() == dest_hash.strip().lower()

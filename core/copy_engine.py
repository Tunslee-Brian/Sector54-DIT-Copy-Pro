import os
import time
import json
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable, Optional
from core.token_parser import TokenParser
from core.directory_builder import DirectoryBuilder
from core.verify_engine import VerifyEngine


def _advise_dontneed(fd: int):
    """Bypasses OS Page Cache on Linux to prevent RAM saturation when copying massive media files."""
    if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        except Exception:
            pass


class CopyEngine:
    """
    High-performance Copy & Verification Engine for DIT Copy Pro.
    Supports single-pass reading, simultaneous multi-destination writing,
    multi-algorithm checksum verification, real-time speed calculation,
    and session resume.
    """

    def __init__(
        self,
        source_dir: str,
        destinations: List[str],
        token_parser: TokenParser,
        directory_builder: DirectoryBuilder,
        hash_algorithm: str = "MD5",
        buffer_size_mb: int = 64,
        project_name: str = "Project",
        session_file: Optional[str] = None
    ):
        self.source_dir = os.path.abspath(source_dir)
        self.destinations = [os.path.abspath(d) for d in destinations if d and d.strip()]
        self.token_parser = token_parser
        self.directory_builder = directory_builder
        self.hash_algorithm = hash_algorithm
        self.buffer_size = max(1, buffer_size_mb) * 1024 * 1024
        self.project_name = project_name

        if not VerifyEngine.is_algorithm_available(hash_algorithm):
            raise ImportError(
                f"Hash algorithm '{hash_algorithm}' is not available. "
                f"Available algorithms: {', '.join(VerifyEngine.ALGORITHMS)}"
            )
        if session_file:
            self.session_file = session_file
        elif self.destinations:
            self.session_file = os.path.join(self.destinations[0], ".dit_copy_session.json")
        else:
            cache_dir = os.path.expanduser("~/.cache/dit_copy_pro")
            os.makedirs(cache_dir, exist_ok=True)
            self.session_file = os.path.join(cache_dir, ".dit_copy_session.json")

        self.cancel_requested = False
        self.is_running = False
        self._progress_lock = threading.Lock()

        self.file_list: List[Dict] = []
        self.extra_files: List[Dict] = []
        self.total_bytes = 0
        self.copied_bytes = 0
        self.start_time = 0.0
        self.end_time = 0.0

    def scan_source(self) -> List[Dict]:
        """
        Scans source directory and builds the list of files to process.
        """
        self.file_list = []
        self.total_bytes = 0
        self.folder_count = 0

        if not os.path.exists(self.source_dir):
            return self.file_list

        session_state = self._load_session_state()

        if os.path.isfile(self.source_dir):
            filename = os.path.basename(self.source_dir)
            rel_path = filename
            file_size = os.path.getsize(self.source_dir)

            tokens = self.token_parser.parse(filename, fallback_project=self.project_name)
            dest_paths = self.directory_builder.build_paths_for_all_destinations(
                self.destinations, tokens, filename
            )

            cached_status = session_state.get(rel_path, {}).get("status", "QUEUED")
            cached_source_hash = session_state.get(rel_path, {}).get("source_hash", "")
            cached_dest_hashes = session_state.get(rel_path, {}).get("dest_hashes", {})
            cached_shot_time = session_state.get(rel_path, {}).get("shot_time", "")

            file_info = {
                "rel_path": rel_path,
                "filename": filename,
                "source_path": self.source_dir,
                "dest_paths": dest_paths,
                "size": file_size,
                "tokens": tokens,
                "status": cached_status,
                "source_hash": cached_source_hash,
                "dest_hashes": cached_dest_hashes,
                "shot_time": cached_shot_time,
                "error_msg": ""
            }

            self.file_list.append(file_info)
            self.total_bytes += file_size
            self.folder_count = 0
            return self.file_list

        dirs_set = set()
        for root, dirs, files in os.walk(self.source_dir):
            for d in dirs:
                dirs_set.add(os.path.join(root, d))
            for filename in sorted(files):
                # Ignore hidden files / metadata files
                if filename.startswith(".") or filename.endswith((".DS_Store", "desktop.ini")):
                    continue

                full_source_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_source_path, self.source_dir)
                file_size = os.path.getsize(full_source_path)

                tokens = self.token_parser.parse(filename, fallback_project=self.project_name)
                dest_paths = self.directory_builder.build_paths_for_all_destinations(
                    self.destinations, tokens, filename
                )

                # Check if already verified in session
                cached_status = session_state.get(rel_path, {}).get("status", "QUEUED")
                cached_source_hash = session_state.get(rel_path, {}).get("source_hash", "")
                cached_dest_hashes = session_state.get(rel_path, {}).get("dest_hashes", {})
                cached_shot_time = session_state.get(rel_path, {}).get("shot_time", "")

                file_info = {
                    "rel_path": rel_path,
                    "filename": filename,
                    "source_path": full_source_path,
                    "dest_paths": dest_paths,
                    "size": file_size,
                    "tokens": tokens,
                    "status": cached_status,  # QUEUED, COPYING, VERIFIED, FAILED
                    "source_hash": cached_source_hash,
                    "dest_hashes": cached_dest_hashes,
                    "shot_time": cached_shot_time,
                    "error_msg": ""
                }

                self.file_list.append(file_info)
                self.total_bytes += file_size

        self.folder_count = len(dirs_set)
        return self.file_list

    def run_copy_session(
        self,
        on_file_start: Optional[Callable[[Dict], None]] = None,
        on_file_progress: Optional[Callable[[Dict, int, float, float], None]] = None,
        on_file_complete: Optional[Callable[[Dict], None]] = None,
        on_session_complete: Optional[Callable[[Dict], None]] = None,
        metadata_reader_func: Optional[Callable[[str], str]] = None
    ) -> Dict:
        """
        Executes the copy & verification workflow for all queued files.
        Single-pass read, simultaneous N-destination write.
        """
        self.is_running = True
        self.cancel_requested = False
        self.start_time = time.time()
        self.copied_bytes = 0

        # Account for already verified bytes in session
        for f in self.file_list:
            if f["status"] == "VERIFIED":
                self.copied_bytes += f["size"]

        verified_count = 0
        failed_count = 0

        for file_info in self.file_list:
            if self.cancel_requested:
                break

            # If already verified in previous session, skip copy
            if file_info["status"] == "VERIFIED":
                verified_count += 1
                if on_file_complete:
                    on_file_complete(file_info)
                continue

            file_info["status"] = "COPYING"
            if on_file_start:
                on_file_start(file_info)

            # Read shot metadata if available
            if metadata_reader_func and not file_info.get("shot_time"):
                try:
                    file_info["shot_time"] = metadata_reader_func(file_info["source_path"])
                except Exception:
                    file_info["shot_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(file_info["source_path"])))

            success = self._copy_single_file(
                file_info,
                on_file_progress
            )

            if success:
                file_info["status"] = "VERIFIED"
                verified_count += 1
            else:
                file_info["status"] = "FAILED"
                failed_count += 1

            self._save_file_session_state(file_info)

            if on_file_complete:
                on_file_complete(file_info)

        self.end_time = time.time()
        self.is_running = False

        self.scan_extra_destination_files()
        elapsed = max(0.1, self.end_time - self.start_time)
        avg_speed = self.copied_bytes / elapsed

        summary = {
            "total_files": len(self.file_list),
            "verified": verified_count,
            "failed": failed_count,
            "extra_files": self.extra_files,
            "extra_count": len(self.extra_files),
            "total_bytes": self.total_bytes,
            "copied_bytes": self.copied_bytes,
            "elapsed_seconds": elapsed,
            "avg_speed_bytes_sec": avg_speed,
            "cancelled": self.cancel_requested
        }

        if on_session_complete:
            on_session_complete(summary)

        return summary

    def scan_extra_destination_files(self) -> List[Dict]:
        """
        Scans destination directories for extra/orphan files not present in the source card list.
        """
        self.extra_files = []
        expected_dest_paths = set()
        for f in self.file_list:
            for dst in f.get("dest_paths", []):
                expected_dest_paths.add(os.path.normpath(dst))

        for dest_root in self.destinations:
            if not os.path.exists(dest_root):
                continue
            for root, _, files in os.walk(dest_root):
                for filename in sorted(files):
                    if filename.startswith(".") or filename.endswith((".DS_Store", "desktop.ini", ".dit_copy_session.json")) or filename.startswith("DIT_Report_"):
                        continue
                    full_dest_path = os.path.normpath(os.path.join(root, filename))
                    if full_dest_path not in expected_dest_paths:
                        file_size = os.path.getsize(full_dest_path) if os.path.exists(full_dest_path) else 0
                        rel_path = os.path.relpath(full_dest_path, dest_root)
                        self.extra_files.append({
                            "dest_path": full_dest_path,
                            "rel_path": rel_path,
                            "filename": filename,
                            "size": file_size,
                            "status": "EXTRA"
                        })
        return self.extra_files

    def run_verify_only_session(
        self,
        on_file_start: Optional[Callable[[Dict], None]] = None,
        on_file_progress: Optional[Callable[[Dict, int, float, float], None]] = None,
        on_file_complete: Optional[Callable[[Dict], None]] = None,
        on_session_complete: Optional[Callable[[Dict], None]] = None,
        metadata_reader_func: Optional[Callable[[str], str]] = None
    ) -> Dict:
        """
        Executes a Standalone Verification-Only workflow (no copying).
        Verifies existing destination files against source files.
        """
        self.is_running = True
        self.cancel_requested = False
        self.start_time = time.time()
        self.copied_bytes = 0

        verified_count = 0
        failed_count = 0

        is_size_only = (self.hash_algorithm.upper() == "SIZE-ONLY")

        for file_info in self.file_list:
            if self.cancel_requested:
                break

            file_info["status"] = "COPYING"
            if on_file_start:
                on_file_start(file_info)

            # Read shot metadata if available
            if metadata_reader_func and not file_info.get("shot_time"):
                try:
                    file_info["shot_time"] = metadata_reader_func(file_info["source_path"])
                except Exception:
                    file_info["shot_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(file_info["source_path"])))

            src_path = file_info["source_path"]
            dest_paths = file_info["dest_paths"]
            file_size = file_info["size"]

            if not os.path.exists(src_path):
                file_info["status"] = "FAILED"
                file_info["error_msg"] = "Source file does not exist"
                failed_count += 1
                if on_file_complete:
                    on_file_complete(file_info)
                continue

            last_calc_time = time.time()
            bytes_since_last_calc = 0
            current_speed = 0.0

            def src_callback(chunk_len):
                nonlocal last_calc_time, bytes_since_last_calc, current_speed
                with self._progress_lock:
                    self.copied_bytes += chunk_len
                    bytes_since_last_calc += chunk_len
                    now = time.time()
                    dt = now - last_calc_time
                    if dt >= 0.5:
                        current_speed = bytes_since_last_calc / dt
                        last_calc_time = now
                        bytes_since_last_calc = 0
                    remaining_bytes = max(0, self.total_bytes - self.copied_bytes)
                    eta = remaining_bytes / current_speed if current_speed > 0 else 0.0
                    eff_speed = current_speed
                if on_file_progress:
                    on_file_progress(file_info, self.copied_bytes, eff_speed, eta)

            def dst_verify_callback(chunk_len):
                nonlocal last_calc_time, bytes_since_last_calc, current_speed
                with self._progress_lock:
                    bytes_since_last_calc += chunk_len
                    now = time.time()
                    dt = now - last_calc_time
                    if dt >= 0.5:
                        current_speed = bytes_since_last_calc / dt
                        last_calc_time = now
                        bytes_since_last_calc = 0
                    remaining_bytes = max(0, self.total_bytes - self.copied_bytes)
                    eta = remaining_bytes / current_speed if current_speed > 0 else 0.0
                    eff_speed = current_speed
                if on_file_progress:
                    on_file_progress(file_info, self.copied_bytes, eff_speed, eta)

            if is_size_only:
                source_hash = str(file_size)
            else:
                source_hash = VerifyEngine.compute_file_hash(src_path, self.hash_algorithm, self.buffer_size, callback=src_callback)

            file_info["source_hash"] = source_hash

            # Verify against destination files in parallel
            all_matched = True
            file_info["dest_hashes"] = {}

            def dst_verify_task(dst_path):
                if not os.path.exists(dst_path):
                    return dst_path, "MISSING", False, f"Destination file missing: {dst_path}"
                if is_size_only:
                    dst_h = str(os.path.getsize(dst_path))
                else:
                    dst_h = VerifyEngine.compute_file_hash(dst_path, self.hash_algorithm, self.buffer_size, callback=dst_verify_callback)
                matched = VerifyEngine.verify_copy(source_hash, dst_h, self.hash_algorithm)
                err = "" if matched else f"Checksum mismatch for destination: {dst_path}"
                return dst_path, dst_h, matched, err

            if len(dest_paths) == 1:
                dst, dst_h, matched, err = dst_verify_task(dest_paths[0])
                file_info["dest_hashes"][dst] = dst_h
                if not matched:
                    all_matched = False
                    file_info["error_msg"] = err
            else:
                with ThreadPoolExecutor(max_workers=min(4, len(dest_paths))) as executor:
                    futures = [executor.submit(dst_verify_task, dst) for dst in dest_paths]
                    for future in futures:
                        dst, dst_h, matched, err = future.result()
                        file_info["dest_hashes"][dst] = dst_h
                        if not matched:
                            all_matched = False
                            file_info["error_msg"] = err

            if all_matched:
                file_info["status"] = "VERIFIED"
                verified_count += 1
            else:
                file_info["status"] = "FAILED"
                failed_count += 1

            self._save_file_session_state(file_info)

            if on_file_complete:
                on_file_complete(file_info)

        self.end_time = time.time()
        self.is_running = False

        self.scan_extra_destination_files()
        elapsed = max(0.1, self.end_time - self.start_time)
        avg_speed = self.copied_bytes / elapsed

        summary = {
            "total_files": len(self.file_list),
            "verified": verified_count,
            "failed": failed_count,
            "extra_files": self.extra_files,
            "extra_count": len(self.extra_files),
            "total_bytes": self.total_bytes,
            "copied_bytes": self.copied_bytes,
            "elapsed_seconds": elapsed,
            "avg_speed_bytes_sec": avg_speed,
            "cancelled": self.cancel_requested,
            "mode": "VERIFY_ONLY"
        }

        if on_session_complete:
            on_session_complete(summary)

        return summary

    def _copy_single_file(
        self,
        file_info: Dict,
        on_file_progress: Optional[Callable[[Dict, int, float, float], None]]
    ) -> bool:
        src_path = file_info["source_path"]
        dest_paths = file_info["dest_paths"]
        file_size = file_info["size"]

        if not os.path.exists(src_path):
            file_info["error_msg"] = "Source file does not exist"
            return False

        # Ensure destination directories exist
        for dst in dest_paths:
            self.directory_builder.ensure_directory_exists(dst)

        # Handle size-only algorithm
        is_size_only = (self.hash_algorithm.upper() == "SIZE-ONLY")
        source_hasher = VerifyEngine.create_hasher(self.hash_algorithm)

        # Open source file and destination files
        src_file = None
        dest_files = []
        try:
            src_file = open(src_path, "rb")
            for dst in dest_paths:
                dest_files.append(open(dst, "wb"))

            file_bytes_read = 0
            last_calc_time = time.time()
            bytes_since_last_calc = 0
            current_speed = 0.0

            # Producer Thread for Async Reading from Source Card
            chunk_queue = queue.Queue(maxsize=16)

            def reader_worker():
                try:
                    while not self.cancel_requested:
                        chunk = src_file.read(self.buffer_size)
                        if not chunk:
                            chunk_queue.put(None)
                            break
                        _advise_dontneed(src_file.fileno())
                        chunk_queue.put(chunk)
                except Exception as ex:
                    chunk_queue.put(ex)

            reader_thread = threading.Thread(target=reader_worker, daemon=True)
            reader_thread.start()

            while True:
                if self.cancel_requested:
                    file_info["error_msg"] = "User cancelled process"
                    break

                item = chunk_queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item

                chunk = item

                # Update source hash in single pass
                if source_hasher:
                    source_hasher.update(chunk)

                # Write chunk simultaneously to all destination files
                for dst_f in dest_files:
                    dst_f.write(chunk)
                    _advise_dontneed(dst_f.fileno())

                chunk_len = len(chunk)
                file_bytes_read += chunk_len
                self.copied_bytes += chunk_len
                bytes_since_last_calc += chunk_len

                # Speed and ETA calculation
                now = time.time()
                dt = now - last_calc_time
                if dt >= 0.5:
                    current_speed = bytes_since_last_calc / dt
                    last_calc_time = now
                    bytes_since_last_calc = 0

                remaining_bytes = max(0, self.total_bytes - self.copied_bytes)
                eta_seconds = remaining_bytes / current_speed if current_speed > 0 else 0.0

                if on_file_progress:
                    on_file_progress(file_info, file_bytes_read, current_speed, eta_seconds)

            reader_thread.join(timeout=5.0)

        except Exception as e:
            file_info["error_msg"] = str(e)
            self._cleanup_partial_files(dest_paths)
            return False
        finally:
            if src_file and not src_file.closed:
                src_file.close()
            for dst_f in dest_files:
                if not dst_f.closed:
                    dst_f.close()

        if self.cancel_requested:
            self._cleanup_partial_files(dest_paths)
            return False

        # Get Source Hash
        if is_size_only:
            file_info["source_hash"] = str(file_size)
        else:
            file_info["source_hash"] = source_hasher.hexdigest()

        # Compute & Verify Destination Hashes in Parallel
        all_matched = True
        file_info["dest_hashes"] = {}

        def dst_callback(chunk_len):
            nonlocal last_calc_time, bytes_since_last_calc, current_speed
            with self._progress_lock:
                bytes_since_last_calc += chunk_len
                now = time.time()
                dt = now - last_calc_time
                if dt >= 0.5:
                    current_speed = bytes_since_last_calc / dt
                    last_calc_time = now
                    bytes_since_last_calc = 0
                
                elapsed_total = max(0.1, now - self.start_time)
                avg_speed = self.copied_bytes / elapsed_total
                effective_speed = max(current_speed, avg_speed)
                remaining_bytes = max(0, self.total_bytes - self.copied_bytes)
                eta = remaining_bytes / effective_speed if effective_speed > 0 else 0.0

            if on_file_progress:
                on_file_progress(file_info, file_bytes_read, effective_speed, eta)

        def verify_dst_task(dst_path):
            if is_size_only:
                dst_size = os.path.getsize(dst_path) if os.path.exists(dst_path) else 0
                dst_hash = str(dst_size)
            else:
                dst_hash = VerifyEngine.compute_file_hash(dst_path, self.hash_algorithm, self.buffer_size, callback=dst_callback)
            matched = VerifyEngine.verify_copy(file_info["source_hash"], dst_hash, self.hash_algorithm)
            err = "" if matched else f"Checksum mismatch for destination: {dst_path}"
            return dst_path, dst_hash, matched, err

        if len(dest_paths) == 1:
            dst, dst_hash, matched, err = verify_dst_task(dest_paths[0])
            file_info["dest_hashes"][dst] = dst_hash
            if not matched:
                all_matched = False
                file_info["error_msg"] = err
        else:
            with ThreadPoolExecutor(max_workers=min(4, len(dest_paths))) as executor:
                futures = [executor.submit(verify_dst_task, dst) for dst in dest_paths]
                for future in futures:
                    dst, dst_hash, matched, err = future.result()
                    file_info["dest_hashes"][dst] = dst_hash
                    if not matched:
                        all_matched = False
                        file_info["error_msg"] = err

        if not all_matched:
            self._cleanup_partial_files(dest_paths)

        return all_matched

    def _cleanup_partial_files(self, dest_paths: List[str]):
        """Removes incomplete or corrupted destination files when copy fails or is cancelled."""
        for dst in dest_paths:
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass

    def cancel(self):
        self.cancel_requested = True

    def _load_session_state(self) -> Dict:
        if self.session_file and os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_file_session_state(self, file_info: Dict):
        if not self.session_file:
            return
        try:
            session_dir = os.path.dirname(os.path.abspath(self.session_file))
            os.makedirs(session_dir, exist_ok=True)
            state = self._load_session_state()
            state[file_info["rel_path"]] = {
                "status": file_info["status"],
                "source_hash": file_info["source_hash"],
                "dest_hashes": file_info["dest_hashes"],
                "shot_time": file_info["shot_time"]
            }
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

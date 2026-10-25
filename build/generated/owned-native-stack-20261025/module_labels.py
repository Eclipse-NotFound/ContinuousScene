"""Offline exact-export labels for saved native IP observations; JSON stdout only.

No process APIs, DbgHelp, PDB, symbol downloads, import of runner or adapter.
Only recorded local PE paths are read. A name requires the containing x64
RUNTIME_FUNCTION.BeginAddress == an actual, nonforwarded export address.
Reference: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import struct

MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_ENTRIES = 1_000_000


def number(value):
    return int(value, 0) if isinstance(value, str) else int(value)


class PE:
    def __init__(self, data):
        self.data = data
        if self.read(0, 2) != b"MZ":
            raise ValueError("not MZ")
        pe = self.u32(60)
        if self.read(pe, 4) != b"PE\0\0":
            raise ValueError("not PE")
        machine, section_count = struct.unpack("<HH", self.read(pe + 4, 4))
        optional_size = struct.unpack("<H", self.read(pe + 20, 2))[0]
        optional = pe + 24
        if machine != 0x8664 or self.read(optional, 2) != b"\x0b\x02":
            raise ValueError("not AMD64 PE32+")
        if optional_size < 112 or not 1 <= section_count <= 96:
            raise ValueError("unsupported PE header dimensions")
        self.size_of_image = self.u32(optional + 56)
        self.header_size = self.u32(optional + 60)
        directory_count = self.u32(optional + 108)
        if directory_count > (optional_size - 112) // 8:
            raise ValueError("directories exceed optional header")
        self.directories = [struct.unpack("<II", self.read(optional + 112 + i * 8, 8))
                            for i in range(directory_count)]
        self.sections = []
        for i in range(section_count):
            sh = optional + optional_size + 40 * i
            vs, va, raw_size, raw_at = struct.unpack("<IIII", self.read(sh + 8, 16))
            flags = self.u32(sh + 36)
            if va + max(vs, raw_size) > self.size_of_image:
                raise ValueError("section exceeds image")
            self.sections.append((va, vs, raw_at, raw_size, flags))
        self.runtime = self.read_runtime()
        self.starts = [row[0] for row in self.runtime]
        self.exports, self.forwarder_count = self.read_exports()

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise ValueError("PE file span out of bounds")
        return self.data[offset:offset + size]

    def u32(self, offset):
        return struct.unpack("<I", self.read(offset, 4))[0]

    def rva_read(self, rva, size):
        if rva < 0 or size < 0 or rva + size > self.size_of_image:
            raise ValueError("RVA span out of image")
        if rva + size <= self.header_size:
            return self.read(rva, size)
        matches = []
        for va, vs, raw_at, raw_size, _flags in self.sections:
            offset = rva - va
            if 0 <= offset and offset + size <= raw_size:
                matches.append(raw_at + offset)
        if len(matches) != 1:
            raise ValueError("RVA missing, zero-fill-only or ambiguous")
        return self.read(matches[0], size)

    def executable(self, rva):
        return any(va <= rva < va + vs and flags & 0x20000000
                   for va, vs, _raw, _size, flags in self.sections)

    def directory(self, index):
        return self.directories[index] if index < len(self.directories) else (0, 0)

    def read_runtime(self):
        rva, size = self.directory(3)
        if not rva and not size:
            return []
        if not rva or not size or size % 12 or size // 12 > MAX_ENTRIES:
            raise ValueError("invalid x64 exception directory")
        rows = list(struct.iter_unpack("<III", self.rva_read(rva, size)))
        previous_end = 0
        for begin, end, unwind in rows:
            if begin < previous_end or not begin < end <= self.size_of_image or unwind >= self.size_of_image:
                raise ValueError("runtime function range invalid/overlapping")
            if not self.executable(begin) or not self.executable(end - 1):
                raise ValueError("runtime function outside executable section")
            previous_end = end
        return rows

    def string(self, rva):
        data = bytearray()
        for i in range(1024):
            byte = self.rva_read(rva + i, 1)
            if byte == b"\0":
                return data.decode("ascii", errors="strict")
            data.extend(byte)
        raise ValueError("export name exceeds bound")

    def read_exports(self):
        rva, size = self.directory(0)
        if not rva and not size:
            return {}, 0
        if not rva or size < 40:
            raise ValueError("invalid export directory")
        h = self.rva_read(rva, 40)
        functions, names, eat, name_ptrs, ordinals = struct.unpack_from("<IIIII", h, 20)
        if functions > MAX_ENTRIES or names > MAX_ENTRIES:
            raise ValueError("export table exceeds bound")
        addresses = struct.unpack("<" + "I" * functions, self.rva_read(eat, functions * 4)) if functions else ()
        pointers = struct.unpack("<" + "I" * names, self.rva_read(name_ptrs, names * 4)) if names else ()
        indexes = struct.unpack("<" + "H" * names, self.rva_read(ordinals, names * 2)) if names else ()
        result, forwarded = {}, 0
        for pointer, index in zip(pointers, indexes):
            if index >= functions:
                raise ValueError("export ordinal index out of address table")
            address = addresses[index]
            if rva <= address < rva + size:
                forwarded += 1
                continue  # forwarder RVA is a string, not code in this image.
            if not address or not self.executable(address):
                continue
            name = self.string(pointer)
            if name:
                result.setdefault(address, set()).add(name)
        return {address: sorted(names) for address, names in result.items()}, forwarded

    def label(self, rva):
        if not self.executable(rva):
            return {"status": "unknown-nonexecutable-rva", "exact_export_names": []}
        i = bisect.bisect_right(self.starts, rva) - 1
        if i < 0 or not self.runtime[i][0] <= rva < self.runtime[i][1]:
            return {"status": "unknown-no-runtime-function", "exact_export_names": []}
        begin, end, _ = self.runtime[i]
        names = self.exports.get(begin, [])
        return {"status": "exact-runtime-start-export" if names else "unknown-runtime-start-not-exported",
                "runtime_begin_rva": hex(begin), "runtime_end_rva": hex(end),
                "offset_in_runtime_function": rva - begin, "exact_export_names": names}


def verify_bytes(data, recorded_sha256, recorded_size):
    expected = str(recorded_sha256).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("missing/invalid recorded SHA256")
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ValueError("local file SHA256 differs from after-run evidence")
    pe = PE(data)
    if pe.size_of_image != number(recorded_size):
        raise ValueError("PE SizeOfImage differs from initial module inventory")
    return pe, actual


def read_local_recorded_file(path):
    # Do not interpret paths as URLs, UNC shares or device names.
    raw = str(path)
    drive, tail = ntpath.splitdrive(raw)
    if not re.fullmatch(r"[A-Za-z]:", drive) or not tail.startswith(("\\", "/")):
        raise ValueError("only recorded absolute local-drive PE paths accepted")
    if Path(raw).suffix.lower() not in (".dll", ".exe") or ":" in tail:
        raise ValueError("not an ordinary PE module path")
    if os.name != "nt":
        raise ValueError("recorded Windows module paths require local Windows filesystem")
    # Filesystem drive metadata only, never a process API. Reject mapped network drives.
    import ctypes
    get_drive_type = ctypes.WinDLL("kernel32", use_last_error=True).GetDriveTypeW
    get_drive_type.argtypes = [ctypes.c_wchar_p]
    get_drive_type.restype = ctypes.c_uint32
    if get_drive_type(drive + "\\") not in (3, 6):  # local fixed or RAM disk only
        raise ValueError("offline analysis refuses remote/nonlocal drives")
    p = Path(raw)
    # Reject reparse/symlink traversal rather than follow to an unrecorded network target.
    for part in [p, *p.parents]:
        st = part.lstat()
        if getattr(st, "st_file_attributes", 0) & 0x400:
            raise ValueError("reparse path refused for offline local-only analysis")
    if not 0 < p.stat().st_size <= MAX_FILE_BYTES:
        raise ValueError("module file exceeds bounded offline read")
    with p.open("rb") as file:
        data = file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("module file grew beyond read bound")
    return data


def summarize(initial_modules, module_backing_files_after_run, samples):
    """Pure evidence analysis except reads of exact recorded module paths."""
    modules = []
    verification = []
    parsers = {}
    for record in initial_modules:
        path = str(record["path"])
        base, size = number(record["base"]), number(record["size"])
        modules.append((base, base + size, path))
        result = {"path": path, "base": hex(base), "recorded_size_of_image": size}
        try:
            backing = module_backing_files_after_run.get(path)
            if not isinstance(backing, dict) or backing.get("error"):
                raise ValueError("missing or failed after-run backing-file hash")
            if not re.fullmatch(r"[0-9a-fA-F]{64}", str(backing.get("sha256", ""))):
                raise ValueError("missing/invalid recorded SHA256")
            pe, actual = verify_bytes(read_local_recorded_file(path), backing.get("sha256"), size)
            parsers[path] = pe
            result.update(status="verified-disk-sha-and-image-size", sha256=actual,
                runtime_functions=len(pe.runtime), named_code_export_addresses=len(pe.exports),
                forwarded_names_ignored=pe.forwarder_count)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, struct.error) as error:
            result.update(status="unverified", error=str(error))
        verification.append(result)
    groups = {}
    missing_ip = 0
    for s in samples:
        try:
            address = number(s["rip"])
        except (KeyError, ValueError, TypeError):
            missing_ip += 1
            continue
        mapping = s.get("module_mapping_qualified")
        containing = [(a, b, p) for a, b, p in modules if a <= address < b]
        result = {"address": hex(address), "module": None, "rva": None, "exact_export_names": []}
        if mapping is False:
            result["status"] = "unknown-mapping-invalidated"
        elif len(containing) != 1:
            result["status"] = "unknown-jit-unmapped-or-ambiguous"
        else:
            base, _, path = containing[0]
            rva = address - base
            result.update(module=path, rva=hex(rva))
            if path in parsers:
                result.update(parsers[path].label(rva))
            else:
                result["status"] = "unknown-unverified-file"
        result["mapping_evidence"] = "recorded-qualified" if mapping is True else "last-check-only-unknown-between-checks"
        if mapping is False:
            result["mapping_evidence"] = "invalidated"
        key = json.dumps(result, sort_keys=True)
        if key not in groups:
            groups[key] = {**result, "wall_snapshot_count": 0, "tids": set(), "first_sample_indices": []}
        group = groups[key]
        group["wall_snapshot_count"] += 1
        group["tids"].add(s.get("tid"))
        if len(group["first_sample_indices"]) < 8:
            group["first_sample_indices"].append(s.get("index"))
    rows = sorted(groups.values(), key=lambda row: (-row["wall_snapshot_count"], row["address"]))
    counts = Counter()
    for row in rows:
        row["tids"] = sorted(row["tids"], key=lambda tid: str(tid))
        counts[row["status"]] += row["wall_snapshot_count"]
    return {"schema": 1, "analysis": "offline-exact-export-at-runtime-function-start",
        "sample_count": len(samples), "missing_ip_samples": missing_ip,
        "status_counts": dict(counts), "module_verification": verification, "ip_groups": rows,
        "process_reads": False, "downloads": False, "pdb_used": False, "nearest_export_used": False,
        "performance_acceptance": False,
        "limits": ["Labels are conditional on recorded module mapping; a disk hash after the run is not proof of memory bytes at every sample.",
            "Only the runtime-function containing the exact RIP is used; its start must equal a named nonforwarded code export.",
            "Leaf/syscall stubs without .pdata remain unknown, even if close to an export.",
            "Export aliases are preserved together; a module or name is not a thread-role or CPU-cost attribution.",
            "Counts are wall-clock IP observations, not CPU percentages, wait durations or GPU evidence."]}


def self_test():
    """In-memory PE fixture: no file or process inspection."""
    data = bytearray(0xC00)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", data, 0x84, 0x8664, 2)
    struct.pack_into("<H", data, 0x94, 240)
    op = 0x98
    struct.pack_into("<H", data, op, 0x20B)
    struct.pack_into("<II", data, op + 56, 0x4000, 0x400)
    struct.pack_into("<I", data, op + 108, 16)
    struct.pack_into("<II", data, op + 112, 0x2000, 0x180)
    struct.pack_into("<II", data, op + 112 + 24, 0x2200, 36)
    for i, (name, va, raw, flags) in enumerate([(b".text", 0x1000, 0x400, 0x60000020),
                                               (b".rdata", 0x2000, 0x800, 0x40000040)]):
        sh = op + 240 + i * 40
        data[sh:sh + len(name)] = name
        struct.pack_into("<IIII", data, sh + 8, 0x400, va, 0x400, raw)
        struct.pack_into("<I", data, sh + 36, flags)
    # Three real ranges, only first and third have exact named exports.
    for i, row in enumerate([(0x1000, 0x1020, 0x2300), (0x1040, 0x1060, 0x2300), (0x1080, 0x10A0, 0x2300)]):
        struct.pack_into("<III", data, 0xA00 + i * 12, *row)
    struct.pack_into("<IIIII", data, 0x800 + 20, 4, 4, 0x2040, 0x2050, 0x2060)
    struct.pack_into("<IIII", data, 0x840, 0x1000, 0x1000, 0x1080, 0x2070)
    struct.pack_into("<IIII", data, 0x850, 0x20A0, 0x20B0, 0x20C0, 0x20D0)
    struct.pack_into("<HHHH", data, 0x860, 0, 1, 2, 3)
    for at, text in [(0x8A0, b"ExactOne\0"), (0x8B0, b"AliasOne\0"),
                     (0x8C0, b"ExactTwo\0"), (0x8D0, b"Forwarded\0"), (0x870, b"DLL.Real\0")]:
        data[at:at + len(text)] = text
    digest = hashlib.sha256(data).hexdigest()
    pe, _ = verify_bytes(bytes(data), digest, 0x4000)
    assert pe.label(0x1010)["exact_export_names"] == ["AliasOne", "ExactOne"]
    assert pe.label(0x1050)["status"] == "unknown-runtime-start-not-exported"
    assert pe.label(0x1020)["status"] == "unknown-no-runtime-function"
    assert pe.label(0x1080)["exact_export_names"] == ["ExactTwo"]
    assert pe.label(0x1100)["status"] == "unknown-no-runtime-function"
    assert pe.label(0x2000)["status"] == "unknown-nonexecutable-rva"
    assert pe.forwarder_count == 1
    rejected = 0
    for wrong_hash, wrong_size in [("0" * 64, 0x4000), (digest, 0x5000)]:
        try:
            verify_bytes(bytes(data), wrong_hash, wrong_size)
        except ValueError:
            rejected += 1
    assert rejected == 2
    return {"self_test": "passed", "checks": 9, "process_reads": False, "module_files_read": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observation", nargs="?", help="saved native-stack-observation.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
    elif args.observation:
        document = json.loads(Path(args.observation).read_text(encoding="utf-8-sig"))
        sampler = document["sampler"]
        result = summarize(sampler["initial_modules"], document["moduleBackingFilesAfterRun"], sampler["samples"])
    else:
        parser.error("Provide saved evidence or --self-test; no PID/attach input exists")
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()

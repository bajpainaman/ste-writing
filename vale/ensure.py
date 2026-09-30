#!/usr/bin/env python3
"""Find Vale or install a verified release in the current user's data directory."""

from __future__ import annotations

import hashlib
import io
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "3.23.0"
ASSETS = {
    ("Linux", "64-bit"): "cc35445a45186b8f0b01e11c01359694cf941e72cf6ab0fc44774f0e54c9d5fc",
    ("Linux", "arm64"): "45720aadcb01401ac394641287a2c74e094045a89a450f5edcf98c8969df0884",
    ("macOS", "64-bit"): "416fdd3ba32e32dc71c87b479cb86757bb6437bcebc7a3e4a095e863b7ce583d",
    ("macOS", "arm64"): "b913574b2c83b541d8bc2d8938e53a58a2fb06bab15135efcc755afb074f4430",
    ("Windows", "64-bit"): "ea9a8048498b869be8475a01488cd056f60b769f2d450311b9c24f07d11edd57",
    ("Windows", "arm64"): "e6e1dc8eacd288df66bea63358c934114ab08621c146a38777a655484eef14b6",
}


def managed_binary() -> Path:
    name = "vale.exe" if platform.system() == "Windows" else "vale"
    return Path.home() / ".local/share/ste-writing/bin" / name


def supported(executable: str | Path) -> bool:
    try:
        result = subprocess.run([str(executable), "--version"], capture_output=True, text=True, timeout=3)
        match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", result.stdout)
        return result.returncode == 0 and bool(match) and tuple(map(int, match.groups())) >= (3, 23, 0)
    except (OSError, subprocess.TimeoutExpired):
        return False


def resolve_vale() -> str | None:
    executable = shutil.which("vale")
    direct = Path("/snap/vale/current/bin/vale")
    if executable and Path(executable).parent == Path("/snap/bin") and direct.is_file():
        executable = str(direct)
    if executable and supported(executable):
        return executable
    managed = managed_binary()
    if managed.is_file() and supported(managed):
        return str(managed)
    return None


def ensure_vale() -> str:
    existing = resolve_vale()
    if existing:
        return existing
    system = {"Darwin": "macOS"}.get(platform.system(), platform.system())
    machine = platform.machine().lower()
    architecture = {"x86_64": "64-bit", "amd64": "64-bit", "aarch64": "arm64", "arm64": "arm64"}.get(machine)
    digest = ASSETS.get((system, architecture))
    if not digest:
        raise RuntimeError(f"Automatic Vale installation does not support {system}/{machine}.")
    extension = "zip" if system == "Windows" else "tar.gz"
    asset = f"vale_{VERSION}_{system}_{architecture}.{extension}"
    url = f"https://github.com/vale-cli/vale/releases/download/v{VERSION}/{asset}"
    request = urllib.request.Request(url, headers={"User-Agent": "ste-writing"})
    with urllib.request.urlopen(request, timeout=30) as response:
        archive = response.read(64 * 1024 * 1024 + 1)
    if len(archive) > 64 * 1024 * 1024 or hashlib.sha256(archive).hexdigest() != digest:
        raise RuntimeError("Vale archive failed SHA-256 verification.")
    target = managed_binary()
    if extension == "zip":
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = [name for name in bundle.namelist() if Path(name).name == target.name]
            if len(members) != 1:
                raise RuntimeError("Vale archive does not contain one executable.")
            binary = bundle.read(members[0])
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            members = [member for member in bundle.getmembers() if member.isfile() and Path(member.name).name == target.name]
            if len(members) != 1:
                raise RuntimeError("Vale archive does not contain one executable.")
            stream = bundle.extractfile(members[0])
            if stream is None:
                raise RuntimeError("Could not read the Vale executable.")
            binary = stream.read()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".vale-install-", dir=target.parent) as directory:
        temporary = Path(directory) / target.name
        temporary.write_bytes(binary)
        temporary.chmod(0o755)
        if not supported(temporary):
            raise RuntimeError("The downloaded Vale executable could not run.")
        os.replace(temporary, target)
    return str(target)


if __name__ == "__main__":
    print(ensure_vale())

"""Install a verified native Harper CLI without a system package manager."""

from __future__ import annotations

import hashlib
import io
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "2.11.0"
ASSETS = {
    ("Linux", "x86_64"): ("x86_64-unknown-linux-gnu", "1bfbe16927ef86b8ae09a964f83ea0662bca023f3ad32a5dc0dd141d5e684cd9"),
    ("Linux", "aarch64"): ("aarch64-unknown-linux-gnu", "e151dcfb03a7b9c6eb8e8f9d1c1bb16bbec19435553debb76ba0f022bf11d528"),
    ("Darwin", "x86_64"): ("x86_64-apple-darwin", "4e15c615f87b01f43030bedc1280dcffb43b32cbc1b10eda58c594112dede925"),
    ("Darwin", "aarch64"): ("aarch64-apple-darwin", "30856dc960f5ea5d2b6236e2208397d4444334e389358d51d7f9e04e57d00515"),
    ("Windows", "x86_64"): ("x86_64-pc-windows-msvc", "a32ad61f0ecef5272dab6e356d35e896da0b9c0274fc70ba62273083fde9a63c"),
}


def managed_binary() -> Path:
    name = "harper-cli.exe" if platform.system() == "Windows" else "harper-cli"
    return Path.home() / ".local/share/ste-writing/bin" / name


def supported(executable: str | Path) -> bool:
    # Some release builds report 0.1.0. Check the required interface instead.
    try:
        result = subprocess.run([str(executable), "lint", "--help"], capture_output=True, text=True, timeout=3)
        return result.returncode == 0 and all(s in result.stdout for s in ("--format", "json", "--dialect", "--ignore"))
    except (OSError, subprocess.TimeoutExpired):
        return False


def ensure_harper() -> str:
    managed = managed_binary()
    for executable in (str(managed) if managed.is_file() else None, shutil.which("harper-cli")):
        if executable and supported(executable):
            return executable
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)
    asset = ASSETS.get((platform.system(), machine))
    if not asset:
        raise RuntimeError(f"Automatic Harper installation does not support {platform.system()}/{machine}.")
    target_triple, digest = asset
    extension = "zip" if platform.system() == "Windows" else "tar.gz"
    url = f"https://github.com/Automattic/harper/releases/download/v{VERSION}/harper-cli-{target_triple}.{extension}"
    request = urllib.request.Request(url, headers={"User-Agent": "ste-writing"})
    with urllib.request.urlopen(request, timeout=30) as response:
        archive = response.read(64 * 1024 * 1024 + 1)
    if len(archive) > 64 * 1024 * 1024 or hashlib.sha256(archive).hexdigest() != digest:
        raise RuntimeError("Harper archive failed SHA-256 verification.")
    target = managed_binary()
    if extension == "zip":
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = [name for name in bundle.namelist() if Path(name).name == target.name]
            if len(members) != 1:
                raise RuntimeError("Harper archive does not contain one executable.")
            binary = bundle.read(members[0])
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            members = [m for m in bundle.getmembers() if m.isfile() and Path(m.name).name == target.name]
            if len(members) != 1:
                raise RuntimeError("Harper archive does not contain one executable.")
            stream = bundle.extractfile(members[0])
            if stream is None:
                raise RuntimeError("Could not read the Harper executable.")
            binary = stream.read()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".harper-install-", dir=target.parent) as directory:
        temporary = Path(directory) / target.name
        temporary.write_bytes(binary)
        temporary.chmod(0o755)
        if not supported(temporary):
            raise RuntimeError("The downloaded Harper executable could not run.")
        os.replace(temporary, target)
    return str(target)


if __name__ == "__main__":
    print(ensure_harper())

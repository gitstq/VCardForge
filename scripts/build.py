#!/usr/bin/env python3
"""一键打包脚本：生成 zipapp 单文件命令行工具 + 源码包 + SHA256 校验和。

用法::

    python3 scripts/build.py

产物（输出到 dist/）::

    vcardforge-<版本>.pyz        # 零安装单文件 CLI，任何装有 Python 的平台直接运行
    vcardforge-<版本>-src.zip    # 完整源码包
    SHA256SUMS.txt               # 全部产物校验和
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vcardforge  # noqa: E402

VERSION = vcardforge.__version__
DIST = os.path.join(ROOT, "dist")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_zipapp() -> str:
    """用标准库 zipapp 打包单文件 CLI。"""
    pyz = os.path.join(DIST, f"vcardforge-{VERSION}.pyz")
    tmp = tempfile.mkdtemp()
    try:
        # 只拷贝包本体，避免把 dist/ 自身打进去造成递归
        pkg_src = os.path.join(ROOT, "vcardforge")
        pkg_dst = os.path.join(tmp, "vcardforge")
        shutil.copytree(pkg_src, pkg_dst, ignore=shutil.ignore_patterns("__pycache__"))
        zipapp_args = [sys.executable, "-m", "zipapp", "-o", pyz, "-m", "vcardforge.cli:main", "-p", "/usr/bin/env python3", tmp]
        subprocess.run(zipapp_args, check=True, capture_output=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    os.chmod(pyz, 0o755)
    return pyz


def build_src_zip() -> str:
    src_zip = os.path.join(DIST, f"vcardforge-{VERSION}-src.zip")
    with zipfile.ZipFile(src_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "dist", "__pycache__", ".venv", "venv")]
            for name in files:
                if name == "SHA256SUMS.txt":
                    continue
                full = os.path.join(base, name)
                rel = os.path.relpath(full, os.path.dirname(ROOT))
                zf.write(full, os.path.join("VCardForge", rel))
    return src_zip


def main() -> int:
    os.makedirs(DIST, exist_ok=True)
    artifacts = [build_zipapp(), build_src_zip()]

    lines = []
    for path in artifacts:
        digest = sha256(path)
        lines.append(f"{digest}  {os.path.basename(path)}")
        print(f"[OK] {os.path.basename(path)}  sha256={digest[:16]}...")
    sums = os.path.join(DIST, "SHA256SUMS.txt")
    with open(sums, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"[OK] SHA256SUMS.txt")
    print(f"全部产物位于: {DIST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

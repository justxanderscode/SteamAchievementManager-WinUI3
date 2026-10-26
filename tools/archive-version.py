# -*- coding: utf-8 -*-
"""Builds a release of the Steam Achievement Manager (WinUI 3) and keeps it in the version archive.

    python tools/archive-version.py <version> "short description"

Creates:

    releases/<version>/   to use: SteamAchievementManager-<version>-win-x64.zip (self-contained, start SAM.exe)
    versions/<version>/   for reference: complete source (src/), built program (bin/), VERSION.md

Layout of the program folder in the ZIP:

    SteamAchievementManager/
      SAM.exe             small launcher (SAM.Launcher, .NET Framework 4.8), starts app/SAM.exe
      README.md, LICENSE.txt
      app/                the actual program with its runtime and WinUI's language folders

A version that has already been archived is never overwritten.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"bin", "obj", "versions", "releases", "publish", ".vs", ".git"}
PROJECT = os.path.join(ROOT, "SAM.App", "SAM.App.csproj")
LAUNCHER = os.path.join(ROOT, "SAM.Launcher", "SAM.Launcher.csproj")


def copy_tree(src, dst):
    files = 0
    for root, dirs, names in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel = os.path.relpath(root, src)
        target = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target, exist_ok=True)
        for name in names:
            shutil.copy2(os.path.join(root, name), os.path.join(target, name))
            files += 1
    return files


def project_version(path):
    text = io.open(path, encoding="utf-8-sig").read()
    m = re.search(r"<Version>([^<]+)</Version>", text)
    return m.group(1) if m else None


def main():
    args = sys.argv[1:]
    if len(args) < 1:
        print(__doc__)
        return 2

    version = args[0]
    note = args[1] if len(args) > 1 else ""
    release = os.path.join(ROOT, "releases", version)
    archive = os.path.join(ROOT, "versions", version)

    for existing in (release, archive):
        if os.path.exists(existing):
            print("Version %s already exists: %s" % (version, existing))
            return 1

    for csproj in (PROJECT, os.path.join(ROOT, "SAM.API", "SAM.API.csproj"), LAUNCHER):
        current = project_version(csproj)
        if current != version:
            print("Aborted: %s is at version %s, but %s is to be archived" % (os.path.basename(csproj), current, version))
            return 1

    # ---------------------------------------------------------------- Build the program
    # The program goes to app/ (WinUI only finds its language folders right next to Microsoft.UI.Xaml.dll);
    # the program folder itself only holds the launcher.
    # No debug symbols and a PathMap, so that no local paths (PDB path, source files) end up in SAM.exe/SAM.dll.
    clean = ["-p:DebugType=none", "-p:DebugSymbols=false", "-p:Deterministic=true", "-p:IncludeSourceRevisionInInformationalVersion=false", "-p:PathMap=" + ROOT + os.sep + "=/_/"]
    staging = tempfile.mkdtemp(prefix="sam-publish-")
    publish = os.path.join(staging, "SteamAchievementManager")
    app = os.path.join(publish, "app")
    launcher = os.path.join(staging, "launcher")
    result = subprocess.run(["dotnet", "publish", PROJECT, "-c", "Release", "-r", "win-x64", "-p:Platform=x64",
                             "-o", app, "-nologo", "-v", "q"] + clean)
    if result.returncode == 0:
        result = subprocess.run(["dotnet", "build", LAUNCHER, "-c", "Release", "-o", launcher, "-nologo", "-v", "q"] + clean)
    if result.returncode != 0 or not os.path.exists(os.path.join(app, "SAM.exe"))             or not os.path.exists(os.path.join(launcher, "SAM.exe")):
        shutil.rmtree(staging, ignore_errors=True)
        print("Build failed - nothing archived.")
        return 1

    shutil.copy2(os.path.join(launcher, "SAM.exe"), os.path.join(publish, "SAM.exe"))
    shutil.rmtree(launcher, ignore_errors=True)
    for name in ("README.md", "LICENSE.txt"):
        shutil.copy2(os.path.join(ROOT, name), os.path.join(publish, name))

    zip_name = "SteamAchievementManager-%s-win-x64" % version
    os.makedirs(release)
    shutil.make_archive(os.path.join(release, zip_name), "zip", staging, "SteamAchievementManager")
    shutil.rmtree(staging, ignore_errors=True)

    readme = [
        "# Steam Achievement Manager (WinUI 3) %s" % version,
        "",
        "| File | Purpose |",
        "|---|---|",
        "| `%s.zip` | Self-contained program – extract it and start `SAM.exe` (Windows 10 2004+ / 11, x64; Steam must be running) |" % zip_name,
        "",
        "The extracted folder contains only `SAM.exe` (launcher), `README.md`, `LICENSE.txt` and the `app` folder with the",
        "actual program. Always copy the complete folder.",
        "",
        "Source code and documentation of this version: `../../versions/%s/`." % version,
        "",
    ]
    io.open(os.path.join(release, "README.md"), "w", encoding="utf-8", newline="\n").write("\n".join(readme))

    # ---------------------------------------------------------------- Archive
    os.makedirs(archive)
    files = copy_tree(ROOT, os.path.join(archive, "src"))
    shutil.copytree(release, os.path.join(archive, "bin"), ignore=shutil.ignore_patterns("README.md"))

    info = ["# Steam Achievement Manager (WinUI 3) %s" % version, "", "Archived on %s." % date.today().isoformat(), ""]
    if note:
        info += ["**What this version brings:** " + note, ""]
    info += [
        "| | |",
        "|---|---|",
        "| Source | `src/` – without `bin`/`obj` |",
        "| Files | %d |" % files,
        "| Built | `bin/%s.zip` |" % zip_name,
        "| To use | `../../releases/%s/` |" % version,
        "",
        "This folder is not changed any more. Work continues in the project folder itself.",
        "",
    ]
    io.open(os.path.join(archive, "VERSION.md"), "w", encoding="utf-8", newline="\n").write("\n".join(info))

    size = os.path.getsize(os.path.join(release, zip_name + ".zip")) / 1024 / 1024
    print("release : %s  (%s.zip, %.1f MB)" % (release, zip_name, size))
    print("archive : %s  (%d files in the source)" % (archive, files))
    return 0


if __name__ == "__main__":
    sys.exit(main())

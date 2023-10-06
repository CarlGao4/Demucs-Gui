# Demucs-GUI
# Copyright (C) 2022-2023  Carl Gao, Jize Guo, Rosario S.E.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import __main__
import json
import logging
import os
import pathlib
import sys
import traceback


homeDir = pathlib.Path(__main__.__file__).resolve().parent
debug = False

if not (homeDir.parent / ".git").exists():
    os.chdir(homeDir)

if sys.platform == "win32" and not debug and not sys.executable.endswith("python.exe"):
    import ctypes
    ctypes.windll.kernel32.FreeConsole()

save_loc_syntax = """You can use variables to rename your output file.
Variables "{track}", "{trackext}", "{stem}", "{ext}", "{model}" will be replaced with track name without extension, \
track extension, stem name, default output file extension and model name.

For example, when saving stem "vocals" of "audio.mp3" using model htdemucs, with output format flac, the default \
location "separated/{model}/{track}/{stem}.{ext}" would be "separated/htdemucs/audio/vocals.flac", with the folder \
"separated" created under the same folder of the original audio file.

Please remember that absolute path must start from the root dir (like "C:\\xxx" on Windows or "/xxx" on macOS and \
Linux) in case something unexpected would happen."""


def HSize(size):
    s = size
    t = 0
    u = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    while s >= 1024:
        s /= 1024
        t += 1
        if t >= 6:
            break
    return str(round(s, 3)) + u[t]


def InitializeFolder():
    global logfile, pretrained, settingsFile, settings
    if sys.platform == "win32":
        logfile = pathlib.Path(os.environ["APPDATA"])
    elif sys.platform == "darwin" or sys.platform == "linux":
        logfile = pathlib.Path.home() / ".config"
    else:
        logfile = homeDir
    logfile = logfile / "demucs-gui"
    logfile.mkdir(parents=True, exist_ok=True)
    pretrained = logfile / "pretrained"
    pretrained.mkdir(parents=True, exist_ok=True)
    settingsFile = logfile / "settings.json"
    logfile = logfile / "log"
    logfile.mkdir(parents=True, exist_ok=True)
    if settingsFile.exists():
        try:
            with open(str(settingsFile), mode="rt", encoding="utf8") as f:
                settings = json.loads(f.read())
            if type(settings) != dict:
                raise TypeError
        except:
            settings = {}
    else:
        settings = {}


def SetSetting(attr, value):
    global settings, settingsFile
    logging.debug('(%s) Set setting "%s" to %s' % (traceback.extract_stack()[-2].name, attr, str(value)))
    settings[attr] = value
    with open(str(settingsFile), mode="wt", encoding="utf8") as f:
        f.write(json.dumps(settings, separators=(",", ":")))


def GetSetting(attr, default=None, autoset=True):
    global settings
    if attr in settings:
        return settings[attr]
    else:
        if autoset:
            SetSetting(attr, default)
        return default


class FileStatus:
    Queued = 0
    Paused = 1
    Reading = 2
    Separating = 3
    Writing = 4
    Finished = 5
    Failed = 6
    Cancelled = 7

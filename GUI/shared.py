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
import functools
import json
import logging
import lzma
import ordered_set
import os
import pathlib
import pickle
import subprocess
import sys
import threading
import traceback
import urllib.request


homeDir = pathlib.Path(__main__.__file__).resolve().parent
debug = True
use_PyQt6 = False  # set to True to use PyQt6 instead of PySide6

if sys.platform == "win32" and not debug and not sys.executable.endswith("python.exe"):
    import ctypes

    ctypes.windll.kernel32.FreeConsole()

if not (homeDir.parent / ".git").exists():
    os.chdir(homeDir)

save_loc_syntax = """You can use variables to rename your output file.
Variables "{track}", "{trackext}", "{stem}", "{ext}", "{model}" will be replaced with track name without extension, \
track extension, stem name, default output file extension and model name.

For example, when saving stem "vocals" of "audio.mp3" using model htdemucs, with output format flac, the default \
location "separated/{model}/{track}/{stem}.{ext}" would be "separated/htdemucs/audio/vocals.flac", with the folder \
"separated" created under the same folder of the original audio file.

Please remember that absolute path must start from the root dir (like "C:\\xxx" on Windows or "/xxx" on macOS and \
Linux) in case something unexpected would happen."""

update_url = "https://api.github.com/repos/CarlGao4/Demucs-GUI/releases/latest"

settingsLock = threading.Lock()
historyLock = threading.Lock()


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
    global logfile, pretrained, settingsFile, historyFile, configPath, settings, history
    if sys.platform == "win32":
        configPath = pathlib.Path(os.environ["APPDATA"])
    elif sys.platform == "darwin" or sys.platform == "linux":
        configPath = pathlib.Path.home() / ".config"
    else:
        configPath = homeDir
    configPath = configPath / "demucs-gui"
    configPath.mkdir(parents=True, exist_ok=True)
    pretrained = configPath / "pretrained"
    pretrained.mkdir(parents=True, exist_ok=True)
    settingsFile = configPath / "settings.json"
    historyFile = configPath / "history.db"
    logfile = configPath / "log"
    logfile.mkdir(parents=True, exist_ok=True)
    if settingsFile.exists():
        try:
            with open(str(settingsFile), mode="rt", encoding="utf8") as f:
                settings_data = f.read()
                settings = json.loads(settings_data)
            if type(settings) != dict:
                raise TypeError
        except:
            print("Settings file is corrupted, reset to default", file=sys.stderr)
            print("Error message:\n%s" % traceback.format_exc(), file=sys.stderr)
            print("Settings file content:\n%s" % settings_data, file=sys.stderr)
            settings = {}
    else:
        settings = {}
    if historyFile.exists():
        try:
            with open(str(historyFile), mode="rb") as f:
                history = pickle.loads(lzma.decompress(f.read()))
            if type(history) != dict:
                raise TypeError
        except:
            print("History file is corrupted, reset to default", file=sys.stderr)
            print("Error message:\n%s" % traceback.format_exc(), file=sys.stderr)
            history = {}
    else:
        history = {}


def SetSetting(attr, value):
    global settings, settingsFile, settingsLock
    with settingsLock:
        logging.debug('(%s) Set setting "%s" to %s' % (traceback.extract_stack()[-2].name, attr, str(value)))
        if attr in settings and settings[attr] == value:
            logging.debug("Setting not changed, ignored")
            return
        settings[attr] = value
        try:
            with open(str(settingsFile), mode="wt", encoding="utf8") as f:
                f.write(json.dumps(settings, separators=(",", ":")))
        except:
            logging.warning("Failed to save settings:\n%s" % traceback.format_exc())


def GetSetting(attr, default=None, autoset=True):
    global settings
    if attr in settings:
        return settings[attr]
    else:
        if autoset:
            SetSetting(attr, default)
        return default


def _SaveHistory():
    global history, historyFile, historyLock
    with historyLock:
        try:
            with open(str(historyFile), mode="wb") as f:
                f.write(lzma.compress(pickle.dumps(history), preset=7))
        except:
            logging.warning("Failed to save history:\n%s" % traceback.format_exc())


def SetHistory(attr, value):
    global history, historyFile, historyLock
    with historyLock:
        logging.debug('(%s) Set history "%s" to %s' % (traceback.extract_stack()[-2].name, attr, str(value)))
        if attr in history and history[attr] == value:
            logging.debug("History not changed, ignored")
            return
        history[attr] = value
    _SaveHistory()


def GetHistory(attr, default=None, autoset=True, use_ordered_set=False):
    global history
    if attr in history:
        if (not use_ordered_set) or type(history[attr]) == ordered_set.OrderedSet:
            return history[attr]
        return ordered_set.OrderedSet([history[attr]])
    else:
        if autoset and not use_ordered_set:
            SetHistory(attr, default)
            return default
        else:
            SetHistory(attr, ordered_set.OrderedSet([default]))
            return history[attr]


def AddHistory(attr, value):
    old_value = GetHistory(attr, ordered_set.OrderedSet(), False)
    if type(old_value) != ordered_set.OrderedSet:
        old_value = ordered_set.OrderedSet([old_value])
    SetHistory(attr, ordered_set.OrderedSet([value]) | old_value)


def ResetHistory(attr=None):
    global history, historyFile, historyLock
    if attr is None:
        with historyLock:
            history = {}
        _SaveHistory()
    else:
        if attr in history:
            with historyLock:
                history.pop(attr)
            _SaveHistory()


class FileStatus:
    Queued = 0
    Paused = 1
    Reading = 2
    Separating = 3
    Writing = 4
    Finished = 5
    Failed = 6
    Cancelled = 7


def Popen(*args, **kwargs):
    """A wrapper of `subprocess.Popen` to hide console window on Windows and redirect stdout and stderr to PIPE"""
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    # stdin, stdout and stderr are always redirected or creating process will fail on Windows without console
    kwargs["stdout"] = subprocess.PIPE
    kwargs["stderr"] = subprocess.PIPE
    kwargs["stdin"] = subprocess.PIPE
    return subprocess.Popen(*args, **kwargs)


def thread_wrapper(*args_thread, **kw_thread):
    if "target" in kw_thread:
        kw_thread.pop("target")
    if "args" in kw_thread:
        kw_thread.pop("args")
    if "kwargs" in kw_thread:
        kw_thread.pop("kwargs")

    def thread_func_wrapper(func):
        if not hasattr(thread_wrapper, "index"):
            thread_wrapper.index = 0

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            thread_wrapper.index += 1

            def run_and_log(idx=thread_wrapper.index):
                logging.info(
                    "[%d] Thread %s (%s) starts" % (idx, func.__name__, pathlib.Path(func.__code__.co_filename).name)
                )
                try:
                    func(*args, **kwargs)
                finally:
                    logging.info(
                        "[%d] Thread %s (%s) ends" % (idx, func.__name__, pathlib.Path(func.__code__.co_filename).name)
                    )

            t = threading.Thread(target=run_and_log, *args_thread, **kw_thread)
            t.start()
            return t

        return wrapper

    return thread_func_wrapper


@thread_wrapper(daemon=True)
def checkUpdate(callback):
    try:
        logging.info("Checking for updates...")
        with urllib.request.urlopen(update_url) as f:
            data = json.loads(f.read())
        logging.info("Latest version: %s" % data["tag_name"])
        callback(data["tag_name"])
    except:
        logging.warning("Failed to check for updates:\n%s" % traceback.format_exc())
        callback(None)

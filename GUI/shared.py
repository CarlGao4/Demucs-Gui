# Demucs-GUI
# Copyright (C) 2022-2025  Demucs-GUI developers
# See https://github.com/CarlGao4/Demucs-Gui for more information

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

import certifi
import os

# Use certifi to get CA certificates
os.environ["SSL_CERT_FILE"] = certifi.where()

import __main__
import functools
import json
import logging
import lzma
import ordered_set
import packaging.version
import pathlib
import pickle
import re
import shlex
import subprocess
import sys
import threading
import traceback
import urllib.parse
import urllib.request


homeDir = pathlib.Path(__main__.__file__).resolve().parent
debug = False  # Do not write log file, output to console instead if True
use_PyQt6 = False  # set to True to use PyQt6 instead of PySide6

if not (homeDir.parent / ".git").exists():
    os.chdir(homeDir)  # Change working directory to homeDir if not running from source
else:
    debug = True  # Disable log file if running from source

if os.environ.get("DGUI_DEBUG", "0") not in {"0", "no", "false"}:
    debug = True

if sys.platform == "win32" and not debug and not sys.executable.endswith("python.exe"):
    import ctypes

    ctypes.windll.kernel32.FreeConsole()

save_loc_syntax = """\
You can use variables to rename your output file. Available variables are:
- {track}: track name without extension
- {trackext}: track name with extension
- {stem}: stem name
- {ext}: default output file extension
- {model}: model name
- {host}: URL host name. If input is local file, it will be "localfile"
- {0}, {1}, ...: input file name and its parent folder names, 0 for file name, 1 for parent folder name, and so on. \
You can use up to 15. If the number is greater than the actual number of parent folders, it will be empty.
- {TAG}: audio tag. TAG is the tag name. Available tags are listed below. If the audio file does not have the \
corresponding tag, it will be empty. If you know the audio file has an extra tag, you can also use it, though it \
might not be listed here. If the audio file does not contain the extra tag, save process will fail. If a tag name is \
used as a variable, an underscore "_" will be automatically added to the end of the tag name to avoid conflict.
    Available example tags: title, artist, album, date, track_, genre, comment, composer, performer, album_artist, \
disc, publisher, language, lyricist, conductor, arranger, engineer, producer, mixer, grouping

For example, when saving stem "vocals" of "audio.mp3" using model htdemucs, with output format flac, the default \
location "separated/{model}/{track}/{stem}.{ext}" would be "separated/htdemucs/audio/vocals.flac", with the folder \
"separated" created under the same folder of the original audio file.

Please remember that absolute path must start from the root dir (like "C:\\xxx" on Windows or "/xxx" on macOS and \
Linux) in case something unexpected would happen."""

command_syntax = """\
You can use FFmpeg to encode output audio files instead of the internal libsndfile.

The separated audio data will be piped to FFmpeg's stdin and the output file will be created by FFmpeg. FFmpeg stdout \
will be ignored and stderr will be logged to the log file.
Data passed to FFmpeg is in wav format, encoded with float32 sample format. So if you want to change the format, \
please manually add "-sample_fmt" option to the command. e.g. "-sample_fmt s16" for 16-bit signed integer.

There are also some variables you can use in the command. Your command will be splitted to argument list by \
shlex.split (Unix-like shell syntax), then the variables will be replaced with the corresponding values. \
Available variables:
- {input}: input file name without extension
- {inputext}: input file extension
- {inputpath}: input file path (without file name)
- {output}: output file full path
- {TAG}: audio tag. TAG is the tag name. Available tags are listed below. If the audio file does not have the \
corresponding tag, it will be empty. If you know the audio file has an extra tag, you can also use it, though it \
might not be listed here. If the audio file does not contain the extra tag, save process will fail. If a tag name is \
used as a variable, an underscore "_" will be automatically added to the end of the tag name to avoid conflict.
    Available example tags: title, artist, album, date, track, genre, comment, composer, performer, album_artist, \
disc, publisher, language, lyricist, conductor, arranger, engineer, producer, mixer, grouping
Variables about input file above will also be replaced in file extension."""

update_url = "https://api.github.com/repos/CarlGao4/Demucs-GUI/releases"

settingsLock = threading.Lock()
historyLock = threading.Lock()

urlreg_str = (
    r"^(?P<scheme>[a-zA-Z]+)://"
    r"(?P<authority>(?P<host>[^:/?#&=\[\]\(\)\{\}]+|\[[0-9a-fA-F:.]+\])"
    r"(?::(?P<port>\d+))?)"
    r"(?P<path>(?:/(?P<name>[^?#/]+)|/)*)"
    r"(?:\?(?P<query>[^#]*))?"
    r"(?:#(?P<anchor>.*))?$"
)
urlreg = re.compile(urlreg_str)


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") and sys.platform == "win32":
    # Popen should be wrapped to avoid WinError 50
    subprocess._Popen = subprocess.Popen

    class wrapped_Popen(subprocess._Popen):
        def __init__(self, *args, **kwargs):
            if "stdout" in kwargs and kwargs["stdout"] is not None:
                if "stderr" not in kwargs or kwargs["stderr"] is None:
                    kwargs["stderr"] = subprocess.PIPE
                if "stdin" not in kwargs or kwargs["stdin"] is None:
                    kwargs["stdin"] = subprocess.PIPE
            if "stderr" in kwargs and kwargs["stderr"] is not None:
                if "stdout" not in kwargs or kwargs["stdout"] is None:
                    kwargs["stdout"] = subprocess.PIPE
                if "stdin" not in kwargs or kwargs["stdin"] is None:
                    kwargs["stdin"] = subprocess.PIPE
            if "stdin" in kwargs and kwargs["stdin"] is not None:
                if "stdout" not in kwargs or kwargs["stdout"] is None:
                    kwargs["stdout"] = subprocess.PIPE
                if "stderr" not in kwargs or kwargs["stderr"] is None:
                    kwargs["stderr"] = subprocess.PIPE
            super().__init__(*args, **kwargs)

    subprocess.Popen = wrapped_Popen


def HSize(size):
    s = size
    t = 0
    u = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    while s >= 1024:
        s /= 1024
        t += 1
        if t >= 6:
            break
    return ("%.3f" % s).rstrip("0").rstrip(".") + u[t]


def is_sublist(a, b):
    if not isinstance(a, list):
        a = list(a)
    if not isinstance(b, list):
        b = list(b)
    if not a:
        return True
    if not b:
        return False
    if a[0] == b[0]:
        return is_sublist(a[1:], b[1:])
    return is_sublist(a, b[1:])


def try_parse_cmd(cmd):
    try:
        return shlex.split(cmd)
    except Exception:
        return []


def InitializeFolder():
    global logfile, pretrained, settingsFile, historyFile, configPath, settings, history, model_cache
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
            if type(settings) is not dict:
                raise TypeError
        except Exception:
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
            if type(history) is not dict:
                raise TypeError
        except Exception:
            print("History file is corrupted, reset to default", file=sys.stderr)
            print("Error message:\n%s" % traceback.format_exc(), file=sys.stderr)
            history = {}
    else:
        history = {}

    model_cache = pathlib.Path(GetSetting("model_cache", str(pretrained)))
    (model_cache / "checkpoints").mkdir(parents=True, exist_ok=True)


def SetSetting(attr, value):
    global settings, settingsFile, settingsLock
    with settingsLock:
        func_name = traceback.extract_stack()
        if func_name[-2].name == "GetSetting":
            func_name = func_name[-3].name
        else:
            func_name = func_name[-2].name
        if value is None:
            logging.debug('(%s) Remove setting "%s"' % (func_name, attr))
            del settings[attr]
        else:
            logging.debug('(%s) Set setting "%s" to %s' % (func_name, attr, str(value)))
            if attr in settings and settings[attr] == value:
                logging.debug("Setting not changed, ignored")
                return
            settings[attr] = value
        try:
            settings_write_data = json.dumps(settings, separators=(",", ":"))
            with open(str(settingsFile), mode="wt", encoding="utf8") as f:
                f.write(settings_write_data)
        except Exception:
            logging.warning("Failed to save settings:\n%s" % traceback.format_exc())


def GetSetting(attr, default=None, autoset=True):
    global settings
    if attr in settings:
        return settings[attr]
    else:
        if autoset:
            SetSetting(attr, default)
        return default


def _get_from_dict(dataDict, mapList):
    for key in mapList:
        if key in dataDict:
            dataDict = dataDict[key]
        else:
            return None
    return dataDict


def _set_to_dict(dataDict, mapList, value):
    if value is None:
        for i in reversed(range(len(mapList))):
            key = mapList[i]
            parent = _get_from_dict(dataDict, mapList[:i])
            if parent and key in parent:
                del parent[key]
                if not parent:
                    continue
            break
    else:
        for key in mapList[:-1]:
            if key not in dataDict:
                dataDict[key] = {}
            dataDict = dataDict[key]
        dataDict[mapList[-1]] = value


def _SaveHistory():
    global history, historyFile, historyLock
    with historyLock:
        try:
            history_write_data = lzma.compress(pickle.dumps(history), preset=7)
            with open(str(historyFile), mode="wb") as f:
                f.write(history_write_data)
        except Exception:
            logging.warning("Failed to save history:\n%s" % traceback.format_exc())


def SetHistory(*attr, value):
    global history, historyFile, historyLock
    with historyLock:
        func_name = traceback.extract_stack()
        if func_name[-2].name in ["GetHistory", "AddHistory", "ResetHistory"]:
            func_name = func_name[-3].name
        else:
            func_name = func_name[-2].name
        logging.debug("(%s) Set history %s to %s" % (func_name, attr, str(value)))
        if _get_from_dict(history, attr) == value:
            logging.debug("History not changed, ignored")
            return
        _set_to_dict(history, attr, value)
    _SaveHistory()


def GetHistory(*attr, default=None, autoset=True, use_ordered_set=False):
    global history
    if _get_from_dict(history, attr) is not None:
        if (not use_ordered_set) or type(_get_from_dict(history, attr)) is ordered_set.OrderedSet:
            return _get_from_dict(history, attr)
        return ordered_set.OrderedSet([_get_from_dict(history, attr)])
    elif autoset:
        if not use_ordered_set:
            SetHistory(*attr, value=default)
            return default
        else:
            SetHistory(*attr, value=ordered_set.OrderedSet([default]))
            return _get_from_dict(history, attr)
    return default


def AddHistory(*attr, value):
    old_value = GetHistory(*attr, default=ordered_set.OrderedSet(), autoset=False)
    if type(old_value) is not ordered_set.OrderedSet:
        old_value = ordered_set.OrderedSet([old_value])
    if value in old_value:  # Move to front
        old_value.remove(value)
    SetHistory(*attr, value=ordered_set.OrderedSet([value]) | old_value)


def ResetHistory(*attr):
    global history, historyFile, historyLock
    if not attr:
        logging.info("Resetting history")
        with historyLock:
            history = {}
        _SaveHistory()
    else:
        logging.info("Resetting history %s" % str(attr))
        with historyLock:
            _set_to_dict(history, attr, None)
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
    Skipped = 8


def get_unique_filename(filepath: pathlib.Path) -> pathlib.Path:
    """Generate a unique filename by appending a number to the stem if it already exists."""
    if not filepath.exists():
        return filepath

    stem = filepath.stem
    suffix = filepath.suffix
    counter = 2

    if m := re.search(r" *\((\d+)\)$", stem):
        # If the stem ends with a number in parentheses, start from that number + 1
        counter = int(m.group(1)) + 1
        stem = stem[: -len(m.group(0))]

    while filepath.exists():
        filepath = filepath.with_stem(f"{stem} ({counter})").with_suffix(suffix)
        counter += 1

    return filepath


def re_sub_remove_file(m: re.Match):
    """Remove the file part in the URL, re callback function"""
    ret = m["scheme"] + "://" + m["authority"]
    if m["port"]:
        ret += ":" + m["port"]
    if m["path"]:
        if m["name"]:
            ret += m["path"][: -len(m["name"])]
        else:
            ret += m["path"]
    if m["query"]:
        ret += "?" + m["query"]
    if m["anchor"]:
        ret += "#" + m["anchor"]
    return ret


class URL_with_filename(object):
    def __new__(cls, url, protocols=["http", "https"], **kwargs):
        # Verify URL
        if (not (m := urlreg.match(url))) or m.group("scheme") not in protocols:
            return None
        return object.__new__(cls)

    def __init__(self, url, name=None, **kwargs):
        self._url = url
        self._m = urlreg.match(url)
        self._protocols = kwargs.get("protocols", ["http", "https"])
        if name is not None:
            self._name = name
            self._hasname = True

    def __repr__(self):
        return "URL_with_filename(%r)" % self._url

    def __str__(self):
        return self._url

    def __getitem__(self, key):
        return self._m[key]

    def __eq__(self, other):
        if isinstance(other, URL_with_filename):
            return self._url == other._url
        return False

    @property
    def name(self):
        if hasattr(self, "_hasname"):
            return self._name
        m = urlreg.match(self._url)
        url_name = urllib.parse.unquote_plus(m["name"])
        if m["scheme"].lower() in {"http", "https", "ftp"}:
            try:
                logging.info("Getting file name from URL: %s" % self)
                req = urllib.request.Request(self, method="GET")
                u = urllib.request.urlopen(req)
                u.close()
                self._name = u.headers.get_filename()
                if self._name:
                    logging.info("Found file name in header: %s" % self._name)
                    self._hasname = True
                    return self._name
                logging.info("No file name in header, trying to get from URL")
            except Exception:
                logging.error("Failed to get file name from header:\n%s" % traceback.format_exc())
        if url_name:
            self._name = url_name
            self._hasname = True
            logging.info("Found file name in URL: %s" % self._name)
            return self._name
        logging.error("Failed to find file name in URL")
        self._name = None
        self._hasname = False
        return None

    @property
    def stem(self):
        if self.name:
            return pathlib.Path(self.name).stem
        return ""

    @property
    def suffix(self):
        if self.name:
            return pathlib.Path(self.name).suffix
        return ""

    @property
    def suffixes(self):
        if self.name:
            return pathlib.Path(self.name).suffixes
        return []

    @property
    def parent(self):
        removed = re.sub(urlreg, re_sub_remove_file, self._url)
        return URL_with_filename(removed, name=re.match(urlreg, removed)["name"], protocols=self._protocols)

    @property
    def url(self):
        return self._url

    @property
    def protocols(self):
        return self._protocols


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
            stack = "".join(traceback.format_list(traceback.extract_stack()[:-1]))

            def run_and_log(idx=thread_wrapper.index):
                logging.info(
                    "[%d] Thread %s (%s) starts" % (idx, func.__name__, pathlib.Path(func.__code__.co_filename).name)
                )
                try:
                    func(*args, **kwargs)
                except Exception:
                    logging.error(
                        "[%d] Thread %s (%s) failed:\n%s%s"
                        % (
                            idx,
                            func.__name__,
                            pathlib.Path(func.__code__.co_filename).name,
                            stack,
                            traceback.format_exc(),
                        )
                    )
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
            data = json.loads(f.read())[:3]  # Get the latest 3 releases so we can also check for pre-releases
        data = sorted(data, key=lambda x: packaging.version.parse(x["tag_name"]), reverse=True)
        logging.info("Latest version: %s" % data[0]["tag_name"])
        m = re.search(r"<!--\s*\[inapp-info\](.*)\s*-->", data[0]["body"], re.DOTALL)
        description = ""
        if m:
            description = m[1].strip()
        callback(data[0]["tag_name"], description)
    except Exception:
        logging.warning("Failed to check for updates:\n%s" % traceback.format_exc())
        callback(None)

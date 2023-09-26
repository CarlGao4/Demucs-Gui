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

import logging
import os
import soundfile
import soxr
import subprocess
import traceback
import typing as tp

import shared

os.environ["PATH"] += os.pathsep + str(shared.homeDir / "ffmpeg")

logging.info("Soundfile version: %s" % soundfile.__version__)
logging.info("libsndfile version: %s" % soundfile.__libsndfile_version__)
logging.info("SoXR version: %s" % soxr.__version__)
logging.info("libsoxr version: %s" % soxr.__libsoxr_version__)


def checkFFMpeg():
    try:
        p = subprocess.Popen(["ffmpeg", "-version"], stdout=subprocess.PIPE)
        out, _ = p.communicate()
        out = out.decode()
        logging.info("ffmpeg -version output:\n" + out)
        ffmpeg_version = out.strip().splitlines()[0].strip()
        p = subprocess.Popen(["ffprobe", "-version"], stdout=subprocess.PIPE)
        out, _ = p.communicate()
        out = out.decode()
        logging.info("ffprobe -version output:\n" + out)
        return ffmpeg_version
    except:
        logging.warning("FFMpeg cannot start:\n" + traceback.format_exc())
        return False


def read_audio(file, target_sr=None, update_status: tp.Callable[[str], None] = lambda _: None):
    if callable(update_status):
        update_status(f"Reading audio: {file.name if hasattr(file, 'name') else file}")
    try:
        audio, sr = soundfile.read(file, dtype="float32", always_2d=True)
    except soundfile.LibsndfileError:
        logging.error(f"Failed to read file {file}:\n" + traceback.format_exc())
        return
    logging.info(f"Read audio {file}: samplerate={sr} shape={audio.shape}")
    if target_sr is not None and sr != target_sr:
        logging.info(f"Samplerate {sr} doesn't match target {target_sr}, resampling with SoXR")
        if callable(update_status):
            update_status("Resampling audio")
        audio = soxr.resample(audio, sr, target_sr, "VHQ")
    return audio

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

import io
import logging
import os
import shlex
import soundfile
import soxr
import traceback
import typing as tp

import shared

if shared.GetSetting("prepend_ffmpeg_path", False):
    os.environ["PATH"] += os.pathsep + str(shared.homeDir / "ffmpeg")
else:
    os.environ["PATH"] = str(shared.homeDir / "ffmpeg") + os.pathsep + os.environ["PATH"]

logging.info("Soundfile version: %s" % soundfile.__version__)
logging.info("libsndfile version: %s" % soundfile.__libsndfile_version__)
logging.info("SoXR version: %s" % soxr.__version__)
logging.info("libsoxr version: %s" % soxr.__libsoxr_version__)

ffmpeg_available = False

format_filter = "libsndfile (%s)" % " ".join(f"*.{format}".lower() for format in soundfile.available_formats().keys())


def checkFFMpeg():
    try:
        p = shared.Popen(["ffmpeg", "-version"])
        out, _ = p.communicate()
        out = out.decode()
        logging.info("ffmpeg -version output:\n" + out)
        ffmpeg_version = out.strip().splitlines()[0].strip()
        p = shared.Popen(["ffprobe", "-version"])
        out, _ = p.communicate()
        out = out.decode()
        logging.info("ffprobe -version output:\n" + out)
        global ffmpeg_available, format_filter
        ffmpeg_available = True
        format_filter += ";;All types (*.*)"
        return ffmpeg_version
    except:
        logging.warning("FFMpeg cannot start:\n" + traceback.format_exc())
        return False


def read_audio(file, target_sr=None, update_status: tp.Callable[[str], None] = lambda _: None):
    logging.debug("Reading audio with soundfile: %s" % file)
    try:
        return read_audio_soundfile(file, target_sr, update_status)
    except soundfile.LibsndfileError:
        logging.error("Failed to read with soundfile:\n" + traceback.format_exc())
    logging.debug("Reading audio with ffmpeg: %s" % file)
    try:
        return read_audio_ffmpeg(file, target_sr, update_status)
    except shared.subprocess.CalledProcessError:
        logging.error("Failed to read with ffmpeg:\n" + traceback.format_exc())


def read_audio_soundfile(file, target_sr=None, update_status: tp.Callable[[str], None] = lambda _: None):
    if callable(update_status):
        update_status(f"Reading audio: {file.name if hasattr(file, 'name') else file}")
    audio, sr = soundfile.read(file, dtype="float32", always_2d=True)
    logging.info(f"Read audio {file}: samplerate={sr} shape={audio.shape}")
    assert audio.shape[0] > 0, "Audio is empty"
    if target_sr is not None and sr != target_sr:
        logging.info(f"Samplerate {sr} doesn't match target {target_sr}, resampling with SoXR")
        if callable(update_status):
            update_status("Resampling audio")
        audio = soxr.resample(audio, sr, target_sr, "VHQ")
    return audio


def read_audio_ffmpeg(file, target_sr=None, update_status: tp.Callable[[str], None] = lambda _: None):
    if not ffmpeg_available:
        raise NotImplementedError("FFmpeg is not available")
    if callable(update_status):
        update_status(f"Reading file metadata: {file.name if hasattr(file, 'name') else file}")
    p = shared.Popen(["ffprobe", "-v", "warning", "-of", "xml", "-show_streams", "-show_format", str(file)])
    logging.debug("ffprobe command: %s" % shlex.join(p.args))
    logging.info(p.communicate()[0].decode())
    if callable(update_status):
        update_status(f"Reading audio: {file.name if hasattr(file, 'name') else file}")
    command = ["ffmpeg", "-v", "warning", "-i", str(file), "-map", "a:0"]
    if target_sr is not None:
        command += ["-ar", str(target_sr)]
    command += ["-c:a", "pcm_f32le", "-f", "wav", "-"]
    p = shared.Popen(command)
    logging.debug("ffmpeg command: %s" % shlex.join(p.args))
    wav_buffer = io.BytesIO()
    wav_buffer.write(p.stdout.read())
    wav_buffer.seek(0)
    ffmpeg_log = p.stderr.read().decode()
    if ffmpeg_log:
        logging.debug(p.stderr.read().decode())
    audio, sr = soundfile.read(wav_buffer, dtype="float32", always_2d=True)
    logging.info(f"Read audio {file}: samplerate={sr} shape={audio.shape}")
    assert audio.shape[0] > 0, "Audio is empty"
    return audio


def save_audio(file, audio, format, sr, update_status: tp.Callable[[str], None] = lambda _: None):
    if callable(update_status):
        update_status(f"Saving audio: {file.name}")
    try:
        soundfile.write(file, audio.transpose(0, 1).numpy(), sr, format)
    except soundfile.LibsndfileError:
        logging.error(f"Failed to write file {file}:\n" + traceback.format_exc())
        return
    logging.info(f"Saved audio {file}: shape={audio.shape}")

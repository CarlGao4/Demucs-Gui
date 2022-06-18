# Demucs-GUI 0.1
# Copyright (C) 2022  Carl Gao, Jize Guo, Rosario S.E.

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

import numpy as np
import julius
import torch
import soundfile
import os
import logging
import traceback
import io
import wave
import _thread
import subprocess
from DemucsCallCore import *


def convert_audio(wav, from_samplerate, to_samplerate, channels):
    """Convert audio from a given samplerate to a target one and target number of channels."""
    wav = convert_audio_channels(wav, channels)
    return julius.resample_frac(wav, from_samplerate, to_samplerate)


def convert_audio_channels(wav, channels=2):
    """Convert audio to the given number of channels."""
    *shape, src_channels, length = wav.shape
    if src_channels == channels:
        pass
    elif channels == 1:
        # Case 1:
        # The caller asked 1-channel audio, but the stream have multiple
        # channels, downmix all channels.
        wav = wav.mean(dim=-2, keepdim=True)
    elif src_channels == 1:
        # Case 2:
        # The caller asked for multiple channels, but the input file have
        # one single channel, replicate the audio over all channels.
        wav = wav.expand(*shape, channels, length)
    elif src_channels >= channels:
        # Case 3:
        # The caller asked for multiple channels, and the input file have
        # more channels than requested. In that case return the first channels.
        wav = wav[..., :channels, :]
    else:
        # Case 4: What is a reasonable choice here?
        raise ValueError("The audio file has less channels than requested but is not mono.")
    return wav


def load_audio(fn, sr):
    audio, raw_sr = soundfile.read(fn, dtype="float32")
    if len(audio.shape) == 1:
        audio = np.atleast_2d(audio).transpose()
    converted = convert_audio(torch.from_numpy(audio.transpose()), raw_sr, sr, 2)
    return converted.numpy()


def load_file_ffmpeg(fn, sr):
    p = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "warning",
            "-i",
            fn,
            "-map",
            "0:a:0",
            "-ar",
            str(sr),
            "-ac",
            "2",
            "-f",
            "wav",
            "-c:a",
            "pcm_f32le",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    b = io.BytesIO(p.stdout.read())
    p.stdout.close()
    if p.returncode != 0:
        return (p.stderr.read(),)
    return (p.stderr.read(), soundfile.read(b))


def i16_pcm(wav):
    """Convert audio to 16 bits integer PCM format."""
    if wav.dtype.is_floating_point:
        return (wav.clamp_(-1, 1) * (2**15 - 1)).short()
    else:
        return wav


def write_wav(wav, filename, samplerate):
    wav = i16_pcm(wav).numpy()
    with wave.open(filename, "wb") as f:
        f.setnchannels(wav.shape[1])
        f.setsampwidth(2)
        f.setframerate(samplerate)
        f.writeframes(wav.tobytes())


def process(
    model: HDemucs,
    infile: pathlib.Path,
    write: bool = True,
    outpath: pathlib.Path = pathlib.Path(""),
    split: float = 10.0,
    overlap: float = 0.25,
    sample_rate: int = 44100,
    shifts: int = 1,
    device: Literal["cpu", "cuda"] = "cuda" if torch.cuda.is_available() else "cpu",
    callback=None,
):
    def call(status):
        if callable(callback):
            _thread.start_new_thread(callback, (status,))

    split = int(split * sample_rate)
    overlap = int(overlap * split)
    call("Loading file")
    audio = load_audio(str(infile), sample_rate)
    logging.debug(f"Loaded audio of shape {audio.shape}")
    orig_len = audio.shape[1]
    n = int(np.ceil((orig_len - overlap) / (split - overlap)))
    audio = np.pad(audio, [(0, 0), (0, n * (split - overlap) + overlap - orig_len)])
    call("Loading model to device %s" % device)
    model.to(device)
    stems = GetData(model)["sources"]
    new_audio = np.zeros((len(stems), 2, audio.shape[1]))
    total = np.zeros(audio.shape[1])
    call("Total splits of '%s' : %d" % (str(infile), n))
    for i in range(n):
        call("Separation %d/%d" % (i + 1, n))
        l = i * (split - overlap)
        r = l + split
        result = Apply(model, torch.from_numpy(audio[:, l:r]).to(device))
        for (j, stem) in enumerate(stems):
            new_audio[j, :, l:r] += result[stem].cpu().numpy()
        total[l:r] += 1
    if write:
        call("Writing to file")
        outpath.mkdir(exist_ok=True)
        for i in range(len(stems)):
            stem = (new_audio[i] / total)[:, :orig_len]
            # torchaudio.save(f"{stems[i]}.wav", i16_pcm(torch.from_numpy(stem)), sample_rate)
            try:
                soundfile.write(str(outpath / f"{stems[i]}.wav"), stem, sample_rate, format="WAV", subtype="PCM_16")
            except:
                call("Failed to write with soundfile, using wave instead")
                logging.error(traceback.format_exc())
                write_wav(torch.from_numpy(stem.transpose()), str(outpath / f"{stems[i]}.wav"), sample_rate)

    else:
        pass

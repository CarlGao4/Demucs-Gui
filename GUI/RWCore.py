# Demucs-GUI 0.1a2
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
import io
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
    # audio, raw_sr = torchaudio.load(fn)
    # audio.to("cpu")
    # return convert_audio(audio, raw_sr, sr, 2).numpy().transpose()
    audio, raw_sr = soundfile.read(fn)
    return convert_audio(torch.from_numpy(audio), raw_sr, sr, 2).numpy().transpose()


def load_file_ffmpeg(fn, sr):
    p = subprocess.Popen(['ffmpeg', '-v', 'warning', '-i', fn, '-map', '0:a:0', '-ar', str(sr), '-ac', '2', '-f', 'wav', '-c:a', 'pcm_f32le', '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    b = io.BytesIO(p.stdout.read())
    p.stdout.close()
    if p.returncode != 0:
        return (p.stderr.read(), )
    return(p.stderr.read(), soundfile.read(b))


def i16_pcm(wav):
    """Convert audio to 16 bits integer PCM format."""
    if wav.dtype.is_floating_point:
        return (wav.clamp_(-1, 1) * (2**15 - 1)).short()
    else:
        return wav


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
    orig_len = audio.shape[0]
    n = int(np.ceil((orig_len - overlap) / (split - overlap)))
    audio = np.pad(audio, [(0, n * (split - overlap) + overlap - orig_len), (0, 0)])
    call("Loading model to device %s" % device)
    model.to(device)
    stems = GetData(model)["sources"]
    new_audio = np.zeros((len(stems), 2, audio.shape[0]))
    total = np.zeros(audio.shape[0])
    call("Total splits of '%s' : %d" % (str(infile), n))
    for i in range(n):
        call("Separation %d/%d" % (i + 1, n))
        l = i * (split - overlap)
        r = l + split
        result = Apply(model, torch.from_numpy(audio[l:r].transpose()).to(device), shifts=shifts)
        for (i, stem) in enumerate(stems):
            new_audio[i, :, l:r] += result[stem].cpu().numpy()
        total[l:r] += 1
    if write:
        call("Writing to file")
        outpath.mkdir(exist_ok=True)
        os.chdir(outpath)
        for i in range(len(stems)):
            stem = (new_audio[i] / total)[:orig_len]
            # torchaudio.save(f"{stems[i]}.wav", i16_pcm(torch.from_numpy(stem)), sample_rate)
            soundfile.write(f"{stems[i]}.wav", stem, sample_rate, subtype='PCM_16')
    else:
        pass

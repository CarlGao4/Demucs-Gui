import numpy as np
import julius
import torch
import torchaudio
import os
import time
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
        raise ValueError('The audio file has less channels than requested but is not mono.')
    return wav

def load_audio(fn, sr):
    audio, raw_sr = torchaudio.load(fn)
    audio.to("cpu")
    return convert_audio(audio, raw_sr, sr, 2).numpy().transpose()
def i16_pcm(wav):
    """Convert audio to 16 bits integer PCM format."""
    if wav.dtype.is_floating_point:
        return (wav.clamp_(-1, 1) * (2**15 - 1)).short()
    else:
        return wav

def process(model: HDemucs,
            infile: pathlib.Path,
            write: bool = True,
            outpath: pathlib.Path = pathlib.Path(""),
            duration: float = 10.,
            overlap: float = 0.25,
            sample_rate: int = 44100,
            shifts: int = 1,
            device: Literal["cpu", "cuda"] = "cuda" if torch.cuda.is_available() else "cpu"):
    duration = int(duration * sample_rate)
    overlap = int(overlap * duration)
    audio = load_audio(str(infile), sample_rate)
    orig_len = audio.shape[0]
    n = int(np.ceil((orig_len - overlap) / (duration - overlap)))
    audio = np.pad(audio, [(0, n * (duration - overlap) + overlap - orig_len), (0, 0)])
    stems = GetData(model)["sources"]
    new_audio = np.zeros((len(stems)+1, 2, audio.shape[0]))
    print("Total splits of '%s' : %d" % (str(infile), n))
    print(time.time())
    for i in range(n):
        print("Processing splited", i+1)
        l = i * (duration - overlap)
        r = l + duration
        result = Apply(model, torch.from_numpy(audio[l:r].transpose()).to(device), shifts=shifts)
        for (i, stem) in enumerate(stems):
            new_audio[i, :, l:r] += result[stem].cpu().numpy()
        new_audio[-1][l:r] += 1
    print(time.time())
    if write:
        outpath.mkdir(exist_ok=True)
        os.chdir(outpath)
        for i in range(len(stems)):
            print((new_audio[i] / new_audio[-1])[:orig_len].shape, torch.from_numpy((new_audio[i] / new_audio[-1])[:orig_len]).shape)
            torchaudio.save(f'{stems[i]}.wav', torch.from_numpy((new_audio[i] / new_audio[-1])[:orig_len]), sample_rate)
    else:
        pass

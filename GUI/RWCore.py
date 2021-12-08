import numpy as np
import miniaudio as ma
import soundfile as sf
import soxr
import wave
import torch
import torchaudio as ta
import os
import time
from DemucsCallCore import *

def load_audio(fn, sr):
    try:
        raw_sr = ma.get_file_info(fn).sample_rate
        audio_file = ma.decode_file(fn, ma.SampleFormat.FLOAT32, 2, raw_sr)
        audio = np.array(audio_file.samples)
    except ma.DecodeError:
        audio, raw_sr = sf.read(fn, dtype='float32', always_2d=True)
        assert audio.shape[1] <= 2, 'Not supported'
        if audio.shape[1] == 1:
            audio = np.hstack(audio, audio)
    if raw_sr != sr:
        audio = soxr.resample(audio, raw_sr, sr)
    return audio

def process(model: HDemucs,
            infile: pathlib.Path,
            write: bool = True,
            outpath: pathlib.Path = pathlib.Path(""),
            duration: float = 10.,
            overlap: float = 0.25,
            sample_rate: int = 44100,
            shifts: int = 1,
            device: Literal["cpu", "cuda"] = "cuda" if torch.cuda.is_available() else "cpu"):
    # assert out_stems in [2, 4], 'Invalid out_stems'
    duration = int(duration * sample_rate)
    overlap = int(overlap * duration)
    audio = load_audio(str(infile), sample_rate)
    orig_len = audio.shape[0]
    n = int(np.ceil((orig_len - overlap) / (duration - overlap)))
    audio = np.pad(audio, [(0, n * (duration - overlap) + overlap - orig_len), (0, 0)])
    stems = GetData(model)["sources"]
    new_audio = np.zeros((len(stems)+1, 2, audio.shape[0]))
    print(time.time())
    for i in range(n):
        print("Processing splited", i)
        l = i * (duration - overlap)
        r = l + duration
        result = Apply(model, torch.from_numpy(audio[l:r].transpose()).to(device), shifts=shifts)
        for (i, stem) in enumerate(stems):
            new_audio[i, :, l:r] += result[stem].cpu().numpy()
        new_audio[-1][l:r] += 1
    print(time.time())
    # if out_stems == 2:
    #     new_audio[:][1] += new_audio[:][2]
    #     new_audio[:][1] += new_audio[:][3]
    if write:
        outpath.mkdir(exist_ok=True)
        os.chdir(outpath)
        for i in range(len(stems)):
            # sf.write(f'{stems[i]}.wav', (new_audio[i] / new_audio[-1])[:orig_len], sample_rate, "PCM_16")
            print(type((new_audio[i] / new_audio[-1])[:orig_len]), (new_audio[i] / new_audio[-1])[:orig_len].shape, torch.from_numpy((new_audio[i] / new_audio[-1])[:orig_len]).shape)
            ta.save(f'{stems[i]}.wav', torch.from_numpy((new_audio[i] / new_audio[-1])[:orig_len]), sample_rate)
    else:
        pass
'''
def process(model: HDemucs,
            infile: pathlib.Path,
            write: bool = True,
            outpath: pathlib.Path = pathlib.Path(""),
            duration: float = 10.,
            overlap: float = 0.25,
            sample_rate: int = 44100,
            shifts: int = 1,
            device: Literal["cpu", "cuda"] = "cuda" if torch.cuda.is_available() else "cpu"):
    # assert out_stems in [2, 4], 'Invalid out_stems'
    duration = int(duration * sample_rate)
    overlap = int(overlap * duration)
    audio = torch.from_numpy(load_audio(str(infile), sample_rate))
    orig_len = audio.shape[0]
    n = math.ceil((orig_len - overlap) / (duration - overlap))
    audio = torch.nn.functional.pad(audio, [(0, n * (duration - overlap) + overlap - orig_len), (0, 0)])
    print(type(audio), audio.shape)
    stems = GetData(model)["sources"]
    new_audio = np.zeros((len(stems)+1, 2, audio.shape[0]))
    print(time.time())
    for i in range(n):
        print("Processing splited", i)
        l = i * (duration - overlap)
        r = l + duration
        result = Apply(model, torch.from_numpy(audio[l:r].transpose()).to(device), shifts=shifts)
        for (i, stem) in enumerate(stems):
            new_audio[i, :, l:r] += result[stem].cpu().numpy()
        new_audio[-1][l:r] += 1
    print(time.time())
    # if out_stems == 2:
    #     new_audio[:][1] += new_audio[:][2]
    #     new_audio[:][1] += new_audio[:][3]
    if write:
        outpath.mkdir(exist_ok=True)
        os.chdir(outpath)
        for i in range(len(stems)):
            # sf.write(f'{stems[i]}.wav', (new_audio[i] /
            #          new_audio[-1])[:orig_len], sample_rate, "PCM_16")
            print(orig_len)
            writewave(pathlib.Path(f'{stems[i]}.wav'), (new_audio[i] / new_audio[-1])[:orig_len], sample_rate)
    else:
        pass
'''

if __name__ == "__main__":
    print("Started")
    model = GetModel(device="cuda")
    print("Model Loaded")
    process(model, pathlib.Path(r"C:\TempUse\功夫熊猫2配音片段_48s.wav"), outpath=pathlib.Path("./testdemucs"), duration=16, device="cuda")

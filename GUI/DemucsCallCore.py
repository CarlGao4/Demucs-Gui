from demucs.pretrained import get_model
from demucs.hdemucs import HDemucs
from demucs.apply import BagOfModels, apply_model
import pathlib
import torch
from typing import Literal


def GetModel(name: str = "mdx_extra_q", repo: pathlib.Path = None,
             device: Literal["cpu", "cuda"] = "cuda" if torch.cuda.is_available() else "cpu") -> HDemucs:
    model = get_model(name=name, repo=repo)
    model.to(device)
    model.eval()
    return model


def GetData(model: HDemucs):
    res = {}
    # Number of audio channels
    res["channels"] = model.audio_channels
    # Require audio sample rate
    res["samplerate"] = model.samplerate
    # Number of models in the bag
    if isinstance(model, BagOfModels):
        res["models"] = len(model.models)
    else:
        res["models"] = 1
    # list of final output tracks
    res["sources"] = model.sources
    return res


def Apply(model: HDemucs,
          wav: torch.Tensor,
          shifts: int = 1,
          ) -> dict:
    #   device: Literal["cpu", "cuda"] = "cuda" if torch.cuda.is_available() else "cpu") -> dict:
    audio = wav
    # audio.to(device)
    ref = audio.mean(0)
    audio = (audio - ref.mean()) / ref.std()
    sources = apply_model(model, audio[None], shifts=shifts, split=False, overlap=0.25, progress=False)[0]
    sources = sources * ref.std() + ref.mean()
    return dict(zip(model.sources, sources))

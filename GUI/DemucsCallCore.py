import demucs.separate
import demucs.pretrained
import demucs.hdemucs
import demucs.apply
import pathlib
import torch
from typing import Literal


def GetModel(name: str = "mdx_extra_q", repo: pathlib.Path = "",
             device: Literal["cpu", "cuda"] = "cuda"
             if torch.cuda.is_available() else "cpu") -> demucs.hdemucs.HDemucs:
    model = demucs.pretrained.get_model(name=name, repo=repo)
    model.to(device)
    model.eval()
    return model


def GetData(model: demucs.hdemucs.HDemucs):
    res = {}
    # Number of audio channels
    res["channels"] = model.audio_channels
    # Require audio sample rate
    res["samplerate"] = model.samplerate
    # Number of models in the bag
    if isinstance(model, demucs.apply.BagOfModels):
        res["models"] = len(model.models)
    else:
        res["models"] = 1
    # list of final output tracks
    res["sources"] = model.sources
    return res


def Apply(model: demucs.hdemucs.HDemucs,
          wav: torch.Tensor,
          shifts: int = 1) -> dict:
    audio = wav
    ref = audio.mean(0)
    audio = (audio - ref.mean()) / ref.std()
    sources = demucs.apply.apply_model(
        model, wav[None], shifts=shifts, split=False, overlap=0.25, progress=False)[0]
    sources = sources * ref.std() + ref.mean()
    return dict(zip(sources, model.sources))

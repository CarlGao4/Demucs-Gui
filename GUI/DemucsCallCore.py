# Demucs-GUI 0.1a1
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

from demucs.pretrained import get_model as _gm
from demucs.hdemucs import HDemucs
from demucs.apply import BagOfModels, apply_model
import pathlib
import torch
from typing import Literal


def GetModel(name: str = "mdx_extra_q", repo: pathlib.Path = None,
             device: Literal["cpu", "cuda"] = "cuda" if torch.cuda.is_available() else "cpu") -> HDemucs:
    model = _gm(name=name, repo=repo)
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

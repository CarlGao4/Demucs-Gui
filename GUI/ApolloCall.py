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

import os
import torch as th
from torch.nn import functional as F
from typing import Optional, Union, Tuple, Dict, Callable, List, Hashable, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import copy
import julius
import look2hear.models
import tqdm
import random
import logging
import inspect
import yaml


# Modified from api.py and apply.py in Demucs
# Though the author of original code is me


class _NotProvided:
    pass


NotProvided = _NotProvided()


def _replace_dict(_dict: Optional[dict], *subs: Tuple[Hashable, Any]) -> dict:
    if _dict is None:
        _dict = {}
    else:
        _dict = copy.copy(_dict)
    for key, value in subs:
        _dict[key] = value
    return _dict


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


def convert_audio(wav, from_samplerate, to_samplerate, channels) -> th.Tensor:
    """Convert audio from a given samplerate to a target one and target number of channels."""
    wav = convert_audio_channels(wav, channels)
    return julius.resample_frac(wav, from_samplerate, to_samplerate)


class CancelledError(Exception):
    """The Future was cancelled."""

    pass


class DummyPoolExecutor:
    class DummyResult:
        def __init__(self, func, _dict, *args, **kwargs):
            self.func = func
            self._dict = _dict
            self.args = args
            self.kwargs = kwargs

        def result(self):
            if self._dict["run"]:
                return self.func(*self.args, **self.kwargs)
            else:
                raise CancelledError()

    def __init__(self, workers=0):
        self._dict = {"run": True}

    def submit(self, func, *args, **kwargs):
        return DummyPoolExecutor.DummyResult(func, self._dict, *args, **kwargs)

    def shutdown(self, *_, **__):
        self._dict["run"] = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        return


class TensorChunk:
    def __init__(self, tensor, offset=0, length=None):
        total_length = tensor.shape[-1]
        assert offset >= 0
        assert offset < total_length

        if length is None:
            length = total_length - offset
        else:
            length = min(total_length - offset, length)

        if isinstance(tensor, TensorChunk):
            self.tensor = tensor.tensor
            self.offset = offset + tensor.offset
        else:
            self.tensor = tensor
            self.offset = offset
        self.length = length
        self.device = tensor.device

    @property
    def shape(self):
        shape = list(self.tensor.shape)
        shape[-1] = self.length
        return shape

    def padded(self, target_length):
        delta = target_length - self.length
        total_length = self.tensor.shape[-1]
        assert delta >= 0

        start = self.offset - delta // 2
        end = start + target_length

        correct_start = max(0, start)
        correct_end = min(total_length, end)

        pad_left = correct_start - start
        pad_right = end - correct_end

        out = F.pad(self.tensor[..., correct_start:correct_end], (pad_left, pad_right))
        assert out.shape[-1] == target_length
        return out


def tensor_chunk(tensor_or_chunk):
    if isinstance(tensor_or_chunk, TensorChunk):
        return tensor_or_chunk
    else:
        assert isinstance(tensor_or_chunk, th.Tensor)
        return TensorChunk(tensor_or_chunk)


def center_trim(tensor: th.Tensor, reference: Union[th.Tensor, int]):
    """
    Center trim `tensor` with respect to `reference`, along the last dimension.
    `reference` can also be a number, representing the length to trim to.
    If the size difference != 0 mod 2, the extra sample is removed on the right side.
    """
    ref_size: int
    if isinstance(reference, th.Tensor):
        ref_size = reference.size(-1)
    else:
        ref_size = reference
    delta = tensor.size(-1) - ref_size
    if delta < 0:
        raise ValueError("tensor must be larger than reference. " f"Delta is {delta}.")
    if delta:
        tensor = tensor[..., delta // 2 : -(delta - delta // 2)]
    return tensor


def apply_model(
    model: look2hear.models.BaseModel,
    mix: Union[th.Tensor, TensorChunk],
    shifts: int = 1,
    split: bool = True,
    overlap: float = 0.25,
    transition_power: float = 1.0,
    progress: bool = False,
    device=None,
    num_workers: int = 0,
    segment: Optional[float] = None,
    pool=None,
    lock=None,
    callback: Optional[Callable[[dict], None]] = None,
    callback_arg: Optional[dict] = None,
) -> th.Tensor:
    """
    Apply model to a given mixture.

    Args:
        shifts (int): if > 0, will shift in time `mix` by a random amount between 0 and 0.5 sec
            and apply the oppositve shift to the output. This is repeated `shifts` time and
            all predictions are averaged. This effectively makes the model time equivariant
            and improves SDR by up to 0.2 points.
        split (bool): if True, the input will be broken down in 8 seconds extracts
            and predictions will be performed individually on each and concatenated.
            Useful for model with large memory footprint like Tasnet.
        progress (bool): if True, show a progress bar (requires split=True)
        device (torch.device, str, or None): if provided, device on which to
            execute the computation, otherwise `mix.device` is assumed.
            When `device` is different from `mix.device`, only local computations will
            be on `device`, while the entire tracks will be stored on `mix.device`.
        num_workers (int): if non zero, device is 'cpu', how many threads to
            use in parallel.
        segment (float or None): override the model segment parameter.
    """
    if device is None:
        device = mix.device
    else:
        device = th.device(device)
    if pool is None:
        if num_workers > 0 and device.type == "cpu":
            pool = ThreadPoolExecutor(num_workers)
        else:
            pool = DummyPoolExecutor()
    if lock is None:
        lock = Lock()
    callback_arg = _replace_dict(callback_arg, *{"model_idx_in_bag": 0, "shift_idx": 0, "segment_offset": 0}.items())
    kwargs: Dict[str, Any] = {
        "shifts": shifts,
        "split": split,
        "overlap": overlap,
        "transition_power": transition_power,
        "progress": progress,
        "device": device,
        "pool": pool,
        "segment": segment,
        "lock": lock,
    }
    out: Union[float, th.Tensor]
    res: Union[float, th.Tensor]
    if "models" not in callback_arg:
        callback_arg["models"] = 1
    model.to(device)
    model.eval()
    assert transition_power >= 1, "transition_power < 1 leads to weird behavior."
    batch, channels, length = mix.shape
    if shifts:
        kwargs["shifts"] = 0
        max_shift = int(0.5 * model._sample_rate)
        mix = tensor_chunk(mix)
        assert isinstance(mix, TensorChunk)
        padded_mix = mix.padded(length + 2 * max_shift)
        out = 0.0
        for shift_idx in range(shifts):
            offset = random.randint(0, max_shift)
            shifted = TensorChunk(padded_mix, offset, length + max_shift - offset)
            kwargs["callback"] = lambda d, i=shift_idx: (
                callback(_replace_dict(d, ("shift_idx", i))) if callback else None
            )
            res = apply_model(model, shifted, **kwargs, callback_arg=callback_arg)
            shifted_out = res
            out += shifted_out[..., max_shift - offset :]
        out /= shifts
        assert isinstance(out, th.Tensor)
        return out
    elif split:
        kwargs["split"] = False
        out = th.zeros(batch, 1, channels, length, device=mix.device)
        sum_weight = th.zeros(length, device=mix.device)
        if segment is None:
            segment = 10
        assert segment is not None and segment > 0.0
        segment_length: int = int(model._sample_rate * segment)
        stride = int((1 - overlap) * segment_length)
        offsets = range(0, length, stride)
        scale = float(format(stride / model._sample_rate, ".2f"))
        # We start from a triangle shaped weight, with maximal weight in the middle
        # of the segment. Then we normalize and take to the power `transition_power`.
        # Large values of transition power will lead to sharper transitions.
        weight = th.cat(
            [
                th.arange(1, segment_length // 2 + 1, device=device),
                th.arange(segment_length - segment_length // 2, 0, -1, device=device),
            ]
        )
        assert len(weight) == segment_length
        # If the overlap < 50%, this will translate to linear transition when
        # transition_power is 1.
        weight = (weight / weight.max()) ** transition_power
        futures = []
        for offset in offsets:
            chunk = TensorChunk(mix, offset, segment_length)
            future = pool.submit(
                apply_model,
                model,
                chunk,
                **kwargs,
                callback_arg=callback_arg,
                callback=(lambda d, i=offset: callback(_replace_dict(d, ("segment_offset", i))) if callback else None),
            )
            futures.append((future, offset))
            offset += segment_length
        if progress:
            futures = tqdm.tqdm(futures, unit_scale=scale, ncols=120, unit="seconds")
        for future, offset in futures:
            try:
                chunk_out = future.result()  # type: th.Tensor
            except Exception:
                pool.shutdown(wait=True, cancel_futures=True)
                raise
            chunk_length = chunk_out.shape[-1]
            out[..., offset : offset + segment_length] += (weight[:chunk_length] * chunk_out).to(mix.device)
            sum_weight[offset : offset + segment_length] += weight[:chunk_length].to(mix.device)
        assert sum_weight.min() > 0
        out /= sum_weight
        assert isinstance(out, th.Tensor)
        return out
    else:
        mix = tensor_chunk(mix)
        assert isinstance(mix, TensorChunk)
        padded_mix = mix.padded(length).to(device)
        with lock:
            if callback is not None:
                callback(_replace_dict(callback_arg, ("state", "start")))  # type: ignore
        with th.no_grad():
            out = model(padded_mix)
        with lock:
            if callback is not None:
                callback(_replace_dict(callback_arg, ("state", "end")))  # type: ignore
        assert isinstance(out, th.Tensor)
        return center_trim(out, length)


class Enhancer:
    def __init__(
        self,
        model: str = "apollo",
        repo: Path = Path(__file__).parent / "models",
        device: str = "cuda" if th.cuda.is_available() else "cpu",
        shifts: int = 1,
        overlap: float = 0.25,
        split: bool = True,
        segment: Optional[int] = 10,
        jobs: int = 0,
        progress: bool = False,
        callback: Optional[Callable[[dict], None]] = None,
        callback_arg: Optional[dict] = None,
    ):
        """
        `class Enhancer`
        =================

        Parameters
        ----------
        model: Pretrained model name or signature. Default is apollo.
        repo: Folder containing all pre-trained models for use.
        segment: Length (in seconds) of each segment (only available if `split` is `True`). If \
            not specified, will use the command line option.
        shifts: If > 0, will shift in time `wav` by a random amount between 0 and 0.5 sec and \
            apply the oppositve shift to the output. This is repeated `shifts` time and all \
            predictions are averaged. This effectively makes the model time equivariant and \
            improves SDR by up to 0.2 points. If not specified, will use the command line option.
        split: If True, the input will be broken down into small chunks (length set by `segment`) \
            and predictions will be performed individually on each and concatenated. Useful for \
            model with large memory footprint like Tasnet. If not specified, will use the command \
            line option.
        overlap: The overlap between the splits. If not specified, will use the command line \
            option.
        device (torch.device, str, or None): If provided, device on which to execute the \
            computation, otherwise `wav.device` is assumed. When `device` is different from \
            `wav.device`, only local computations will be on `device`, while the entire tracks \
            will be stored on `wav.device`. If not specified, will use the command line option.
        jobs: Number of jobs. This can increase memory usage but will be much faster when \
            multiple cores are available. If not specified, will use the command line option.
        callback: A function will be called when the separation of a chunk starts or finished. \
            The argument passed to the function will be a dict. For more information, please see \
            the Callback section.
        callback_arg: A dict containing private parameters to be passed to callback function. For \
            more information, please see the Callback section.
        progress: If true, show a progress bar.

        Callback
        --------
        The function will be called with only one positional parameter whose type is `dict`. The
        `callback_arg` will be combined with information of current separation progress. The
        progress information will override the values in `callback_arg` if same key has been used.
        To abort the separation, raise `KeyboardInterrupt`.

        Progress information contains several keys (These keys will always exist):
        - `model_idx_in_bag`: The index of the submodel in `BagOfModels`. Starts from 0.
        - `shift_idx`: The index of shifts. Starts from 0.
        - `segment_offset`: The offset of current segment. If the number is 441000, it doesn't
            mean that it is at the 441000 second of the audio, but the "frame" of the tensor.
        - `state`: Could be `"start"` or `"end"`.
        - `audio_length`: Length of the audio (in "frame" of the tensor).
        - `models`: Count of submodels in the model.
        """
        self._name = model
        self._repo = repo
        self._load_model()
        self.update_parameter(
            device=device,
            shifts=shifts,
            overlap=overlap,
            split=split,
            segment=segment,
            jobs=jobs,
            progress=progress,
            callback=callback,
            callback_arg=callback_arg,
        )

    def update_parameter(
        self,
        device: Union[str, _NotProvided] = NotProvided,
        shifts: Union[int, _NotProvided] = NotProvided,
        overlap: Union[float, _NotProvided] = NotProvided,
        split: Union[bool, _NotProvided] = NotProvided,
        segment: Optional[Union[int, _NotProvided]] = NotProvided,
        jobs: Union[int, _NotProvided] = NotProvided,
        progress: Union[bool, _NotProvided] = NotProvided,
        callback: Optional[Union[Callable[[dict], None], _NotProvided]] = NotProvided,
        callback_arg: Optional[Union[dict, _NotProvided]] = NotProvided,
    ):
        """
        Update the parameters of separation.

        Parameters
        ----------
        segment: Length (in seconds) of each segment (only available if `split` is `True`). If \
            not specified, will use the command line option.
        shifts: If > 0, will shift in time `wav` by a random amount between 0 and 0.5 sec and \
            apply the oppositve shift to the output. This is repeated `shifts` time and all \
            predictions are averaged. This effectively makes the model time equivariant and \
            improves SDR by up to 0.2 points. If not specified, will use the command line option.
        split: If True, the input will be broken down into small chunks (length set by `segment`) \
            and predictions will be performed individually on each and concatenated. Useful for \
            model with large memory footprint like Tasnet. If not specified, will use the command \
            line option.
        overlap: The overlap between the splits. If not specified, will use the command line \
            option.
        device (torch.device, str, or None): If provided, device on which to execute the \
            computation, otherwise `wav.device` is assumed. When `device` is different from \
            `wav.device`, only local computations will be on `device`, while the entire tracks \
            will be stored on `wav.device`. If not specified, will use the command line option.
        jobs: Number of jobs. This can increase memory usage but will be much faster when \
            multiple cores are available. If not specified, will use the command line option.
        callback: A function will be called when the separation of a chunk starts or finished. \
            The argument passed to the function will be a dict. For more information, please see \
            the Callback section.
        callback_arg: A dict containing private parameters to be passed to callback function. For \
            more information, please see the Callback section.
        progress: If true, show a progress bar.

        Callback
        --------
        The function will be called with only one positional parameter whose type is `dict`. The
        `callback_arg` will be combined with information of current separation progress. The
        progress information will override the values in `callback_arg` if same key has been used.
        To abort the separation, raise `KeyboardInterrupt`.

        Progress information contains several keys (These keys will always exist):
        - `model_idx_in_bag`: The index of the submodel in `BagOfModels`. Starts from 0.
        - `shift_idx`: The index of shifts. Starts from 0.
        - `segment_offset`: The offset of current segment. If the number is 441000, it doesn't
            mean that it is at the 441000 second of the audio, but the "frame" of the tensor.
        - `state`: Could be `"start"` or `"end"`.
        - `audio_length`: Length of the audio (in "frame" of the tensor).
        - `models`: Count of submodels in the model.
        """
        if not isinstance(device, _NotProvided):
            self._device = device
        if not isinstance(shifts, _NotProvided):
            self._shifts = shifts
        if not isinstance(overlap, _NotProvided):
            self._overlap = overlap
        if not isinstance(split, _NotProvided):
            self._split = split
        if not isinstance(segment, _NotProvided):
            self._segment = segment
        if not isinstance(jobs, _NotProvided):
            self._jobs = jobs
        if not isinstance(progress, _NotProvided):
            self._progress = progress
        if not isinstance(callback, _NotProvided):
            self._callback = callback
        if not isinstance(callback_arg, _NotProvided):
            self._callback_arg = callback_arg

    def _load_model(self):
        if (self._repo / f"{self._name}.bin").exists():
            conf = th.load(self._repo / f"{self._name}.bin", map_location="cpu")
        elif (self._repo / f"{self._name}.ckpt").exists():
            conf = th.load(self._repo / f"{self._name}.ckpt", map_location="cpu")
        # If the model config is provided along with the model, read additional information
        if (self._repo / f"{self._name}.yml").exists():
            logging.info(f"Found model config file! Reading config from {self._repo / f'{self._name}.yml'}")
            with open(self._repo / f"{self._name}.yml", "rt", encoding="utf-8") as f:
                model_init_config = yaml.safe_load(f)["model"]
            logging.info(f"model init config: {model_init_config}")
        elif (self._repo / f"{self._name}.yaml").exists():
            logging.info(f"Found model config file! Reading config from {self._repo / f'{self._name}.yaml'}")
            with open(self._repo / f"{self._name}.yaml", "rt", encoding="utf-8") as f:
                model_init_config = yaml.safe_load(f)["model"]
            logging.info(f"model init config: {model_init_config}")
        else:
            model_init_config = {}
        model_class = look2hear.models.get(conf["model_name"])
        init_args = conf["model_args"]
        logging.info(f"model init args: {init_args}")
        # Uses args from the model when a same key is provided in both the model config and the model
        model_init_config.update(init_args)
        init_args = model_init_config
        # We need to remove the parameters that are not in the model constructor
        # Get all argument names that can be specified with keyword arguments
        params = inspect.signature(model_class.__init__).parameters.copy()
        # Remove 'self' (the first argument)
        params.pop(next(iter(params)))
        # If the constructor has variadic keyword arguments, we do not to filter unsupported arguments
        if not any(p.kind == p.VAR_KEYWORD for p in params.values()):
            availble_args = set(i for i, j in params.items() if j.kind in {j.POSITIONAL_OR_KEYWORD, j.KEYWORD_ONLY})
            init_args = {k: v for k, v in init_args.items() if k in availble_args}
        self._model = model_class(**init_args)
        self._model.load_state_dict(conf["state_dict"])
        self._samplerate = self._model._sample_rate

    def enhance_tensor(self, wav: th.Tensor, sr: Optional[int] = None) -> Tuple[th.Tensor, th.Tensor]:
        """
        Enhance a loaded tensor.

        Parameters
        ----------
        wav: Waveform of the audio. Should have 2 dimensions, the first is each audio channel, \
            while the second is the waveform of each channel. Type should be float32. \
            e.g. `tuple(wav.shape) == (2, 884000)` means the audio has 2 channels.
        sr: Sample rate of the original audio, the wave will be resampled if it doesn't match the \
            model.

        Returns
        -------
        A tuple, whose first element is the original wave and second element is enhanced waves.

        Notes
        -----
        Use this function with cautiousness. This function does not provide data verifying.
        """
        if sr is not None and sr != self.samplerate:
            wav = convert_audio(wav, sr, self._samplerate, self._audio_channels)
        ref = wav.mean(0)
        wav -= ref.mean()
        wav /= ref.std() + 1e-8
        out = apply_model(
            self._model,
            wav[None],
            segment=self._segment,
            shifts=self._shifts,
            split=self._split,
            overlap=self._overlap,
            device=self._device,
            num_workers=self._jobs,
            callback=self._callback,
            callback_arg=_replace_dict(self._callback_arg, ("audio_length", wav.shape[1])),
            progress=self._progress,
        )
        if out is None:
            raise KeyboardInterrupt
        out *= ref.std() + 1e-8
        out += ref.mean()
        wav *= ref.std() + 1e-8
        wav += ref.mean()
        return wav, out[0]

    @property
    def samplerate(self):
        return self._samplerate

    @property
    def audio_channels(self):
        return None

    @property
    def model(self):
        return self._model


def list_models(repo: Path) -> List[str]:
    """
    List the available models. Please remember that not all the returned models can be
    successfully loaded.

    Parameters
    ----------
    repo: The repo whose models are to be listed.

    Returns
    -------
    A list of model names.
    """
    files = os.listdir(repo)
    ckpts = set(f[:-4] for f in files if f.endswith(".bin")) | set(f[:-5] for f in files if f.endswith(".ckpt"))
    return list(ckpts)

# Demucs-GUI
# Copyright (C) 2022-2024  Demucs-GUI developers
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

import hashlib
import json
import logging
import os
import pathlib
import platform
import psutil
import shutil
import sys
import time
import traceback
import typing as tp
import urllib.parse
import urllib.request
import yaml

from fractions import Fraction

import shared


default_device = 0
used_cuda = False
used_xpu = False
has_Intel = False
Intel_JIT_only = False

downloaded_models = {}
remote_urls = {}


class ModelSourceNameUnsupportedError(Exception):
    pass


@shared.thread_wrapper(daemon=True)
def starter(update_status: tp.Callable[[str], None], finish: tp.Callable[[float], None]):
    global torch, demucs, audio, has_Intel, Intel_JIT_only, np
    import torch
    import numpy as np

    for i in range(5):
        try:
            global ipex
            ipex = False
            import intel_extension_for_pytorch as ipex  # type: ignore

            logging.info("Intel Extension for PyTorch version: " + ipex.__version__)
        except ModuleNotFoundError:
            logging.info("Intel Extension for PyTorch is not installed")
            break
        except Exception:
            logging.error(
                "Failed to load Intel Extension for PyTorch for the %d time:\n" % (i + 1) + traceback.format_exc()
            )
        else:
            if torch.xpu.is_available():
                has_Intel = True
                if sys.platform == "win32":
                    dll_size = os.path.getsize(ipex.dlls[0])
                    logging.info("IPEX extension dll path: %s" % ipex.dlls[0])
                    logging.info("IPEX extension dll size: %d" % dll_size)
                    if dll_size < 1073741824:
                        logging.info("IPEX extension dll is not large enough, probably JIT only (No AOT)")
                        Intel_JIT_only = True
                break
    import demucs.api
    import demucs.apply
    import audio

    update_status("Successfully loaded modules")
    logging.info("Demucs version: " + demucs.__version__)
    logging.info("PyTorch version: " + torch.__version__)
    if sys.platform == "darwin":
        if torch.backends.mps.is_built() and torch.backends.mps.is_available():  # type: ignore
            update_status("MPS backend is available")
        else:
            update_status("MPS backend is not available")
    else:
        backends = []
        if torch.backends.cuda.is_built() and torch.cuda.is_available():  # type: ignore
            backends.append("CUDA")
            logging.info(
                "CUDA Info: "
                + "    \n".join(str(torch.cuda.get_device_properties(i)) for i in range(torch.cuda.device_count()))
            )
            logging.info("CUDA Arch list: " + str(torch.cuda.get_arch_list()))
        if ipex is not None and hasattr(torch, "xpu") and torch.xpu.is_available():
            backends.append("Intel MKL")
            logging.info(
                "Intel MKL Info: "
                + "    \n".join(str(torch.xpu.get_device_properties(i)) for i in range(torch.xpu.device_count()))
            )
        if backends:
            update_status(", ".join(backends) + " backend is available")
        else:
            update_status("No accelerator backend is available")
    time.sleep(1)
    ffmpeg_version = audio.checkFFMpeg()
    if not ffmpeg_version:
        update_status("FFMpeg is not available")
    else:
        update_status("FFMpeg is available:\n" + ffmpeg_version)
    time.sleep(1)
    finish(2)


def getAvailableDevices():
    global default_device
    devices = []
    devices.append(("CPU - %s (%d MiB)" % (platform.processor(), psutil.virtual_memory().total / 1048576), "cpu"))
    if sys.platform == "darwin":
        if torch.backends.mps.is_built() and torch.backends.mps.is_available():
            devices.append(("MPS (%d MiB)" % (psutil.virtual_memory().total / 1048576), "mps"))
            default_device = 1
            logging.info("MPS backend is available")
        else:
            logging.info("MPS backend is not available")
    else:
        if hasattr(torch, "xpu") and torch.xpu.is_available():
            max_memory = 0
            for i in range(torch.xpu.device_count()):
                device_property = torch.xpu.get_device_properties(i)
                device_info_string = ""
                if hasattr(device_property, "dev_type") and isinstance(device_property.dev_type, str):
                    device_info_string += device_property.dev_type.upper() + " - "
                device_info_string += device_property.name
                if hasattr(device_property, "platform_name") and isinstance(device_property.platform_name, str):
                    device_info_string += " (" + device_property.platform_name + ", "
                else:
                    device_info_string += " ("
                device_info_string += "%d MiB)" % (device_property.total_memory / 1048576)
                devices.append((device_info_string, "xpu:%d" % i))
                if device_property.total_memory > max_memory and device_property.total_memory > 2147480000:
                    max_memory = device_property.total_memory
                    if hasattr(device_property, "gpu_eu_count") and device_property.gpu_eu_count >= 96:
                        default_device = len(devices) - 1
        if torch.backends.cuda.is_built() and torch.cuda.is_available():  # type: ignore
            max_memory = 0
            for i in range(torch.cuda.device_count()):
                device_property = torch.cuda.get_device_properties(i)
                devices.append(
                    (
                        "CUDA - %s (%d MiB)" % (device_property.name, device_property.total_memory / 1048576),
                        "cuda:%d" % i,
                    )
                )
                if device_property.total_memory > max_memory and device_property.total_memory > 2147480000:
                    max_memory = device_property.total_memory
                    default_device = len(devices) - 1
    return devices


def autoListModels():
    global downloaded_models, remote_urls
    bags = []
    singles = []
    custom_repo = shared.GetSetting("custom_repo", [])
    repos = [shared.homeDir / "pretrained", shared.pretrained]
    repos += [pathlib.Path(i) for i in custom_repo]
    repos += [None]
    try:
        torch.hub.set_dir(shared.model_cache)
        checkpoint_dir = shared.model_cache / "checkpoints"
        downloaded_models = demucs.api.list_models(checkpoint_dir)["single"]
    except Exception:
        logging.error("Failed to list downloaded models:\n%s" % traceback.format_exc())
    for repopath in repos:
        if repopath is not None and not repopath.exists():
            continue
        try:
            new_models = demucs.api.list_models(repopath)
        except Exception:
            logging.error("Failed to list models from %s:\n%s" % (str(repopath), traceback.format_exc()))
            continue
        for sig, filepath in new_models["bag"].items():
            info = "Model signature: " + sig
            info += "\nType: Bag of models"
            if repopath is None:
                info += "\nPosition: Remote model"
            else:
                info += "\nPosition: Local model"
                info += "\nRepo: " + str(repopath)
            info += "\nFile: " + str(filepath)
            try:
                with open(filepath, "rt", encoding="utf8") as f:
                    model_def = yaml.load(f, yaml.Loader)
                info += "\nModels:"
                if "weights" in model_def:
                    weights = model_def["weights"]
                    for i, (model, weight) in enumerate(zip(model_def["models"], weights)):
                        info += "\n\u3000%d. %s: %s" % (i + 1, model, weight)
                        if repopath is None:
                            info += " (Downloaded)" if model in downloaded_models else " (Not downloaded)"
                else:
                    for i, model in enumerate(model_def["models"]):
                        info += "\n\u3000%d. %s" % (i + 1, model)
                        if repopath is None:
                            info += " (Downloaded)" if model in downloaded_models else " (Not downloaded)"
                if "segment" in model_def:
                    info += "\nDefault segment: %.1f" % model_def["segment"]
            except Exception:
                logging.error("Failed to load info of model %s:\n%s" % (sig, traceback.format_exc()))
            else:
                remote_urls[sig] = model_def["models"]
                bags.append((sig, info, repopath))
        for sig, filepath in new_models["single"].items():
            info = "Model signature: " + sig
            info += "\nType: Single model"
            if repopath is None:
                info += "\nPosition: Remote model"
                info += "\nURL: " + str(filepath)
                info += "\nState: " + ("Downloaded" if sig in downloaded_models else "Not downloaded")
                if sig in downloaded_models:
                    info += "\nFile: " + str(downloaded_models[sig])
                else:
                    remote_urls[sig] = str(filepath)
            else:
                info += "\nPosition: Local model"
                info += "\nRepo: " + str(repopath)
                info += "\nFile: " + str(filepath)
            singles.append((sig, info, repopath))
    models, infos, each_repos = tuple(zip(*(bags + singles + [("demucs_unittest", "Unit test model", None)])))
    return models, infos, each_repos


def empty_cache():
    if used_cuda:
        for _ in range(10):
            torch.cuda.empty_cache()
    if used_xpu:
        for _ in range(10):
            torch.xpu.empty_cache()


class Separator:
    def __init__(
        self,
        model: str = "htdemucs",
        repo: tp.Optional[pathlib.Path] = None,
        updateStatus: tp.Optional[tp.Callable[[str], None]] = None,
    ):
        if callable(updateStatus):
            self.updateStatus = updateStatus
        else:
            self.updateStatus = lambda *_: None
        if repo is None:
            self.ensureDownloaded(model)
        self.separator = demucs.api.Separator(model=model, repo=repo, progress=False)
        if len(set(self.separator.model.sources)) != len(self.separator.model.sources):
            raise ModelSourceNameUnsupportedError(
                "Duplicate source names in model %s\nSources: %s" % (model, self.separator.model.sources)
            )
        if "origin" in self.separator.model.sources:
            raise ModelSourceNameUnsupportedError("Source name 'origin' is reserved in model %s" % model)
        self.model = model
        self.repo = repo
        if not isinstance(self.separator.model, demucs.apply.BagOfModels):
            self.default_segment = self.separator.model.segment
        else:
            self.default_segment = min(i.segment for i in self.separator.model.models)  # type: ignore
            if hasattr(self.separator.model, "segment"):
                self.default_segment = min(self.default_segment, self.separator.model.segment)
        self.default_segment = max(self.default_segment, 0.1)
        self.sources = self.separator.model.sources
        self.separating = False

    def ensureDownloaded(self, model):
        if model == "demucs_unittest":
            return
        if model in downloaded_models:
            return
        if isinstance(remote_urls[model], list):
            for i in remote_urls[model]:
                self.ensureDownloaded(i)
            return
        # Download codes modified from torch.hub
        try:
            url = remote_urls[model]
        except KeyError:
            err = "Model %s not found\n" % model
            err += "Downloaded models: " + json.dumps(downloaded_models)
            err += "\nRemote models: " + json.dumps(remote_urls)
            raise RuntimeError(err)
        self.updateStatus("Downloading model %s" % model)
        logging.info("Downloading model %s from %s" % (model, url))
        next_update = 0.0
        req = urllib.request.Request(url, headers={"User-Agent": "torch.hub"})
        u = urllib.request.urlopen(req)
        meta = u.info()
        if hasattr(meta, "getheaders"):
            content_length = meta.getheaders("Content-Length")
        else:
            content_length = meta.get_all("Content-Length")
        if content_length is not None and len(content_length) > 0:
            file_size = int(content_length[0])
        file_name = urllib.parse.urlparse(url).path.split("/")[-1]
        tmp_name = file_name + ".tmp"
        tmp_file = shared.model_cache / "checkpoints" / tmp_name  # type: pathlib.Path
        tmp_file.unlink(missing_ok=True)
        f = open(str(tmp_file), "wb")
        file_size_dl = 0
        if len(chunks := file_name.rsplit(".", 1)[0].rsplit("-", 1)) > 1:
            checksum = chunks[-1]
            hasher = hashlib.sha256()
        else:
            checksum = None
        while True:
            buffer = u.read(8192)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
            if checksum is not None:
                hasher.update(buffer)
            if time.time() > next_update:
                status = "Downloading model %s: %s / %s (%.2f%%)" % (
                    model,
                    shared.HSize(file_size_dl),
                    shared.HSize(file_size),
                    file_size_dl * 100.0 / file_size,
                )
                self.updateStatus(status)
                next_update = time.time() + 0.5
        f.close()
        if checksum is not None:
            if not hasher.hexdigest().startswith(checksum):
                tmp_file.unlink(missing_ok=True)
                logging.error(
                    "Checksum mismatch for %s: received %s, expected %s" % (model, hasher.hexdigest(), checksum)
                )
                raise RuntimeError("Checksum mismatch")
        self.updateStatus("Downloaded model %s" % model)
        shutil.move(str(tmp_file), str(tmp_file.parent / file_name))

    def modelInfo(self):
        channels = self.separator.model.audio_channels
        samplerate = self.separator.model.samplerate
        if isinstance(self.separator.model, demucs.apply.BagOfModels):
            infos = []
            weights = self.separator.model.weights
            for i in range(len(self.separator.model.models)):
                segment = self.separator.model.models[i].segment
                infos.append(
                    "Model %d:\n\u3000Type: %s\n\u3000Default segment: %.8g\n\u3000Weight: %s"
                    % (
                        i,
                        self.separator.model.models[i].__class__.__name__,
                        segment,
                        weights[i],
                    )
                )
            return (
                "Model: %s\nRepo: %s\nType: Bag of models\nAudio channels: %d\nSample rate: %d\nSources: %s\n\n%s"
                % (
                    self.model,
                    self.repo if self.repo is not None else '"remote"',
                    channels,
                    samplerate,
                    ", ".join(self.sources),
                    "\n".join(infos),
                )
            )

        return "Model: %s\nRepo: %s\nType: %s\nAudio channels: %d\nSample rate: %d\nSources: %s" % (
            self.model,
            self.repo if self.repo is not None else '"remote"',
            self.separator.model.__class__.__name__,
            channels,
            samplerate,
            ", ".join(self.sources),
        )

    def startSeparate(self, *args, **kwargs):
        if self.separating:
            return
        self.separating = True
        self.separate(*args, **kwargs)

    def updateProgress(self, progress_dict):
        progress = Fraction(0)
        progress_per_model = Fraction(1, progress_dict["models"])
        progress_per_shift = Fraction(1, max(1, self.shifts))
        progress += progress_per_model * progress_dict["model_idx_in_bag"]
        progress_model = Fraction(0)
        progress_model += progress_per_shift * progress_dict["shift_idx"]
        progress_shift = Fraction(progress_dict["segment_offset"], progress_dict["audio_length"])
        if progress_dict["state"] == "end":
            progress_shift += Fraction(
                int(self.segment * (1 - self.overlap) * self.separator.samplerate), progress_dict["audio_length"]
            )
        progress_shift = min(Fraction(1, 1), progress_shift)
        progress_model += progress_per_shift * progress_shift
        progress += progress_model * progress_per_model
        progress *= Fraction(1, self.in_length)
        progress += Fraction(self.out_length, self.in_length)
        current_time = time.time()
        self.time_hists.append((current_time, progress))
        if current_time - self.last_update_eta > 0.5:
            while len(self.time_hists) >= 20 and current_time - self.time_hists[0][0] > 15:
                self.time_hists.pop(0)
            if len(self.time_hists) >= 2 and progress != self.time_hists[0][1]:
                eta = int((1 - progress) / (progress - self.time_hists[0][1]) * (current_time - self.time_hists[0][0]))
            else:
                eta = 1000000000
            if eta >= 99 * 86400:
                eta_str = "--:--:--:--"
            elif eta >= 86400:
                eta_str = "%d:" % (eta // 86400)
                eta %= 86400
                eta_str += time.strftime("%H:%M:%S", time.gmtime(eta))
            else:
                eta_str = time.strftime("%H:%M:%S", time.gmtime(eta))
            self.updateStatus("Separating audio: %s | ETA %s" % (self.file.name, eta_str))
            self.last_update_eta = current_time
        pause_start = time.time()
        self.setModelProgress(min(1.0, float(progress_shift)))
        self.setAudioProgress(min(1.0, float(progress)), self.item)
        pause_end = time.time()
        self.time_hists = [(i[0] + pause_end - pause_start, i[1]) for i in self.time_hists]

    def save_callback(self, *args, encoder="sndfile"):
        match encoder:
            case "sndfile":
                return audio.save_audio_sndfile(*args, self.separator.samplerate, self.updateStatus)
            case "ffmpeg":
                return audio.save_audio_ffmpeg(*args, self.separator.samplerate, self.updateStatus)

    @shared.thread_wrapper(daemon=True)
    def separate(
        self,
        file,
        item,
        segment,
        overlap,
        shifts,
        device,
        save_callback,
        setModelProgress: tp.Callable[[float], None],
        setAudioProgress: tp.Callable[[float, tp.Any], None],
        setStatus: tp.Callable[[tp.Any, int], None],
        finishCallback: tp.Callable[[int, tp.Any], None],
    ):
        logging.info("Start separating audio: %s" % file.name)
        logging.info("Parameters: segment=%.2f overlap=%.2f shifts=%d" % (segment, overlap, shifts))
        logging.info("Device: %s" % device)
        global used_cuda, used_xpu
        if device.startswith("cuda"):
            used_cuda = True
        if device.startswith("xpu"):
            used_xpu = True
        try:
            setStatus(shared.FileStatus.Reading, item)
            wav, tags = audio.read_audio(file, self.separator.model.samplerate, self.updateStatus)
            assert wav is not None
            assert (np.isnan(wav).sum() == 0) and (np.isinf(wav).sum() == 0), "Audio contains NaN or Inf"
        except Exception:
            finishCallback(shared.FileStatus.Failed, item)
            self.separating = False
            return

        self.item = item
        self.shifts = shifts
        self.segment = segment
        self.overlap = overlap
        self.setAudioProgress = setAudioProgress
        self.setModelProgress = setModelProgress
        self.file = file
        self.time_hists = []
        self.last_update_eta = 0

        self.separator.model.to("cpu")  # To avoid moving between different GPUs which may cause error

        try:
            self.updateStatus("Separating audio: %s" % file.name)
            self.separator.update_parameter(
                device=device, segment=segment, shifts=shifts, overlap=overlap, callback=self.updateProgress
            )
            wav_torch = torch.from_numpy(wav).clone().transpose(0, 1)
            assert (not wav_torch.isnan().any()) and (not wav_torch.isinf().any()), "Audio contains NaN or Inf"
            src_channels = wav_torch.shape[0]
            logging.info("Running separation...")
            self.time_hists.append((time.time(), 0))
            if src_channels != self.separator.model.audio_channels:
                out = {stem: torch.zeros(1, wav_torch.shape[1], dtype=torch.float32) for stem in self.sources}
                self.in_length = src_channels
                self.out_length = 0
                for i in range(src_channels):
                    self.out_length += 1
                    for stem, tensor in self.separator.separate_tensor(
                        wav_torch[i, :].repeat(self.separator.model.audio_channels, 1)
                    )[1].items():
                        out[stem][i, :] = tensor.sum(dim=0) / tensor.shape[0]
            else:
                self.in_length = 1
                self.out_length = 0
                out = self.separator.separate_tensor(wav_torch)[1]
        except KeyboardInterrupt:
            finishCallback(shared.FileStatus.Cancelled, item)
            self.separating = False
            return
        except Exception:
            logging.error(traceback.format_exc())
            finishCallback(shared.FileStatus.Failed, item)
            self.separating = False
            return
        finally:
            self.separator.model.to("cpu")
        logging.info("Saving separated audio...")
        save_callback(file, wav_torch, out, tags, self.save_callback, item, finishCallback)
        self.separating = False
        return

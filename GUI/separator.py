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

import logging
import pathlib
import platform
import psutil
import sys
import time
import traceback
import typing as tp
import yaml

from fractions import Fraction

import shared


default_device = 0
used_cuda = False


@shared.thread_wrapper(daemon=True)
def starter(update_status: tp.Callable[[str], None], finish: tp.Callable[[float], None]):
    global torch, demucs, audio
    import torch
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
        if torch.backends.cuda.is_built() and torch.cuda.is_available():  # type: ignore
            update_status("CUDA backend is available")
            logging.info(
                "CUDA Info: "
                + "    \n".join(str(torch.cuda.get_device_properties(i)) for i in range(torch.cuda.device_count()))
            )
        else:
            update_status("CUDA backend is not available")
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
                    default_device = i + 1
    return devices


def autoListModels():
    bags = []
    singles = []
    custom_repo = shared.GetSetting("custom_repo", [])
    repos = [shared.homeDir / "pretrained", shared.pretrained]
    repos += [pathlib.Path(i) for i in custom_repo]
    repos += [None]
    for repopath in repos:
        if repopath is not None and not repopath.exists():
            continue
        try:
            new_models = demucs.api.list_models(repopath)
        except:
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
                    model_def = yaml.safe_load(f)
                if weights := model_def.get("weights"):
                    info += "\nModels and weights:"
                    for i, (model, weight) in enumerate(zip(model_def["models"], weights)):
                        info += "\n\u3000%d. %s: %s" % (i + 1, model, weight)
                else:
                    info += "\nModels: " + ", ".join(model_def["models"])
                if segment := model_def.get("segment"):
                    info += "\nDefault segment: %.1f" % segment
            except:
                logging.error("Failed to load info of model %s:\n%s" % (sig, traceback.format_exc()))
            bags.append((sig, info, repopath))
        for sig, filepath in new_models["single"].items():
            info = "Model signature: " + sig
            info += "\nType: Single model"
            if repopath is None:
                info += "\nPosition: Remote model"
                info += "\nURL: " + str(filepath)
            else:
                info += "\nPosition: Local model"
                info += "\nRepo: " + str(repopath)
                info += "\nFile: " + str(filepath)
            singles.append((sig, info, repopath))
    models, infos, each_repos = tuple(zip(*(bags + singles + [("demucs_unittest", "Unit test model", None)])))
    return models, infos, each_repos


def empty_cuda_cache():
    if used_cuda:
        for _ in range(10):
            torch.cuda.empty_cache()


class Separator:
    def __init__(
        self,
        model: str = "htdemucs",
        repo: tp.Optional[pathlib.Path] = None,
        updateStatus: tp.Optional[tp.Callable[[str], None]] = None,
    ):
        self.separator = demucs.api.Separator(model=model, repo=repo, progress=False)
        self.model = model
        self.repo = repo
        if callable(updateStatus):
            self.updateStatus = updateStatus
        else:
            self.updateStatus = lambda *_: None
        if not isinstance(self.separator.model, demucs.apply.BagOfModels):
            self.default_segment = self.separator.model.segment
        else:
            self.default_segment = min(i.segment for i in self.separator.model.models)  # type: ignore
            if hasattr(self.separator.model, "segment"):
                self.default_segment = min(self.default_segment, self.separator.model.segment)
        self.default_segment = max(self.default_segment, 0.1)
        self.sources = self.separator.model.sources
        self.separating = False

    def modelInfo(self):
        channels = self.separator.model.audio_channels
        samplerate = self.separator.model.samplerate
        sources = self.separator.model.sources
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
                    ", ".join(sources),
                    "\n".join(infos),
                )
            )

        return "Model: %s\nRepo: %s\nType: %s\nAudio channels: %d\nSample rate: %d\nSources: %s" % (
            self.model,
            self.repo if self.repo is not None else '"remote"',
            self.separator.model.__class__.__name__,
            channels,
            samplerate,
            ", ".join(sources),
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
        self.setModelProgress(min(1.0, float(progress_shift)))
        self.setAudioProgress(min(1.0, float(progress)), self.item)
        current_time = time.time()
        self.time_hists.append((current_time, progress))
        if current_time - self.last_update_eta > 1:
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

    def save_callback(self, *args):
        audio.save_audio(*args, self.separator.samplerate, self.updateStatus)

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
        global used_cuda
        if device.startswith("cuda"):
            used_cuda = True
        try:
            setStatus(shared.FileStatus.Reading, item)
            wav = audio.read_audio(file, self.separator.model.samplerate, self.updateStatus)
            assert wav is not None
        except:
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

        try:
            self.updateStatus("Separating audio: %s" % file.name)
            self.separator.update_parameter(
                device=device, segment=segment, shifts=shifts, overlap=overlap, callback=self.updateProgress
            )
            wav_torch = torch.from_numpy(wav).clone().transpose(0, 1)
            src_channels = wav_torch.shape[0]
            logging.info("Running separation...")
            self.time_hists.append((time.time(), 0))
            if src_channels != self.separator.model.audio_channels:
                out = {}
                for stem in self.separator.model.sources:
                    out[stem] = torch.zeros(src_channels, wav_torch.shape[1], dtype=torch.float32)
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
        except:
            logging.error(traceback.format_exc())
            finishCallback(shared.FileStatus.Failed, item)
            self.separating = False
            return
        logging.info("Saving separated audio...")
        save_callback(file, out, self.save_callback, item, finishCallback)
        self.separating = False
        return

## [![Icon](./icon/icon_32x32.png)](.) Demucs GUI
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/CarlGao4/Demucs-GUI?include_prereleases&style=plastic)](https://github.com/CarlGao4/Demucs-Gui/releases) [![GitHub all releases](https://img.shields.io/github/downloads/CarlGao4/Demucs-GUI/total?style=plastic)](https://github.com/CarlGao4/Demucs-Gui/releases) [![GitHub](https://img.shields.io/github/license/carlgao4/demucs-gui?style=plastic)](LICENSE) [![platform](https://img.shields.io/badge/platform-Windows--64bit-blue?style=plastic)](https://github.com/CarlGao4/Demucs-Gui/releases) [![platform](https://img.shields.io/badge/platform-macOS--64bit%20%7C%20ARM64-yellow?style=plastic)](https://github.com/CarlGao4/Demucs-Gui/releases)

This is a GUI for python project `demucs`.

The project aims to let users without any coding experience separate tracks without difficulty. If you have any question about usage or the project, please open an issue to tell us. Since the original project [Demucs](https://github.com/facebookresearch/demucs) used scientific library `torch`, the packed binaries with environment is very large, and we will only pack binaries for formal releases.

<details id="CannotOpen">
  <summary>Note for macOS users</summary>

If the application cannot be launched due to the Mac's security protection feature, try the following:

1. Right-click on the Demucs-GUI app icon and select "Open".
2. Click "Open" again in the window that appears as follows.
![Open Anyway](./mac_open_anyway.png)

</details>

## System requirements
### Installing binaries
#### System version
For Windows: At least Windows 8

For Mac: At least macOS 10.15

For Linux: Any system that can install and run python 3.11 (Because I'll pack the binaries using python 3.11)

#### Hardware
Memory: About at least 8GB of total memory (physical and swap) would be required. The longer the track you want to separate, the more memory will be required.

GPU: Only NVIDIA GPUs (whose compute capability should be at least 3.5) and Apple MPS are supported. At least 2GB of private memory is required.

### Running the codes yourself
At least Python 3.9 is required. Other requirements please refer to [Installing binaries](#installing-binaries).

## Downloads
Binaries for download are available [here](https://github.com/CarlGao4/Demucs-Gui/releases).

## Update History

Please refer to [history.md](history.md).


## Usage
**If you are using released binaries, please refer to [usage.md](usage.md)**

*This part is written for beta versions*

<details>
  <summary>For macOS ARM64 users: There is a bug related to Qt causing crash. To avoid it, please run Python x86_64 using Rosetta 2.</summary>

According to [Apple Developer Forums](https://developer.apple.com/forums/thread/729355), the crash is caused by manipulating the GUI from a thread other than the main thread. This is exactly what Demucs GUI does: the separation process is time-consuming, so it is run in a separate thread to avoid causing the main window to stop responding. This thread will manipulate the GUI to update the progress bar and retrieve separation parameters from time to time.

But it's strange that the crash only happens on Apple Silicon Macs. Besides, Demucs GUI manipulates the GUI from a separate thread more than once, but the crash only happens when loading a model if you've chosen another model (as long as you've opened the drop-down menu for choosing models even if you didn't choose another model). So the solution is to run Python x86_64 using Rosetta 2, or wait for the bug to be fixed.

</details>

### CPU only or Apple MPS
1. Install Python (and git if you'd like to clone this repository) to your system.
2. Download zip of this branch and extract it to a folder, or clone this repository and switch to this branch.
3. Run `pip`, `conda` or other package managers to install all packages in [requirements.txt](requirements.txt).
```bash
# For pip
pip install -r requirements.txt
# For conda
conda install --yes --file requirements.txt
```
4. Run [`GuiMain.py`](GUI/GuiMain.py) and separate your song!

### CUDA acceleration
1. Install Python (and git if you'd like to clone this repository) to your system.
2. Download zip of this branch and extract it to a folder, or clone this repository and switch to this branch.
3. Install torch with cuda under intructions on [pyTorch official website](https://pytorch.org/get-started/locally/#start-locally). There is no requirement of cuda version, but the version of torch should be at least 2.0.0.
4. Run `pip`, `conda` or other package managers to install all packages in [requirements_cuda.txt](requirements_cuda.txt).
```bash
# For pip
pip install -r requirements_cuda.txt
# Conda is not available as this project has dependencies only on PyPI
```
5. Run [`GuiMain.py`](GUI/GuiMain.py) and separate your song! If your GPU is not listed in the `device` column, or is labeled "not recommended", this means your GPU is not available or the VRAM is not enough. Please use CPU instead or open an issue to tell us if you think this is a problem.

## Acknowledgements
This project includes code of [Demucs](https://github.com/facebookresearch/demucs) under MIT license.

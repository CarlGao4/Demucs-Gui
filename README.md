## [![Icon](./icon/icon_32x32.png)](.) Demucs GUI
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/CarlGao4/Demucs-GUI?include_prereleases&style=plastic)](https://github.com/CarlGao4/Demucs-Gui/releases) [![GitHub all releases](https://img.shields.io/github/downloads/CarlGao4/Demucs-GUI/total?style=plastic)](https://github.com/CarlGao4/Demucs-Gui/releases) [![GitHub](https://img.shields.io/github/license/carlgao4/demucs-gui?style=plastic)](LICENSE) [![platform](https://img.shields.io/badge/platform-win--64%20%7C%20osx--64-green?style=plastic)](https://github.com/CarlGao4/Demucs-Gui/releases)

**This is the latest develop branch of Demucs-GUI. Current status is reading and separating audios, without writing support. I'll develop this part when I'm free.**

This is a GUI for python project `demucs`.

The project aims to let users without any coding experience separate tracks without difficulty. If you have any question about usage or the project, please open an issue to tell us. Since the original project [Demucs](https://github.com/facebookresearch/demucs) used scientific library `torch`, the packed binaries with environment is very large, and we will only pack binaries for formal releases. 

<details id="CannotOpen">
  <summary>Note for macOS users</summary>

> Because of the limitation of Apple, Demucs-GUI need some extra configuration to work properly. 
> 
> First, we should allow running apps from all of sources. Execute following command in your Terminal (if you do not know where your Terminal.app is, please search your dashboard): 
> 
> ```bash
> sudo spctl --master-disable
> ```
> You may need to input your password. 
> 
> Then, we need to bypass the notarization (replace the path below to where your Demucs-GUI.app is if you did not install to the default location): 
> 
> ```bash
> sudo xattr -rd com.apple.quarantine /Applications/Demucs-GUI.app
> ```

</details>

## System requirements
### Installing binaries
#### System version
For Windows: At least Windows 8

For Mac: At least macOS 10.15

For Linux: We currently have no intention to pack binaries for linux. 

#### Hardware
Memory: At least 6GB memory, but 8GB swap may be required. The longer the track you want to separate, the more memory will be required. 

GPU: Only NVIDIA GPUs are supported. At least 3GB of **private memory** (not shared memory) is required. 

### Running the codes yourself
At least Python 3.9 is required. Other requirements please refer to [Installing binaries](#installing-binaries). 

## Downloads
Binaries for download are available [here](https://github.com/CarlGao4/Demucs-Gui/releases). 

## Update History
(For more please see [history.md](history.md))
Versions in *italic* means that this is a beta version, which does not provide packed binaries. 
- [*0.1a1 (Mar.31, 2022)* Initial release](history.md#01a1)
- [*0.1a2 (May.10, 2022)*](history.md#01a2)
- [0.1 (Jun.22, 2022)](history.md#01) [:link: Downloads](https://github.com/CarlGao4/Demucs-Gui/releases/tag/0.1)

## Usage
**If you are using released binaries, please skip this part**

*This part is written for beta versions*

### CPU only
1. Run `pip`, `conda` or other package managers to install all packages in [requirements.txt](requirements.txt). If you are using 0.1a1, please manually add `psutil>=5.7.0` into `requirements.txt`, please add it manually before installing dependencies, because I forgot to add it. 
```bash
# For pip
pip install -r requirements.txt
# For conda
conda install --yes --file requirements.txt
```
2. Download [pretrained](https://app.box.com/s/rd6h9dilocrrfbsh8u4izgbpnq4w9dnj) models and extract it to `pretrained` folder under `GUI` folder.  
3. Run [`GuiMain.py`](GUI/GuiMain.py) and separate your song! 

### CUDA acceleration
1. Install torch with cuda under intructions on [pyTorch official website](https://pytorch.org/get-started/locally/#start-locally)
2. Run `pip`, `conda` or other package managers to install all packages in [requirements_cuda.txt](requirements_cuda.txt). If you are using 0.1a1, please manually add `psutil>=5.7.0` into `requirements_cuda.txt`, please add it manually before installing dependencies, because I forgot to add it. 
```bash
# For pip
pip install -r requirements_cuda.txt
# For conda
conda install --yes --file requirements_cuda.txt
```
3. Download [pretrained](https://app.box.com/s/rd6h9dilocrrfbsh8u4izgbpnq4w9dnj) models and extract it to `pretrained` folder under `GUI` folder.  
4. Run [`GuiMain.py`](GUI/GuiMain.py) and separate your song! If your GPU is not listed in the `device` column, or is labeled "not recommended", this means your GPU is not available or the VRAM is not enough. Please use CPU instead or open an issue to tell us if you think this is a problem. 

### Other steps for Linux users
`soundfile` uses `libsndfile` but the wheels for Linux does not include it. Please use your package manager to install it manually.  

## Acknowledgements
This project includes code of [Demucs](https://github.com/facebookresearch/demucs) under MIT license. 

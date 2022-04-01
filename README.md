## Demucs GUI
This is a GUI for python project `demucs` with optimized memory usage in CUDA. 
The project aims to let users without any coding experience separate tracks without difficulty. If you have any question about usage or the project, please open an issue to tell us. Since the original project [Demucs](https://github.com/facebookresearch/demucs) used scientific library `torch`, the packed binaries with environment is very large, and we will only pack binaries for formal releases. 

## System requirements
### Installing binaries
#### System version
For Windows: At least Windows 8

For Mac: At least macOS 10.13

For Linux: We currently have no intention to pack binaries for linux. 

#### Hardware
Memory: At least 6GB memory, but 8GB swap may be required. The longer the track you want to separate, the more memory will be required. 
GPU: Only NVIDIA GPUs are available. At least 3GB of **private memory** (not shared memory) is required. 

### Running the codes yourself
At least Python 3.9 is required. Other requirements please refer to [Installing binaries](#installing-binaries). 

## Update History
(For more please see [history.md](history.md))
Versions in *italic* means that this is a beta version, which does not provide packed binaries. 
- [*0.1a1 (Mar.31, 2022)* Initial release](history.md#01a1)

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
pip install -r requirements.txt
# For conda
conda install --yes --file requirements.txt
```
3. Download [pretrained](https://app.box.com/s/rd6h9dilocrrfbsh8u4izgbpnq4w9dnj) models and extract it to `pretrained` folder under `GUI` folder.  
4. Run [`GuiMain.py`](GUI/GuiMain.py) and separate your song! If your GPU is not listed in the `device` column, or is labeled "not recommended", this means your GPU is not available or the VRAM is not enough. Please use CPU instead or open an issue to tell us if you think this is a problem. 

## Acknowledgements
This project includes code of [Demucs](https://github.com/facebookresearch/demucs) under MIT license. 

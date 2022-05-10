Note: Versions in *italic* means that the release is a beta version. 

### *0.1a2*
Release date: May. 10, 2022

#### Updates
1. Added logging so it will be friendlier to debugging
2. Removed requirement for pynvml and torchaudio
3. Thanks @hanton2222 , so logging for macOS could be initialized (#8)

#### Known issues
1. Since the problem of shifts (#6), shifts is temporarily removed
2. FFMpeg is still not available

### *0.1a1*
Release date: Mar. 31, 2022

#### Features
1. Graphic User Interface available
2. Updates system usage info every 0.2 second
3. Reads your hardware information and gives choices
4. Redeces least VRAM requirement to 3GiB
5. Provides recommended value for `split` based on your hardware

#### Known issues
1. Though the welcome page tells whether FFMpeg is installed, FFMpeg would not be used. 

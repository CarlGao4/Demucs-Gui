Note: Versions in *italic* means that the release is a beta version.

### 1.3.2
Release date: Reb. 20, 2025

#### Updates
1. Show update information when checking update

### 1.3.1
Release date: Feb. 12, 2025

#### Fixes
1. Fixed FFMpeg preset saving issue

### 1.3.0.1
Release date: Jan. 13, 2025

#### Updates
1. Added support for Intel Extension for PyTorch `2.1.40+xpu` built with oneAPI 2025.0.1

#### Fixes
1. Fixed an issue that on Linux log file can't be opened using the system file manager

### 1.3
Release date: Jan. 4, 2025

#### Updates
1. Added new default mixer output: `all_left`. This will output sounds do not exist in all stems.

#### Fixes
1. Will replace unsupported characters when decoding UTF-8 encoded strings to solve UnicodeDecodeError
2. Errors encountered when starting the application could be shown using a message box and the splash screen could be closed

### *1.3b1*
Release date: Nov. 3, 2024

#### Updates
1. Added new audio tag variables for output file name and ffmpeg command
2. Added clip mode "tanh"

#### Fixes
1. Package issues (which means that no code changes)
   1. Fixed an issue that models can't be loaded on macOS due to incompatible numpy version
   2. Fixed an issue that the output audio of GPU version on Windows is full of NaNs due to PyTorch compilation issue
   3. Fixed an issue that the GPU version on Windows can't be started due to missing DLLs
2. Now file names retrieved from URL could be URL decoded

### *1.3a1*
Release date: Oct. 5, 2024

#### Updates
1. Allow adding URL(s) as input, which will uses FFMpeg to read the audio
2. Automatically fill in the clipboard if you've copied a URL
3. Will use SoXR VHQ resampler as default when using FFMpeg to read audio
4. Added `{host}` and `{0}`, `{1}`, ... to the output file name variables (refer to [usage](usage.md#save-file-location) for more details)
5. Allow enabling debug using environment variable
6. Added a simple debug console
7. Added support for Intel Extension for PyTorch `2.1.40+xpu`
8. Allow changing options and retry when failed to save output audio

#### Fixes
1. Will open AOT documentation on the main branch instead of develop branch
2. No longer relies on wmic to get GPU information as Windows 11 24H2 has removed it. Used PowerShell to call `Get-CimInstance` instead

#### Known issues
1. CPU usage will stuck at 100% when separating, even running on GPU

### 1.2
Release date: May. 18, 2024

#### Fixes
1. Fixed an issue that "copy video stream" can't deal with pure audio files with no video stream
2. Added diffq as a requirement so quantized models can be used
3. Fix segment length may greater than max available length which will cause an error
4. Will only warn the user once if output file name and FFMpeg command may illegal

### *1.2b2*
Release date: May. 13, 2024

#### Updates
1. Changed library versions so more NVIDIA GPUs are supported

#### Fixes
1. Latest Qt 6.7.0 has added `windows11` window style, which is not stable yet. Automatically switch to `windowsvista` style if `windows11` is default.
2. May fail to initialize on some Windows systems

### *1.2b1*
Release date: May. 10, 2024

#### Updates
1. Supports CUDA and Intel MKL at the same time
2. Supports Intel Extension for PyTorch `2.1.30+xpu`

#### Fixes
1. Can't write to the output file when using FFMpeg encoder
2. Default mixer preset may be edited
3. Applying mixer preset will cause error

### *1.2a1*
Release date: Apr. 8, 2024

#### Updates
1. FFMpeg encoder! Now you can use FFMpeg to encode output file

#### Fixes
1. PdhAddEnglishCounterW failed when starting

#### Known issues
1. Can't write to the output file when using FFMpeg encoder

### 1.1
Release date: Mar. 21, 2024

#### Fixes
1. Will always save the last output file name as default output path

#### Changes
1. Warn the user when adding more than 500 files to the queue
2. Warn the user if settings and preset not match when setting default preset
3. Allowing users reset history location

### *1.1b2*
Release date: Mar. 14, 2024 (Happy pi day! :pie:)

#### Fixes
1. Can't save file

#### Known issues
1. Last saved file path and names will become default when you restart the application

If you run the code under this tag, you still can't save files. You should switch to the commit which updated this version to change log (this file).

### *1.1b1*
Release date: Mar. 13, 2024

#### Updates
1. Add mixer presets and default preset
2. MKL AOT detection and suggestions
3. Save "save location"

#### Fixes
1. SSLError when downloading remote models on macOS

#### Known issues
1. Can't save file

### *1.1a2*
Release date: Jan. 1, 2024 (Happy New Year! :fireworks: :fireworks: :fireworks:)

#### Updates
1. Add mixer
2. Add an option to restart the application quickly
3. Support Intel GPU (MKL) accelerator
4. Add native macOS ARM64 build

#### Fixes
1. Fix an error displaying queue length after removing items

### *1.1a1*
Release date: Dec. 8, 2023

#### Updates
1. Use the new tabbed UI
2. Add new option: separate once added to the queue
3. Save settings history for separate-once-added, file format, save location and clip mode

#### Fixes
1. Will show download progress if a remote model is not downloaded
> In previous versions, Demucs-GUI will not change the default torch hub cache dir. However, from this version, all new models will be downloaded to `Demucs-GUI.config.dir/pretrained/checkpoints`, without copying the old ones there. So you need to copy it manually if you still need those models.
2. Fix auto check updates doesn't work
3. Fix model info can't be shown completely sometimes

### 1.0.2.1
Release date: Nov. 28, 2023

#### Fixes
1. Fix an issue about reading audio with FFMpeg

#### Known issues
1. May causes waiting for long time when loading a remote model for the first time

### 1.0.2
Release date: Nov. 28, 2023

#### Updates
1. Show submodels in bag of models before loading it

#### Fixes
1. Fix an issue about reading audio

#### Known issues
1. **[NEW]** **[ADDED]** Will get stuck when reading with FFMpeg
2. May causes waiting for long time when loading a remote model for the first time

### 1.0.1
Release date: Nov. 25, 2023

#### Updates
1. Automatically check updates

#### Fixes
1. Fix an issue that output is always rescaled to 99.9% when clip mode is set to "rescale"
2. Fix an issue that window will stop to function when opening log file on non-Windows
3. Fix an issue related with detecting FFMpeg on Windows
4. Optimize ETA algorithm

### Known issues
1. May causes waiting for long time when loading a remote model for the first time

### 1.0
Release date: Nov. 11, 2023

#### Updates
1. Read with FFMpeg (which allows separating more file formats, even extracting audio track from a video and separate it)
2. Save files with multithread to avoid waiting between tracks
3. Show ETA
4. Ask before quitting if separating else exits (Yes, this is a conditional expressions)
5. Logging more separating parameters
6. Allow changing window style using settings.json
7. Allow PyQt6 as backend (though packed binaries will not use it. You can use it by modifying shared.py)
8. Add demucs_unittest model
9. Add menu bar

#### Fixes
1. Use absolute path for font
2. Fixed init error of mps
3. Fix sometimes progress goes back
4. Force separation queue using Fusion style on macOS to show progress bar

### Known issues
1. May causes waiting for long time when loading a remote model for the first time
2. **[ADDED]** **[FIXED]** Could not use remote models due to a mistake packing the application on Windows
3. **[ADDED]** Can't start FFmpeg sometimes. If you see `FFMpeg is not available`, please restart the application.
4. **[ADDED]** Will always rescale to 99.9% when clip mode is set to "rescale"

### *1.0a1*
Release date: Oct. 6, 2023

#### Updates
1. Rewritten GUI with PySide6 (Qt)
2. Listing model support
3. Getting model details
4. Multi-channel support - separate each channel one by one and combine them back
5. Separation queue support - automatically separate each song one by one
6. Drag & Drop support - simply drag folders or files into the queue window and will be added to queue
7. Progress bar
8. More save options - flac/wav, clamp/rescale, int16/int24/float32

#### Known issues
1. Waiting for documentation! Everybody is welcome to contribute! (#23)
2. May causes waiting for long time when loading a remote model for the first time
3. No ffmpeg support though I've added ffmpeg detection
4. **[ADDED]** **[FIXED]** Packed binaries can't use remote models
5. **[ADDED]** macOS can’t start up due to relative path

### 0.1
Release date: Jun. 22, 2022

#### Updates
1. Solved mono audio reading issue
2. Now you can type in the numbers of splits and overlap.
3. Windows now can read ogg and mp3 files.
4. Increase log level

#### Known issues
1. FFMpeg is still not available
2. On macOS, reading of mp3 files is not available. We are waiting the 0.11.0 release of python-soundfile.

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

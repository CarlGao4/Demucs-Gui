Note: Versions in *italic* means that the release is a beta version.

### *1.1b2*
Release date: Mar. 14, 2024 (Happy pi day! :pie:)

#### Fixes
1. Can't save file

#### Known issues
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

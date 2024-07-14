# Debugging for Windows 64-bit

**If you are using Windows 64-bit and can't run the program, please read the following instructions.**

**If you are looking for the main page of this project, please [switch to the main branch](https://github.com/CarlGao4/Demucs-Gui).**

The program fails to run on Windows usually because of missing DLLs. I'll explain how to find and report them.

1. Download this branch as a zip file and extract it to a folder. To download the zip file, you can just [click here](https://github.com/CarlGao4/Demucs-Gui/archive/refs/heads/debug-win64.zip).

2. Open the `debugger` folder and drag the `Demucs-Gui.exe` file onto the `run.bat` file. This will open a command prompt window and run the program. Please **DO NOT** close the terminal window.

3. After the terminal window closes automatically, you will find a new file named `Demucs-Gui.log` in the same folder as the `Demucs-Gui.exe` file. Please open this file and copy its content to a new issue on this repository. I will help you find the missing DLLs.

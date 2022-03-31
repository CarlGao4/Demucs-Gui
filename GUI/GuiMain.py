LICENSE = """Demucs-GUI 0.1a1
Copyright (C) 2022  Carl Gao, Jize Guo, Rosario S.E.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>."""

__version__ = "0.1a1"

import time
st = time.time()
import tkinter
import tkinter.ttk
import tkinter.filedialog
import tkinter.messagebox
import PIL
import PIL.Image
import PIL.ImageTk
import traceback
import base64
import pickle
import lzma
import sys
import os
import pathlib
import _thread
import psutil
import platform
import subprocess
import re
import soundfile
from LoadingImgB85 import LoadingImgB85

homeDir = pathlib.Path(__file__).parent
os.chdir(homeDir)
proc = psutil.Process(os.getpid())
FFMpegAvailable = False
cudaID = 0
LastCudaID = 0
UseCPU = True
LastDevice = ''

LoadingImg = pickle.loads(lzma.decompress(base64.b85decode(LoadingImgB85)))

def HSize(size):
    s = size
    t = 0
    u = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    while s >= 1024:
        s /= 1024
        t += 1
        if t >= 5:
            break
    return str(round(s, 3)) + u[t]

def LoadModel():
    global model
    st = time.time()
    ME.config(state=tkinter.DISABLED)
    MB.config(state=tkinter.DISABLED)
    MP.config(state=tkinter.DISABLED)
    SetStatusText('Loading model...')
    if MPV.get() != '':
        if not os.path.exists(pathlib.Path(MPV.get())/(MV.get() + '.yaml')):
            tkinter.messagebox.showerror('Model load failed', 'No such model')
            ME.config(state=tkinter.NORMAL)
            MB.config(state=tkinter.NORMAL)
            MP.config(state=tkinter.NORMAL)
            SetStatusText('Failed to load model')
            return
    try:
        model = RWCore.GetModel(MV.get(), pathlib.Path(MPV.get()) if len(MPV.get()) else None, device="cpu")
    except:
        tkinter.messagebox.showerror('Model load failed', traceback.format_exc())
        ME.config(state=tkinter.NORMAL)
        MB.config(state=tkinter.NORMAL)
        MP.config(state=tkinter.NORMAL)
        SetStatusText('Failed to load model')
        return
    SetStatusText('Loading used %.3fs' % (time.time() - st))
    POE.set(0.25)
    PHE.set(0)
    DLF.grid(column=0, row=1, padx=(20, 0), pady=(10, 0))
    PLF.grid(column=1, row=0, padx=(10, 20), pady=(20, 0))
    FLF.grid(column=1, row=1, padx=(10, 20), pady=(10, 20))
    MH.config(state=tkinter.DISABLED)
    if LastDevice.startswith('CUDA'):
        DefaultSplit = None
        if isinstance(model, RWCore.BagOfModels):
            DefaultSplit = min(list(i.segment for i in model.models) + [(torch.cuda.get_device_properties(LastCudaID).total_memory // 1048576 - 1700) // 128])
            DefaultSplit = 6 if DefaultSplit < 6 else DefaultSplit
            PPE.set(DefaultSplit)
        else:
            DefaultSplit = min([model.segment, (torch.cuda.get_device_properties(LastCudaID).total_memory // 1048576 - 1700) // 128])
            DefaultSplit = 6 if DefaultSplit < 6 else DefaultSplit
            PPE.set(DefaultSplit)
    else:
        if isinstance(model, RWCore.BagOfModels):
            PPE.set(min(i.segment for i in model.models))
        else:
            PPE.set(model.segment)

def Start():
    if psutil.virtual_memory().total < 6000000000:
        LoadingW.attributes('-topmost', False)
        tkinter.messagebox.showwarning('Failed to initialize', 'You do not have enough memory to run this program. \nTotal:\t%s\nMinimum:\t6GB' % HSize(psutil.virtual_memory().total))
        raise SystemExit(1)
    global RWCore, torch
    import RWCore
    import torch
    global devices, cudaID, UseCPU
    devices = ["CPU - %s (%d MiB)" % (platform.processor(), psutil.virtual_memory().total // 1048576)]
    DV.set(devices[0])
    DM.config(values=devices)
    if torch.cuda.is_available():
        deviceMems = []
        for i in range(torch.cuda.device_count()):
            deviceMems.append(torch.cuda.get_device_properties(i).total_memory)
        for i in range(len(deviceMems)):
            devices.append("CUDA:%d - %s (%d MiB)%s" % (i, torch.cuda.get_device_name(i), deviceMems[i] // 1048576, ' (not recommended)' if deviceMems[i] < 3435973836 else ''))
        cudaID = deviceMems.index(max(deviceMems))
        DM.config(values=devices)
        if max(deviceMems) < 3435973836:
            DV.set(devices[0])
        else:
            DV.set(devices[cudaID+1])
            UseCPU = False
        LoadingT.config(text="CUDA is available")
        global pynvml
        import pynvml
        pynvml.nvmlInit()
        global handle
        handle = pynvml.nvmlDeviceGetHandleByIndex(cudaID)
    else:
        LoadingT.config(text="CUDA is not available")
    time.sleep(0.8)
    if (homeDir/'ffmpeg').exists():
        os.environ['PATH'] = str(homeDir/'ffmpeg') + ';' + os.environ['PATH']
    try:
        p = subprocess.Popen(['ffmpeg', '-version'], stdout=subprocess.PIPE)
    except:
        LoadingT.config(text="FFMpeg is not available")
    else:
        global FFMpegAvailable
        try:
            LoadingT.config(text="FFMpeg version %s is available" % re.findall('[0-9]{1,}\\.[0-9\\.]*', p.stdout.read().decode().split('\n')[0])[0])
            FFMpegAvailable = True
        except:
            LoadingT.config(text="FFMpeg is not available")
    time.sleep(0.8)
    RWCore.torchaudio.set_audio_backend("soundfile")
    LoadingW.destroy()
    SetStatusText('Started in %.3fs' % (time.time() - st - 1.6))
    w.deiconify()
    w.minsize(w.winfo_width() + 20, w.winfo_height() + 20)
    w.focus_force()
    w.after(0, UpdateUsage)

def ChooseSeparate():
    if sys.platform == 'win32':
        types = soundfile.available_formats()
        types = list((types[i], "*." + i) for i in types)
        types = [("All available types", " ".join(i[1] for i in types))] + types
    file = tkinter.filedialog.askopenfilename(title="Browse an audio", filetypes=types)
    if file is None:
        return
    _thread.start_new_thread(Separate, (pathlib.Path(file), ))
    
def Separate(File: pathlib.Path):
    PPE.config(state=tkinter.DISABLED)
    POE.config(state=tkinter.DISABLED)
    PHE.config(state=tkinter.DISABLED)
    DM.config(state=tkinter.DISABLED)
    BB.config(state=tkinter.DISABLED)
    try:
        RWCore.process(model, File, True, File.parent/(File.name+'_separated'), int(PPE.get()), float(POE.get()), model.samplerate, int(PHE.get()), LastDevice.lower(), SetStatusText)
    except:
        tkinter.messagebox.showerror('Failed to separate', 'If error is out of memory, please use smaller "split", or close programs require a lot of memory (like browser, games, photo&video editor), or use CPU instead\n\n' + traceback.format_exc())
    else:
        SetStatusText('Successly separated "%s"' % str(File))
    model.to('cpu')
    for _ in range(10):
        torch.cuda.empty_cache()
    PPE.config(state='readonly')
    POE.config(state='readonly')
    PHE.config(state='readonly')
    DM.config(state='readonly')
    BB.config(state=tkinter.NORMAL)

if __name__ == "__main__":
    w = tkinter.Tk()
    LoadingImgTk = PIL.ImageTk.PhotoImage(LoadingImg)
    w.title("Demucs GUI")
    w.resizable(0, 0)

    StatusBar = tkinter.Frame(w)
    StatusText = tkinter.Label(StatusBar)
    StatusText.pack(side=tkinter.LEFT, padx=(8, 0), anchor='sw', fill=tkinter.Y)
    def SetStatusText(text):
        StatusText.config(text=text)
    UsageInfo = tkinter.Label(StatusBar, font=('Courier New', 8))
    UsageInfo.pack(side=tkinter.RIGHT, fill=tkinter.Y)
    def UpdateUsage():
        global handle, cudaID, LastCudaID, LastDevice, UseCPU, model
        m = proc.memory_info()
        try:
            if sys.platform == 'win32':
                UsageInfo.config(text="MEM:%dMB SWAP:%dMB CPU:%d%%\nALLMEM:%dMB GPUMEM:%dMB GPU%d:%d%%" % ((m.rss)//1048576, (m.vms-m.rss)//1048576, proc.cpu_percent(0)//psutil.cpu_count(True), psutil.virtual_memory().total//1048576, pynvml.nvmlDeviceGetMemoryInfo(handle).used//1048576, cudaID, pynvml.nvmlDeviceGetUtilizationRates(handle).gpu))
            else:
                UsageInfo.config(text="MEM:%dMB SWAP:%dMB CPU:%d%%\nALLMEM:%dMB GPUMEM:%dMB GPU%d:%d%%" % (m.rss//1048576, m.vms//1058476, proc.cpu_percent()//psutil.cpu_count(True), psutil.virtual_memory().total//1048576, pynvml.nvmlDeviceGetMemoryInfo(handle).used//1048576, cudaID, pynvml.nvmlDeviceGetUtilizationRates(handle).gpu))
        except:
            if sys.platform == 'win32':
                UsageInfo.config(text="MEM:%dMB SWAP:%dMB\nCPU:%d%% ALLMEM:%dMB" % ((m.rss)//1048576, (m.vms-m.rss)//1048576, proc.cpu_percent()//psutil.cpu_count(True), psutil.virtual_memory().total//1048576))
            else:
                UsageInfo.config(text="MEM:%dMB SWAP:%dMB CPU:%d%%\nALLMEM:%dMB" % (m.rss//1048576, m.vms//1058476, proc.cpu_percent()//psutil.cpu_count(True), psutil.virtual_memory().total//1048576))
        if LastDevice != DV.get().split(' - ')[0]:
            LastDevice = DV.get().split(' - ')[0]
            if LastDevice.startswith('CUDA'):
                LastCudaID = int(LastDevice[5:])
                UseCPU = False
                try:
                    DefaultSplit = None
                    if isinstance(model, RWCore.BagOfModels):
                        DefaultSplit = min(list(i.segment for i in model.models) + [(torch.cuda.get_device_properties(LastCudaID).total_memory // 1048576 - 1700) // 128])
                        DefaultSplit = 6 if DefaultSplit < 6 else DefaultSplit
                        PPE.set(DefaultSplit)
                    else:
                        DefaultSplit = min([model.segment, (torch.cuda.get_device_properties(LastCudaID).total_memory // 1048576 - 1700) // 128])
                        DefaultSplit = 6 if DefaultSplit < 6 else DefaultSplit
                        PPE.set(DefaultSplit)
                except:
                    pass
            else:
                UseCPU = True
                try:
                    if isinstance(model, RWCore.BagOfModels):
                        PPE.set(min(i.segment for i in model.models))
                    else:
                        PPE.set(model.segment)
                except:
                    pass
        if LastCudaID != cudaID:
            handle = pynvml.nvmlDeviceGetHandleByIndex(cudaID)
            LastCudaID = cudaID
        w.after(200, UpdateUsage)
    StatusBar.pack(side=tkinter.BOTTOM, fill=tkinter.X)

    Menu = tkinter.Menu(w, tearoff=False)
    InfoMenu = tkinter.Menu(Menu, tearoff=False)
    InfoMenu.add_command(label="About Demucs-GUI", command=lambda:tkinter.messagebox.showinfo('Demucs-GUI 0.1a1', LICENSE))
    Menu.add_cascade(label="Info", menu=InfoMenu)
    w.config(menu=Menu)

    MainFrame = tkinter.Frame()
    MainFrame.pack(side=tkinter.TOP, fill=tkinter.X)

    MLF = tkinter.ttk.Labelframe(MainFrame, text="Model")
    ML = tkinter.Label(MLF, text="Model name:")
    MPL = tkinter.Label(MLF, text="Model path:")
    MV = tkinter.StringVar(MLF, "mdx_extra_q")
    MPV = tkinter.StringVar(MLF, str(pathlib.Path(__file__).parent/'pretrained'))
    ME = tkinter.Entry(MLF, width=30, font=('Courier New', 12), textvariable=MV)
    MB = tkinter.ttk.Button(MLF, text="Load model", command=lambda:_thread.start_new_thread(LoadModel, ()))
    MH = tkinter.ttk.Button(MLF, text=chr(0xfffd), width=2, command=lambda:tkinter.messagebox.showinfo('Help of Model path', 'Please keep default if you don\'t know how this works\nKeep this empty if you want to use remote models'))
    MP = tkinter.Entry(MLF, width=80, font=('Courier New', 9), textvariable=MPV)
    ML.grid(row=0, column=0, padx=(10, 0), pady=(10, 0), sticky=tkinter.W)
    MPL.grid(row=1, column=0, padx=(10, 0), pady=(10, 0), sticky=tkinter.W)
    ME.grid(row=0, column=1, padx=(0, 0), pady=(10, 0), sticky=tkinter.W)
    MP.grid(row=1, column=1, padx=(0, 0), pady=(10, 0), sticky=tkinter.W)
    MH.grid(row=1, column=2, padx=(0, 10), pady=(10, 0), sticky=tkinter.W)
    MB.grid(row=2, column=0, columnspan=3, sticky=tkinter.N, pady=(10, 10))
    MLF.grid(row=0, column=0, padx=(20, 0), pady=(20, 0))

    DLF = tkinter.ttk.LabelFrame(MainFrame, text="Device")
    DL = tkinter.Label(DLF, text="Device:")
    DV = tkinter.StringVar(DLF)
    DM = tkinter.ttk.Combobox(DLF, state="readonly", width=80, textvariable=DV)
    DL.grid(row=0, column=0, padx=(20, 8), pady=(10, 20), sticky=tkinter.W)
    DM.grid(row=0, column=1, padx=(0, 20), pady=(10, 20), sticky=tkinter.W)

    PLF = tkinter.ttk.LabelFrame(MainFrame, text="Options")
    PPL = tkinter.Label(PLF, text="Split:")
    POL = tkinter.Label(PLF, text="Overlap:")
    PHL = tkinter.Label(PLF, text="Shifts:")
    PPE = tkinter.ttk.Spinbox(PLF, from_=6, to=3600, increment=1, width=5, state='readonly')
    POE = tkinter.ttk.Spinbox(PLF, from_=0, to=0.9, increment=0.01, width=5, state='readonly')
    PHE = tkinter.ttk.Spinbox(PLF, from_=0, to=20, increment=1, width=5, state='readonly')
    PPL.grid(column=0, row=0, padx=(20, 0), pady=(10, 0), sticky=tkinter.W)
    POL.grid(column=0, row=1, padx=(20, 0), pady=(10, 0), sticky=tkinter.W)
    PHL.grid(column=0, row=2, padx=(20, 0), pady=(10, 20), sticky=tkinter.W)
    PPE.grid(column=1, row=0, padx=(5, 20), pady=(10, 0), sticky=tkinter.W)
    POE.grid(column=1, row=1, padx=(5, 20), pady=(10, 0), sticky=tkinter.W)
    PHE.grid(column=1, row=2, padx=(5, 20), pady=(10, 20), sticky=tkinter.W)

    FLF = tkinter.ttk.LabelFrame(MainFrame, text="Separate")
    BB = tkinter.ttk.Button(FLF, text="Browse File to Separate", command=ChooseSeparate)
    BB.grid(column=0, row=0, padx=(20, 20), pady=(10, 20))

    w.withdraw()
    LoadingW = tkinter.Toplevel(w)
    if sys.platform != 'darwin':
        LoadingW.overrideredirect(True)
    LoadingW.protocol("WM_DELETE_WINDOW", None)
    LoadingW.resizable(False, False)
    LoadingL = tkinter.ttk.Label(LoadingW, border=0)
    LoadingL.config(image=LoadingImgTk)
    LoadingL.pack()
    LoadingT = tkinter.Label(LoadingW, text='Loading modules...', background='#000000', foreground='#cccccc', font=('Courier New', 14))
    LoadingT.place(x=5, y=550)
    LoadingW.attributes('-topmost', True)
    LoadingW.geometry('+'+str((w.winfo_screenwidth()-768)//2)+'+'+str((w.winfo_screenheight()-576)//2))

    LoadingW.after(0, lambda:_thread.start_new_thread(Start, ()))

    w.mainloop()
    try:
        pynvml.nvmlShutdown()
    except:
        pass
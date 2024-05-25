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

import sys

assert sys.platform == "win32"

import logging
import re

import shared

# These mappings are generated with ocloc.exe, I ran from 0x0000 to 0xFFFF and found all supported devices
PCI_Mappings = {
    "2.1.10": {
        "12.0.0": {"9A40", "9A49", "9A59", "9A60", "9A68", "9A70", "9A78", "FF20"},
        "12.1.0": {"4C80", "4C8A", "4C8B", "4C8C", "4C90", "4C9A"},
        "12.2.0": {
            "4680",
            "4682",
            "4688",
            "468A",
            "4690",
            "4692",
            "4693",
            "A780",
            "A781",
            "A782",
            "A783",
            "A788",
            "A789",
            "A78B",
        },
        "12.3.0": {
            "4626",
            "4628",
            "462A",
            "46A0",
            "46A1",
            "46A2",
            "46A3",
            "46A6",
            "46A8",
            "46AA",
            "46B0",
            "46B1",
            "46B2",
            "46B3",
            "46C0",
            "46C1",
            "46C2",
            "46C3",
            "A720",
            "A721",
            "A7A0",
            "A7A1",
            "A7A8",
            "A7A9",
        },
        "12.4.0": {"46D0", "46D1", "46D2"},
        "12.10.0": {"4905", "4906", "4907", "4908"},
        "12.55.8": {"4F80", "4F81", "4F82", "4F83", "4F84", "5690", "5691", "5692", "56A0", "56A1", "56A2", "56C0"},
        "12.56.5": {"4F87", "4F88", "5693", "5694", "5695", "56A5", "56A6", "56B0", "56B1", "56C1"},
        "12.57.0": {"4F85", "4F86", "5696", "5697", "56A3", "56A4", "56B2", "56B3"},
        "12.58.0": {"4F8C", "5698", "5699", "569A", "56A7", "56A8"},
        "12.59.0": {"4F89", "56A9", "56AA"},
    },
    "2.1.30": {
        "12.0.0": {"9A40", "9A49", "9A59", "9A60", "9A68", "9A70", "9A78", "FF20"},
        "12.1.0": {"4C80", "4C8A", "4C8B", "4C8C", "4C90", "4C9A"},
        "12.2.0": {
            "4680",
            "4682",
            "4688",
            "468A",
            "4690",
            "4692",
            "4693",
            "A780",
            "A781",
            "A782",
            "A783",
            "A788",
            "A789",
            "A78B",
        },
        "12.3.0": {
            "4626",
            "4628",
            "462A",
            "46A0",
            "46A1",
            "46A2",
            "46A3",
            "46A6",
            "46A8",
            "46AA",
            "46B0",
            "46B1",
            "46B2",
            "46B3",
            "46C0",
            "46C1",
            "46C2",
            "46C3",
            "A720",
            "A721",
            "A7A0",
            "A7A1",
            "A7A8",
            "A7A9",
        },
        "12.4.0": {"46D0", "46D1", "46D2"},
        "12.10.0": {"4905", "4906", "4907", "4908"},
        "12.55.8": {"4F80", "4F81", "4F82", "4F83", "4F84", "5690", "5691", "5692", "56A0", "56A1", "56A2", "56C0"},
        "12.56.5": {
            "4F87",
            "4F88",
            "5693",
            "5694",
            "5695",
            "56A5",
            "56A6",
            "56B0",
            "56B1",
            "56BA",
            "56BB",
            "56BC",
            "56BD",
            "56C1",
        },
        "12.57.0": {"4F85", "4F86", "5696", "5697", "56A3", "56A4", "56B2", "56B3"},
        "12.59.0": {"4F89", "56A9", "56AA"},
        "12.58.0": {"4F8C", "5698", "5699", "569A", "56A7", "56A8"},
        "12.70.4": {"7D40", "7D45", "7D60", "7D67"},
        "12.71.4": {"7D55", "7DD5"},
    },
}

AOT_link_fmt = "https://www.fosshub.com/Demucs-GUI-old.html?dwl={file}"
AOT_links = {
    "2.1.10": {
        "12.0.0": "12.0.0_tgl_tgllp.7z",
        "12.1.0": "12.1.0_rkl.7z",
        "12.2.0": "12.2.0_adl-s.7z",
        "12.3.0": "12.3.0_adl-p.7z",
        "12.4.0": "12.4.0_adl-n.7z",
        "12.10.0": "12.10.0_dg1.7z",
        "12.55.0": "12.55.0_dg2-g10-a0.7z",
        "12.55.1": "12.55.1_dg2-g10-a1.7z",
        "12.55.4": "12.55.4_dg2-g10-b0.7z",
        "12.55.8": "12.55.8_acm-g10_ats-m150_dg2-g10_dg2-g10-c0.7z",
        "12.56.0": "12.56.0_dg2-g11-a0.7z",
        "12.56.4": "12.56.4_dg2-g11-b0.7z",
        "12.56.5": "12.56.5_acm-g11_ats-m75_dg2-g11_dg2-g11-b1.7z",
        "12.57.0": "12.57.0_acm-g12_dg2-g12_dg2-g12-a0.7z",
        "12.58.0": "12.58.0_acm-g20_dg2-g20.7z",
        "12.59.0": "12.59.0_acm-g21_dg2-g21.7z",
    },
    "2.1.30": {
        "12.0.0": "12.0.0_2.1.30.7z",
        "12.1.0": "12.1.0_2.1.30.7z",
        "12.2.0": "12.2.0_2.1.30.7z",
        "12.3.0": "12.3.0_2.1.30.7z",
        "12.4.0": "12.4.0_2.1.30.7z",
        "12.10.0": "12.10.0_2.1.30.7z",
        "12.55.0": "12.55.0_2.1.30.7z",
        "12.55.1": "12.55.1_2.1.30.7z",
        "12.55.4": "12.55.4_2.1.30.7z",
        "12.55.8": "12.55.8_2.1.30.7z",
        "12.56.0": "12.56.0_2.1.30.7z",
        "12.56.4": "12.56.4_2.1.30.7z",
        "12.56.5": "12.56.5_2.1.30.7z",
        "12.57.0": "12.57.0_2.1.30.7z",
        "12.58.0": "12.58.0_2.1.30.7z",
        "12.59.0": "12.59.0_2.1.30.7z",
        "12.70.0": "12.70.0_2.1.30.7z",
        "12.70.4": "12.70.4_2.1.30.7z",
        "12.71.0": "12.71.0_2.1.30.7z",
        "12.71.4": "12.71.4_2.1.30.7z",
    },
}

gpus = []
has_Intel = False
p = shared.Popen(["wmic", "path", "win32_videocontroller", "get", "name,pnpdeviceid"])
parse_re = re.compile(
    r"(?P<name>.+?)\s+[Pp][Cc][Ii]\\[Vv][Ee][Nn]_(?P<vendor>[0-9A-Fa-f]{4})&[Dd][Ee][Vv]_(?P<device>[0-9A-Fa-f]{4})"
)
for line in p.communicate()[0].decode().splitlines():
    m = parse_re.match(line)
    if m is not None:
        gpus.append((m["name"], m["vendor"].upper(), m["device"].upper()))
        logging.info("Found GPU: %s (%s:%s)" % (m["name"], m["vendor"], m["device"]))
        if m["vendor"] == "8086":
            has_Intel = True


def is_intel_supported(vendor, device, ipex_version="2.1.10"):
    if vendor != "8086":
        return
    if ipex_version not in PCI_Mappings:
        return
    for k, v in PCI_Mappings[ipex_version].items():
        if device in v:
            return k
    # for v in Supported_But_Unknown:
    #     if device in v:
    #         return True
    return False


def get_download_link(version, ipex_version="2.1.10"):
    if ipex_version not in AOT_links:
        return None
    if version in AOT_links[ipex_version]:
        return AOT_link_fmt.format(file=AOT_links[ipex_version][version])
    return None


def ipex_version_available(ipex_version="2.1.10"):
    return ipex_version in PCI_Mappings and ipex_version in AOT_links


# I attach a copy of the first version of this list below

# These mappings come from the following websites:
# https://dgpu-docs.intel.com/devices/hardware-table.html
# https://pci-ids.ucw.cz/read/PC/8086
# https://en.wikipedia.org/wiki/List_of_Intel_graphics_processing_units
# https://github.com/GameTechDev/gpudetect/blob/master/IntelGfx.cfg
# IDs listed in the first map comes from official Intel documentation (first link above)
# IDs listed in the second map comes from other sources

# I made this list based on my understanding of the documentation, so it may not be accurate
# You may need to try to find the correct one if it runs really slow on your Intel GPU

# PCI_Mappings = {
#     "12.0.0": [{"9A78", "9AC0", "9AC9", "9AD9", "9AF8", "9A40", "9A49", "9A59", "9A60", "9A68", "9A70"}, {"9A7F"}],
#     "12.1.0": [{"4C8A", "4C8B", "4C90", "4C9A", "4C8C", "4C80"}, set()],
#     "12.2.0": [
#         {
#             "4680",
#             "4682",
#             "4688",
#             "468A",
#             "468B",
#             "4690",
#             "4692",
#             "4693",
#             "A78B",
#             "A78A",
#             "A789",
#             "A788",
#             "A783",
#             "A782",
#             "A781",
#             "A780",
#         },
#         set(),
#     ],
#     "12.3.0": [
#         {
#             "4626",
#             "4628",
#             "462A",
#             "46A0",
#             "46A1",
#             "46A2",
#             "46A3",
#             "46A6",
#             "46A8",
#             "46AA",
#             "46B0",
#             "46B1",
#             "46B2",
#             "46B3",
#             "46C0",
#             "46C1",
#             "46C2",
#             "46C3",
#             "A7A9",
#             "A7A8",
#             "A7A1",
#             "A7A0",
#             "A721",
#             "A720",
#         },
#         {"4636", "4638", "463A", "46B6", "46B8", "46BA", "A7AA", "A7AB", "A7AC", "A7AD"},
#     ],
#     "12.4.0": [{"46D0", "46D1", "46D2"}, set()],
#     "12.10.0": [{"4905", "4907"}, {"4906", "4908", "4909"}],
#     "12.55.0": [set(), set()],
#     "12.55.1": [set(), set()],
#     "12.55.4": [set(), set()],
#     "12.55.8": [set(), {"56A2", "56A1", "56A0", "5692", "5691", "5690"}],
#     "12.56.0": [set(), set()],
#     "12.56.4": [set(), set()],
#     "12.56.5": [set(), {"56A6", "56A5", "5694", "5693", "56B0", "56B1"}],
#     "12.57.0": [set(), {"5697", "5696", "56B3", "56B2"}],
#     "12.58.0": [set(), set()],
#     "12.59.0": [set(), set()],
# }

# Supported_But_Unknown = [
#     {
#         "4571",
#         "4557",
#         "4555",
#         "4551",
#         "4541",
#         "4E71",
#         "4E61",
#         "4E57",
#         "4E55",
#         "4E51",
#         "56B3",
#         "56B2",
#         "56A4",
#         "56A3",
#         "5697",
#         "5696",
#         "5695",
#         "56B1",
#         "56B0",
#         "56C1",
#         "56C0",
#     },
#     {"5698", "56A7", "56A8", "56A9"},
# ]

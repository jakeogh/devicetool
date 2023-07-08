#!/usr/bin/env python3
# -*- coding: utf8 -*-

# pylint: disable=missing-docstring               # [C0111] docstrings are always outdated and wrong
# pylint: disable=fixme                           # [W0511] todo is encouraged
# pylint: disable=line-too-long                   # [C0301]
# pylint: disable=too-many-instance-attributes    # [R0902]
# pylint: disable=too-many-lines                  # [C0302] too many lines in module
# pylint: disable=invalid-name                    # [C0103] single letter var names, name too descriptive
# pylint: disable=too-many-return-statements      # [R0911]
# pylint: disable=too-many-branches               # [R0912]
# pylint: disable=too-many-statements             # [R0915]
# pylint: disable=too-many-arguments              # [R0913]
# pylint: disable=too-many-nested-blocks          # [R1702]
# pylint: disable=too-many-locals                 # [R0914]
# pylint: disable=too-few-public-methods          # [R0903]
# pylint: disable=no-member                       # [E1101] no member for base
# pylint: disable=attribute-defined-outside-init  # [W0201]
# pylint: disable=too-many-boolean-expressions    # [R0916] in if statement
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Tuple

import sh
from asserttool import ic
from eprint import eprint
from mounttool import block_special_path_is_mounted
from pathtool import path_exists
from pathtool import path_is_block_special
from warntool import warn


def write_output(buf):
    sys.stderr.write(buf)


def block_devices():
    _devices = sh.lsblk("-d", "-n", "-p", "-o", "NAME").strip().split("\n")
    devices = set([Path(os.fsdecode(_)).resolve() for _ in _devices])
    return devices


def get_block_device_size(
    device: Path,
    verbose: bool | int | float = False,
):
    assert Path(device).is_block_device()
    fd = os.open(device, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)


def safety_check_devices(
    boot_device: Path,
    root_devices: Tuple[Path, ...],
    boot_device_partition_table: str,
    boot_filesystem: str,
    root_device_partition_table: str,
    root_filesystem: str,
    force: bool,
    disk_size: None | str,
    verbose: bool | int | float = False,
):
    if boot_device:
        assert device_is_not_a_partition(
            device=boot_device,
        )

    for device in root_devices:
        assert device_is_not_a_partition(
            device=device,
        )

    if boot_device:
        eprint(
            f"installing gentoo on boot device: {boot_device} {boot_device_partition_table} {boot_filesystem}"
        )
        assert path_is_block_special(boot_device)
        assert not block_special_path_is_mounted(
            boot_device,
        )

    if root_devices:
        eprint(
            "installing gentoo on root device(s):",
            root_devices,
            "(" + root_device_partition_table + ")",
            "(" + root_filesystem + ")",
        )
        for device in root_devices:
            assert path_is_block_special(device)
            assert not block_special_path_is_mounted(
                device,
            )

    for device in root_devices:
        eprint("boot_device:", boot_device)
        eprint("device:", device)
        eprint(
            "get_block_device_size(boot_device):",
            get_block_device_size(
                boot_device,
            ),
        )
        eprint(
            "get_block_device_size(device):     ",
            get_block_device_size(
                device,
            ),
        )
        assert get_block_device_size(
            boot_device,
        ) <= get_block_device_size(
            device,
        )

    if root_devices:
        first_root_device_size = get_block_device_size(
            root_devices[0],
        )

        for device in root_devices:
            assert (
                get_block_device_size(
                    device,
                )
                == first_root_device_size
            )

    if boot_device or root_devices:
        if not force:
            warn(
                (boot_device,),
                disk_size=disk_size,
            )
            warn(
                root_devices,
                disk_size=disk_size,
            )


def device_is_not_a_partition(
    *,
    device: Path,
    verbose: bool | int | float = False,
):
    device = Path(device)
    if not (device.name.startswith("nvme") or device.name.startswith("mmcblk")):
        assert not device.name[-1].isdigit()
    if device.name.startswith("nvme") or device.name.startswith("mmcblk"):
        assert device.name[-2] != "p"
    return True


def wait_for_block_special_device_to_exist(
    *,
    device: Path,
    timeout: int = 5,
):
    device = Path(device)
    eprint(f"waiting for block special device: {device.as_posix()} to exist")
    start = time.time()
    if path_exists(device):
        assert path_is_block_special(device)
        return True

    while not path_exists(device):
        time.sleep(0.1)
        if time.time() - start > timeout:
            raise TimeoutError(
                f"timeout waiting for block special device: {device} to exist"
            )
        if path_is_block_special(device):
            break
    return True


def add_partition_number_to_device(
    *,
    device: Path,
    partition_number: int,
    verbose: bool | int | float = False,
):
    device = Path(device)
    if device.name.startswith("nvme") or device.name.startswith("mmcblk"):
        devpath = device.as_posix() + "p" + str(partition_number)
    else:
        devpath = device.as_posix() + str(partition_number)
    return Path(devpath)


def get_partuuid_for_partition(
    partition: Path,
    verbose: bool | int | float = False,
):
    assert isinstance(partition, Path)
    blkid_command = sh.blkid(partition.as_posix())
    ic(blkid_command)

    _partuuid = blkid_command.split("PARTUUID=")[-1:][0].split('"')[1]
    ic(_partuuid)

    return _partuuid

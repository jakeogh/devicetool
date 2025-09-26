#!/usr/bin/env python3
# -*- coding: utf8 -*-

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Tuple

import sh
from asserttool import ic
from eprint import eprint
from mounttool import block_special_path_is_mounted
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
        assert path_is_block_special(boot_device, symlink_ok=True)
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
            assert path_is_block_special(device, symlink_ok=True)
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
                symlink_ok=True,
            )
            warn(
                root_devices,
                disk_size=disk_size,
                symlink_ok=True,
            )


def device_is_not_a_partition(
    *,
    device: Path,
):
    device = Path(device)
    if not (device.name.startswith("nvme") or device.name.startswith("mmcblk")):
        assert not device.name[-1].isdigit()
    if device.name.startswith("nvme") or device.name.startswith("mmcblk"):
        assert device.name[-2] != "p"
    return True


def add_partition_number_to_device(
    *,
    device: Path,
    partition_number: int,
):
    device = Path(device)
    if device.name.startswith("nvme") or device.name.startswith("mmcblk"):
        devpath = device.as_posix() + "p" + str(partition_number)
    else:
        devpath = device.as_posix() + str(partition_number)
    return Path(devpath)


def get_partuuid_for_partition(
    partition: Path,
):
    assert isinstance(partition, Path)
    blkid_command = sh.blkid(partition.as_posix())
    ic(blkid_command)

    _partuuid = blkid_command.split("PARTUUID=")[-1:][0].split('"')[1]
    ic(_partuuid)

    return _partuuid


def get_root_device() -> Path:
    _result = sh.grub_probe("--target=device", "/").strip()
    return Path(_result)

#!/usr/bin/env python3

import os
import sys
from pathlib import Path

import hs
from asserttool import ic
from eprint import eprint
from mounttool import block_special_path_is_mounted
from pathtool import path_is_block_special
from warntool import warn


def write_output(buf) -> None:
    sys.stderr.write(buf)


def block_devices() -> set[Path]:
    _devices = str(hs.Command("lsblk")("-d", "-n", "-p", "-o", "NAME")).strip().split("\n")
    return {Path(_).resolve() for _ in _devices}


def get_block_device_size(device: Path) -> int:
    assert Path(device).is_block_device()
    fd = os.open(device, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)


def safety_check_devices(
    boot_device: Path,
    root_devices: tuple[Path, ...],
    boot_device_partition_table: str,
    boot_filesystem: str,
    root_device_partition_table: str,
    root_filesystem: str,
    force: bool,
    disk_size: None | str,
    full_disk: bool = False,
) -> None:
    if boot_device:
        assert device_is_not_a_partition(device=boot_device)

    for device in root_devices:
        assert device_is_not_a_partition(device=device)

    if boot_device:
        eprint(
            f"installing gentoo on boot device: {boot_device} {boot_device_partition_table} {boot_filesystem}"
        )
        assert path_is_block_special(boot_device, symlink_ok=True)
        assert not block_special_path_is_mounted(boot_device)

    if root_devices:
        eprint(
            f"installing gentoo on root device(s): {root_devices} ({root_device_partition_table}) ({root_filesystem})"
        )
        for device in root_devices:
            assert path_is_block_special(device, symlink_ok=True)
            assert not block_special_path_is_mounted(device)

    if boot_device:
        boot_device_size = get_block_device_size(boot_device)
        for device in root_devices:
            device_size = get_block_device_size(device)
            eprint("boot_device:", boot_device, boot_device_size)
            eprint("device:     ", device, device_size)
            assert boot_device_size <= device_size

    if root_devices:
        first_root_device_size = get_block_device_size(root_devices[0])
        for device in root_devices:
            assert get_block_device_size(device) == first_root_device_size

    if boot_device or root_devices:
        if not force:
            warn(
                (boot_device,),
                disk_size=disk_size,
                full_disk=full_disk,
                symlink_ok=True,
            )
            warn(
                root_devices,
                disk_size=disk_size,
                full_disk=full_disk,
                symlink_ok=True,
            )


def device_is_not_a_partition(*, device: Path) -> bool:
    device = Path(device)
    if not (device.name.startswith("nvme") or device.name.startswith("mmcblk")):
        assert not device.name[-1].isdigit()
    else:
        assert device.name[-2] != "p"
    return True


def add_partition_number_to_device(*, device: Path, partition_number: int) -> Path:
    device = Path(device)
    if device.name.startswith("nvme") or device.name.startswith("mmcblk"):
        return Path(f"{device.as_posix()}p{partition_number}")
    return Path(f"{device.as_posix()}{partition_number}")


def get_partuuid_for_partition(partition: Path) -> str:
    assert isinstance(partition, Path)
    blkid_output = str(hs.Command("blkid")(partition.as_posix()))
    ic(blkid_output)
    _partuuid = blkid_output.split("PARTUUID=")[-1].split('"')[1]
    ic(_partuuid)
    return _partuuid


def get_root_device() -> Path:
    _result = str(hs.Command("grub-probe")("--target=device", "/")).strip()
    return Path(_result)

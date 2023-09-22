#!/usr/bin/env python3
# -*- coding: utf8 -*-

# pylint: disable=useless-suppression             # [I0021]
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
import time
from pathlib import Path

import click
import sh
from asserttool import ic
from click_auto_help import AHGroup
from clicktool import click_add_options
from clicktool import click_global_options
from clicktool import tv
from devicefilesystemtool import write as create_filesystem
from eprint import eprint
from globalverbose import gvd
from mounttool import block_special_path_is_mounted
from pathtool import path_is_block_special
from run_command import run_command
from timestamptool import get_timestamp
from warntool import warn

from devicetool import add_partition_number_to_device
from devicetool import device_is_not_a_partition
from devicetool import get_block_device_size
from devicetool import get_partuuid_for_partition
from devicetool import get_root_device
from devicetool import wait_for_block_special_device_to_exist
from devicetool import write_output


@click.group(no_args_is_help=True, cls=AHGroup)
@click_add_options(click_global_options)
@click.pass_context
def cli(
    ctx,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()


@cli.command()
@click.argument(
    "device", required=True, nargs=1, type=click.Path(exists=True, path_type=Path)
)
@click.option("--start", is_flag=False, required=True, type=int)
@click.option("--end", is_flag=False, required=True, type=int)
@click.option("--note", is_flag=False, type=str)
@click_add_options(click_global_options)
@click.pass_context
def backup_byte_range(
    ctx,
    *,
    device: Path,
    start: int,
    end: int,
    note: str,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()

    device = Path(device)
    with open(device, "rb") as dfh:
        bytes_to_read = end - start
        assert bytes_to_read > 0
        dfh.seek(start)
        bytes_read = dfh.read(bytes_to_read)
        assert len(bytes_read) == bytes_to_read

    time_stamp = str(get_timestamp())
    running_on_hostname = os.uname()[1]
    device_string = device.as_posix().replace("/", "_")
    backup_file_tail = (
        "_."
        + device_string
        + "."
        + time_stamp
        + "."
        + running_on_hostname
        + "_start_"
        + str(start)
        + "_end_"
        + str(end)
        + ".bak"
    )
    if note:
        backup_file = "_backup_" + note + backup_file_tail
    else:
        backup_file = "_backup__." + backup_file_tail
    with open(backup_file, "xb") as bfh:
        bfh.write(bytes_read)
    print(backup_file)


@cli.command()
@click.option(
    "--device",
    is_flag=False,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--backup-file", is_flag=False, required=True)
@click.option("--start", is_flag=False, type=int)
@click.option("--end", is_flag=False, type=int)
@click_add_options(click_global_options)
@click.pass_context
def compare_byte_range(
    ctx,
    *,
    device: Path,
    backup_file: str,
    start: int,
    end: int,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    device = Path(device)
    if not start:
        start = int(backup_file.split("start_")[1].split("_")[0])
    if not end:
        end = int(backup_file.split("end_")[1].split("_")[0].split(".")[0])
    assert isinstance(start, int)
    assert isinstance(end, int)
    # current_copy = backup_byte_range(device=device,
    #                                 start=start,
    #                                 end=end,
    #                                 note='current',
    #                                 )
    current_copy = ctx.invoke(
        backup_byte_range,
        device=device,
        start=start,
        end=end,
        note="current",
    )
    vbindiff_command = "vbindiff " + current_copy + " " + backup_file
    eprint(vbindiff_command)
    os.system(vbindiff_command)


# this function has been replaced with calls to devicelabeltool
# @cli.command()
# @click.option(
#    "--device",
#    is_flag=False,
#    required=True,
#    type=click.Path(exists=True, path_type=Path),
# )
# @click.option("--force", is_flag=True, required=False)
# @click.option("--no-wipe", is_flag=True, required=False)
# @click.option("--no-backup", is_flag=True, required=False)
# @click_add_options(click_global_options)
# @click.pass_context
# def write_gpt(
#    ctx,
#    *,
#    device: Path,
#    force: bool,
#    no_wipe: bool,
#    no_backup: bool,
#    verbose_inf: bool,
#    dict_output: bool,
#    verbose: bool = False,
# ):
#    tty, verbose = tv(
#        ctx=ctx,
#        verbose=verbose,
#        verbose_inf=verbose_inf,
#    )
#
#    if not verbose:
#        ic.disable()
#    else:
#        ic.enable()
#
#    if verbose_inf:
#        gvd.enable()
#    device = Path(device)
#    eprint("writing GPT to:", device)
#
#    assert device_is_not_a_partition(
#        device=device,
#    )
#
#    assert path_is_block_special(device)
#    assert not block_special_path_is_mounted(device)
#    if not force:
#        warn((device,))
#    if not no_wipe:
#        assert False  ## cant import below right now
#        # ctx.invoke(destroy_block_device_head_and_tail,
#        #           device=device,
#        #           force=force,
#        #           no_backup=no_backup,
#        #           )
#        ##run_command("sgdisk --zap-all " + boot_device)
#    else:
#        eprint("skipping wipe")
#
#    run_command(
#        "parted " + device.as_posix() + " --script -- mklabel gpt", verbose=True
#    )
#    # run_command("sgdisk --clear " + device) #alt way to greate gpt label


# this was replaced by devicelabeltool
@cli.command()
@click.option(
    "--device",
    is_flag=False,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--force", is_flag=True, required=False)
@click.option("--no-wipe", is_flag=True, required=False)
@click.option("--no-backup", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def write_mbr(
    ctx,
    *,
    device: Path,
    force: bool,
    no_wipe: bool,
    no_backup: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    device = Path(device)
    eprint("writing MBR to:", device)
    assert device_is_not_a_partition(
        device=device,
    )
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(
        device,
    )
    if not force:
        warn(
            (device,),
        )
    if not no_wipe:
        assert False  # fixme
        # ctx.invoke(destroy_block_device_head_and_tail,
        #           device=device,
        #           force=force,
        #           no_backup=no_backup,
        #           )
        ##run_command("sgdisk --zap-all " + boot_device)

    run_command(
        "parted " + device.as_posix() + " --script -- mklabel msdos",
        verbose=True,
    )
    # run_command("parted " + device + " --script -- mklabel gpt")
    # run_command("sgdisk --clear " + device) #alt way to greate gpt label


@cli.command()
@click.option(
    "--device",
    is_flag=False,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--start", is_flag=False, required=True, type=str)
@click.option("--end", is_flag=False, required=True, type=str)
@click.option("--partition-number", is_flag=False, required=True, type=int)
@click.option("--force", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def write_efi_partition(
    ctx,
    *,
    device: Path,
    start: int,
    end: int,
    partition_number: int,
    force: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    device = Path(device)
    ic("creating efi partition on:", device, partition_number, start, end)
    assert device_is_not_a_partition(
        device=device,
    )
    # assert not device.endswith('/')  # Path() fixed that
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(
        device,
    )
    assert int(partition_number)

    if not force:
        warn(
            (device,),
        )

    # output = run_command("parted " + device + " --align optimal --script -- mkpart primary " + start + ' ' + end)
    run_command(
        "parted --align minimal "
        + device.as_posix()
        + " --script -- mkpart primary "
        + str(start)
        + " "
        + str(end),
        verbose=True,
    )
    run_command(
        "parted "
        + device.as_posix()
        + " --script -- name "
        + str(partition_number)
        + " EFI",
        verbose=True,
    )
    run_command(
        "parted "
        + device.as_posix()
        + " --script -- set "
        + str(partition_number)
        + " boot on",
        verbose=True,
    )

    fat16_partition_device = add_partition_number_to_device(
        device=device,
        partition_number=partition_number,
    )
    wait_for_block_special_device_to_exist(device=fat16_partition_device)
    # while not path_is_block_special(fat16_partition_device):
    #    eprint("fat16_partition_device", fat16_partition_device, "is not block special yet, waiting a second.")
    #    time.sleep(1)

    ctx.invoke(
        create_filesystem, device=fat16_partition_device, filesystem="fat16", force=True
    )

    # 127488 /mnt/sdb2/EFI/BOOT/BOOTX64.EFI


@cli.command()
@click.option(
    "--device",
    is_flag=False,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--start", is_flag=False, required=True, type=str)
@click.option("--end", is_flag=False, required=True, type=str)
@click.option("--partition_number", is_flag=False, required=True, type=int)
@click.option("--force", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def write_grub_bios_partition(
    ctx,
    *,
    device: Path,
    start: int,
    end: int,
    force: int,
    partition_number: int,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    device = Path(device)
    ic("creating grub_bios partition on:", device, partition_number, start, end)
    assert device_is_not_a_partition(
        device=device,
    )
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(
        device,
    )
    assert int(partition_number)

    if not force:
        warn(
            (device,),
        )

    # run_command("parted " + device + " --align optimal --script -- mkpart primary " + str(start) + ' ' + str(end), verbose=True)
    run_command(
        "parted "
        + device.as_posix()
        + " --align minimal --script -- mkpart primary "
        + str(start)
        + " "
        + str(end),
        verbose=True,
    )
    run_command(
        "parted "
        + device.as_posix()
        + " --script -- name "
        + str(partition_number)
        + " BIOSGRUB",
        verbose=True,
    )
    run_command(
        "parted "
        + device.as_posix()
        + " --script -- set "
        + str(partition_number)
        + " bios_grub on",
        verbose=True,
    )
    grub_bios_partition_device = add_partition_number_to_device(
        device=device,
        partition_number=partition_number,
    )
    wait_for_block_special_device_to_exist(device=grub_bios_partition_device)


#    parted size prefixes
#    "s" (sectors)
#    "B" (bytes)
#    "kB"
#    "MB"
#    "MiB"
#    "GB"
#    "GiB"
#    "TB"
#    "TiB"
#    "%" (percentage of device size)
#    "cyl" (cylinders)

# sgdisk -a1 -n2:48:2047 -t2:EF02 -c2:"BIOS boot partition " + device # numbers in 512B sectors


# this was moved to devicefilesystemtool
# @cli.command()
# @click.argument(
#    "device", required=True, nargs=1, type=click.Path(exists=True, path_type=Path)
# )
# @click.option(
#    "--filesystem",
#    "filesystem",
#    is_flag=False,
#    required=True,
#    type=click.Choice(["fat16", "fat32", "ext4"]),
# )
# @click.option("--force", is_flag=True, required=False)
# @click.option("--raw-device", is_flag=True, required=False)
# @click_add_options(click_global_options)
# @click.pass_context
# def create_filesystem(
#    ctx,
#    *,
#    device: Path,
#    filesystem: str,
#    force: bool,
#    raw_device: bool,
#    verbose_inf: bool,
#    dict_output: bool,
#    verbose: bool = False,
# ):
#    tty, verbose = tv(
#        ctx=ctx,
#        verbose=verbose,
#        verbose_inf=verbose_inf,
#    )
#
#    if not verbose:
#        ic.disable()
#    else:
#        ic.enable()
#
#    if verbose_inf:
#        gvd.enable()
#    device = Path(device)
#    eprint("creating", filesystem, "filesystem on:", device)
#    if not raw_device:
#        assert device.as_posix()[-1].isdigit()
#    # oddly, this failed on '/dev/sda2', maybe the kernel was not done
#    # digesting the previous table change? (using fat16)
#
#    # this should be done by the caller
#    wait_for_block_special_device_to_exist(device=device)
#    assert path_is_block_special(device)
#    assert not block_special_path_is_mounted(
#        device,
#    )
#
#    if not force:
#        warn(
#            (device,),
#        )
#
#    if filesystem == "fat16":
#        run_command(
#            "mkfs.fat -F16 -s2 " + device.as_posix(),
#            verbose=True,
#        )
#    elif filesystem == "fat32":
#        run_command(
#            "mkfs.fat -F32 -s2 " + device.as_posix(),
#            verbose=True,
#        )
#    elif filesystem == "ext4":
#        run_command(
#            "mkfs.ext4 " + device.as_posix(),
#            verbose=True,
#        )
#    else:
#        assert False


@cli.command()
@click.argument("device", nargs=1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--force",
    is_flag=True,
)
@click.option(
    "--ask",
    is_flag=True,
)
@click_add_options(click_global_options)
@click.pass_context
def destroy_block_device(
    ctx,
    *,
    device: Path,
    force: bool,
    ask: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    device = Path(device)
    assert isinstance(force, bool)
    # assert source in ['urandom', 'zero']
    assert not device.name.endswith("/")
    assert device_is_not_a_partition(
        device=device,
    )
    assert device.as_posix().startswith("/dev/")
    ic("destroying device:", device)
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(
        device,
    )
    if not force:
        warn(
            (device,),
        )
    # device_name = device.split('/')[-1]
    assert len(device.name) >= 3
    assert "/" not in device.name
    assert device.as_posix().endswith(device.name)
    luks_mapper = Path("/dev/mapper") / Path(device.name)
    ic(luks_mapper)
    assert not path_is_block_special(luks_mapper, follow_symlinks=True)
    assert not luks_mapper.exists()

    # zero out any partition or existing LUKS header... otherwise cryptsetup throws warning and asks for comfirmation
    # the LUKS signature "SKUL" is at bytes 16384-16387
    ctx.invoke(
        destroy_block_device_head,
        device=device.as_posix(),
        source="zero",
        size=16387,
        verbose=True,
    )

    luks_command = (
        "cryptsetup open --type plain -d /dev/urandom "
        + device.as_posix()
        + " "
        + device.name
    )
    ic(luks_command)
    run_command(
        luks_command,
        expected_exit_status=0,
        ask=ask,
        verbose=True,
    )
    # sh.cryptsetup('open', '--type', 'plain', '-d', '/dev/urandom', device.as_posix(), device.name)

    assert path_is_block_special(luks_mapper, follow_symlinks=True)
    assert not block_special_path_is_mounted(
        luks_mapper,
    )
    sh.ls("-alh", luks_mapper)

    # sys-fs/dd-rescue
    # --abort_we: makes dd_rescue abort on any write errors
    # wipe_command = "dd_rescue --color=0 --abort_we /dev/zero " + luks_mapper.as_posix()
    # ic(wipe_command)
    # run_command(wipe_command, verbose=True, expected_exit_status=0, ask=ask,)
    sh.dd_rescue(
        "--verbose",
        "--color=1",
        "--abort_we",
        "/dev/zero",
        luks_mapper,
        _out=write_output,
        _err=write_output,
        _out_bufsize=1,
        _err_bufsize=1,
        _ok_code=[21],
    )

    time.sleep(1)  # so "cryptsetup close" doesnt throw an error

    close_command = "cryptsetup close " + device.name
    ic(close_command)
    run_command(
        close_command,
        expected_exit_status=0,
        ask=ask,
        verbose=True,
    )


@cli.command()
@click.argument("device", required=True, nargs=1, type=str)
@click.option("--size", is_flag=False, required=True, type=int)
@click.option(
    "--source", is_flag=False, required=True, type=click.Choice(["urandom", "zero"])
)
@click.option("--no-backup", is_flag=True, required=False)
@click.option("--note", is_flag=False, type=str)
@click.option("--ask", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def destroy_block_device_head(
    ctx,
    *,
    device: Path,
    size: int,
    source: str,
    ask: bool,
    no_backup: bool,
    note: str,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    device = Path(device)
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(
        device,
    )
    ic(device, size, source)
    ctx.invoke(
        destroy_byte_range,
        device=device,
        start=0,
        end=size,
        source=source,
        no_backup=no_backup,
        note=note,
    )


@cli.command()
@click.argument(
    "device", required=True, nargs=1, type=click.Path(exists=True, path_type=Path)
)
@click.option("--size", is_flag=False, required=True, type=int)
@click.option(
    "--source", is_flag=False, required=True, type=click.Choice(["urandom", "zero"])
)
@click.option("--ask", is_flag=True, required=False)
@click.option("--no-backup", is_flag=True, required=False)
@click.option("--note", is_flag=False, type=str)
@click_add_options(click_global_options)
@click.pass_context
def destroy_block_device_tail(
    ctx,
    *,
    device: Path,
    size: int,
    source,
    no_backup: bool,
    ask: bool,
    note: str,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    device = Path(device)
    assert size > 0
    device_size = get_block_device_size(
        device=device,
    )
    assert size <= device_size
    start = device_size - size
    assert start > 0
    end = start + size
    ctx.invoke(
        destroy_byte_range,
        device=device,
        start=start,
        end=end,
        ask=ask,
        source=source,
        no_backup=no_backup,
        note=note,
    )


@cli.command()
@click.argument(
    "device",
    required=True,
    nargs=1,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--start",
    is_flag=False,
    required=True,
    type=int,
)
@click.option(
    "--end",
    is_flag=False,
    required=True,
    type=int,
)
@click.option(
    "--source",
    is_flag=False,
    required=True,
    type=click.Choice(["urandom", "zero"]),
)
@click.option(
    "--ask",
    is_flag=True,
)
@click.option(
    "--no-backup",
    is_flag=True,
)
@click.option(
    "--note",
    is_flag=False,
    type=str,
)
@click_add_options(click_global_options)
@click.pass_context
def destroy_byte_range(
    ctx,
    *,
    device: Path,
    start: int,
    end: int,
    source: str,
    ask: bool,
    no_backup: bool,
    note: str,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    device = Path(device)
    assert start >= 0
    assert end > 0
    assert start < end
    eprint("source:", source)
    if not no_backup:
        ctx.invoke(
            backup_byte_range,
            device=device,
            start=start,
            end=end,
            note=note,
        )
    bytes_to_zero = end - start
    assert bytes_to_zero > 0
    with open(device, "wb") as dfh:
        dfh.seek(start)
        if source == "zero":
            dfh.write(bytearray(bytes_to_zero))
        if source == "urandom":
            urandom_bytes = os.urandom(bytes_to_zero)
            assert len(urandom_bytes) == bytes_to_zero
            dfh.write(urandom_bytes)


@cli.command()
@click.argument(
    "device", required=True, nargs=1, type=click.Path(exists=True, path_type=Path)
)
@click.option("--size", is_flag=False, type=int, default=(2048))
@click.option(
    "--source", is_flag=False, required=True, type=click.Choice(["urandom", "zero"])
)
@click.option("--note", is_flag=False, type=str)
@click.option("--ask", is_flag=True, required=False)
@click.option("--force", is_flag=True, required=False)
@click.option("--no-backup", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def destroy_block_device_head_and_tail(
    ctx,
    *,
    device: Path,
    size: int,
    source: str,
    note: str,
    ask: bool,
    force: bool,
    no_backup: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    # run_command("sgdisk --zap-all " + device, verbose=True,) #alt method
    device = Path(device)
    # assert isinstance(device, str)
    assert device_is_not_a_partition(
        device=device,
    )
    eprint("destroying device:", device)
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(device)
    if not force:
        warn(
            (device,),
        )
    if not note:
        note = str(time.time()) + "_" + device.as_posix().replace("/", "_")
        eprint("note:", note)

    ctx.invoke(
        destroy_block_device_head,
        device=device,
        size=size,
        source=source,
        note=note,
        ask=ask,
        no_backup=no_backup,
    )
    ctx.invoke(
        destroy_block_device_tail,
        device=device,
        size=size,
        source=source,
        note=note,
        ask=ask,
        no_backup=no_backup,
    )


@cli.command()
@click.argument(
    "devices", required=True, nargs=-1, type=click.Path(exists=True, path_type=Path)
)
@click.option("--size", is_flag=False, type=int, default=(1024 * 1024 * 128))
@click.option("--note", is_flag=False, type=str)
@click.option("--force", is_flag=True, required=False)
@click.option("--ask", is_flag=True, required=False)
@click.option("--no-backup", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def destroy_block_devices_head_and_tail(
    ctx,
    *,
    devices: tuple[Path, ...],
    size: int,
    note: str,
    ask: bool,
    force: bool,
    no_backup: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    assert isinstance(devices, list) or isinstance(devices, tuple)
    for device in devices:
        device = Path(device)
        assert device_is_not_a_partition(
            device=device,
        )
        eprint("destroying device:", device)
        assert path_is_block_special(device)
        assert not block_special_path_is_mounted(
            device,
        )

    if not force:
        warn(
            devices,
        )

    for device in devices:
        ctx.invoke(
            destroy_block_device_head_and_tail,
            device=device,
            size=size,
            note=note,
            ask=ask,
            force=force,
            no_backup=no_backup,
        )


@cli.command("partuuid")
@click.argument(
    "partition", required=True, nargs=1, type=click.Path(exists=True, path_type=Path)
)
@click_add_options(click_global_options)
@click.pass_context
def partuuid(
    ctx,
    *,
    partition: Path,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()
    assert isinstance(partition, Path)
    _partuuid = get_partuuid_for_partition(
        partition=partition,
    )
    print(_partuuid)


@cli.command("get-root-device")
@click_add_options(click_global_options)
@click.pass_context
def _get_root_device(
    ctx,
    *,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    if not verbose:
        ic.disable()
    else:
        ic.enable()

    if verbose_inf:
        gvd.enable()

    result = get_root_device()
    print(result)

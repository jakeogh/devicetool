#!/usr/bin/env python3

import os
import sys
import time
from pathlib import Path

import click
import hs
from asserttool import ic
from click_auto_help import AHGroup
from clicktool import click_add_options
from clicktool import click_global_options
from clicktool import tvicgvd
from devicefilesystemtool import write as create_filesystem
from eprint import eprint
from globalverbose import gvd
from mounttool import block_special_path_is_mounted
from pathtool import path_is_block_special
from pathtool import wait_for_block_special_device_to_exist
from timestamptool import get_timestamp
from warntool import warn

from devicetool import add_partition_number_to_device
from devicetool import device_is_not_a_partition
from devicetool import get_block_device_size
from devicetool import get_partuuid_for_partition
from devicetool import get_root_device
from devicetool import write_output

_parted = hs.Command("parted")
_cryptsetup = hs.Command("cryptsetup")


def _ask(command) -> None:
    eprint("Press ENTER to execute command:")
    eprint(command)
    if input():
        sys.exit(1)


@click.group(no_args_is_help=True, cls=AHGroup)
@click_add_options(click_global_options)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
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
@click.option("--note", is_flag=False, type=str)
@click_add_options(click_global_options)
@click.pass_context
def backup_byte_range(
    ctx: click.Context,
    *,
    device: Path,
    start: int,
    end: int,
    note: str,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> str:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

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
        f"_.{device_string}.{time_stamp}.{running_on_hostname}"
        f"_start_{start}_end_{end}.bak"
    )
    if note:
        backup_file = f"_backup_{note}{backup_file_tail}"
    else:
        backup_file = f"_backup__.{backup_file_tail}"
    with open(backup_file, "xb") as bfh:
        bfh.write(bytes_read)
    print(backup_file)
    return backup_file


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
    ctx: click.Context,
    *,
    device: Path,
    backup_file: str,
    start: None | int,
    end: None | int,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    device = Path(device)
    if not start:
        start = int(backup_file.split("start_")[1].split("_")[0])
    if not end:
        end = int(backup_file.split("end_")[1].split("_")[0].split(".")[0])
    current_copy = ctx.invoke(
        backup_byte_range,
        device=device,
        start=start,
        end=end,
        note="current",
    )
    hs.Command("vbindiff")(current_copy, backup_file, _fg=True)


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
    ctx: click.Context,
    *,
    device: Path,
    force: bool,
    no_wipe: bool,
    no_backup: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    device = Path(device)
    eprint("writing MBR to:", device)
    assert device_is_not_a_partition(device=device)
    assert path_is_block_special(device, symlink_ok=True)
    assert not block_special_path_is_mounted(device)
    if not force:
        warn(
            (device,),
            symlink_ok=True,
        )
    if not no_wipe:
        raise NotImplementedError("wipe before mklabel")

    _parted(
        device.as_posix(),
        "--script",
        "--",
        "mklabel",
        "msdos",
        _out=sys.stdout,
        _err=sys.stderr,
    )


@cli.command()
@click.option(
    "--device",
    is_flag=False,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--start",
    is_flag=False,
    required=True,
    type=str,
)
@click.option(
    "--end",
    is_flag=False,
    required=True,
    type=str,
)
@click.option(
    "--partition-number",
    is_flag=False,
    required=True,
    type=int,
)
@click.option("--force", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def write_efi_partition(
    ctx: click.Context,
    *,
    device: Path,
    start: str,
    end: str,
    partition_number: int,
    force: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    device = Path(device)
    ic("creating efi partition on:", device, partition_number, start, end)
    assert device_is_not_a_partition(device=device)
    assert path_is_block_special(device, symlink_ok=True)
    assert not block_special_path_is_mounted(device)
    assert partition_number

    if not force:
        warn(
            (device,),
            symlink_ok=True,
        )

    _parted(
        "--align",
        "minimal",
        device.as_posix(),
        "--script",
        "--",
        "mkpart",
        "primary",
        start,
        end,
        _out=sys.stdout,
        _err=sys.stderr,
    )
    _parted(
        device.as_posix(),
        "--script",
        "--",
        "name",
        str(partition_number),
        "EFI",
        _out=sys.stdout,
        _err=sys.stderr,
    )
    _parted(
        device.as_posix(),
        "--script",
        "--",
        "set",
        str(partition_number),
        "boot",
        "on",
        _out=sys.stdout,
        _err=sys.stderr,
    )

    fat16_partition_device = add_partition_number_to_device(
        device=device,
        partition_number=partition_number,
    )
    wait_for_block_special_device_to_exist(device=fat16_partition_device)

    ctx.invoke(
        create_filesystem,
        device=fat16_partition_device,
        filesystem="fat16",
        force=True,
    )


@cli.command()
@click.option(
    "--device",
    is_flag=False,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--start",
    is_flag=False,
    required=True,
    type=str,
)
@click.option(
    "--end",
    is_flag=False,
    required=True,
    type=str,
)
@click.option(
    "--partition-number",
    is_flag=False,
    required=True,
    type=int,
)
@click.option("--force", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def write_grub_bios_partition(
    ctx: click.Context,
    *,
    device: Path,
    start: str,
    end: str,
    force: bool,
    partition_number: int,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    device = Path(device)
    ic("creating grub_bios partition on:", device, partition_number, start, end)
    assert device_is_not_a_partition(device=device)
    assert path_is_block_special(device, symlink_ok=True)
    assert not block_special_path_is_mounted(device)
    assert partition_number

    if not force:
        warn(
            (device,),
            symlink_ok=True,
        )

    _parted(
        device.as_posix(),
        "--align",
        "minimal",
        "--script",
        "--",
        "mkpart",
        "primary",
        start,
        end,
        _out=sys.stdout,
        _err=sys.stderr,
    )
    _parted(
        device.as_posix(),
        "--script",
        "--",
        "name",
        str(partition_number),
        "BIOSGRUB",
        _out=sys.stdout,
        _err=sys.stderr,
    )
    _parted(
        device.as_posix(),
        "--script",
        "--",
        "set",
        str(partition_number),
        "bios_grub",
        "on",
        _out=sys.stdout,
        _err=sys.stderr,
    )
    grub_bios_partition_device = add_partition_number_to_device(
        device=device,
        partition_number=partition_number,
    )
    wait_for_block_special_device_to_exist(device=grub_bios_partition_device)


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
    ctx: click.Context,
    *,
    device: Path,
    force: bool,
    ask: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    device = Path(device)
    assert not device.name.endswith("/")
    assert device_is_not_a_partition(device=device)
    assert device.as_posix().startswith("/dev/")
    ic("destroying device:", device)
    assert path_is_block_special(device, symlink_ok=True)
    assert not block_special_path_is_mounted(device)
    if not force:
        warn(
            (device,),
            symlink_ok=True,
        )
    assert len(device.name) >= 3
    assert "/" not in device.name
    assert device.as_posix().endswith(device.name)
    luks_mapper = Path("/dev/mapper") / device.name
    ic(luks_mapper)
    assert not path_is_block_special(luks_mapper, symlink_ok=True)
    assert not luks_mapper.exists()

    # zero any existing partition or LUKS header (signature at bytes 16384-16387)
    # otherwise cryptsetup warns and asks for confirmation
    ctx.invoke(
        destroy_block_device_head,
        device=device,
        source="zero",
        size=16387,
        verbose=True,
    )

    open_command = _cryptsetup.rebake(
        "open",
        "--type",
        "plain",
        "-d",
        "/dev/urandom",
        device.as_posix(),
        device.name,
    )
    ic(open_command)
    if ask:
        _ask(open_command)
    open_command()

    assert path_is_block_special(luks_mapper, symlink_ok=True)
    assert not block_special_path_is_mounted(luks_mapper)

    # sys-fs/dd-rescue; --abort_we: abort on any write error; exit 21: device full
    hs.Command("dd_rescue")(
        "--verbose",
        "--color=1",
        "--abort_we",
        "/dev/zero",
        luks_mapper.as_posix(),
        _out=write_output,
        _err=write_output,
        _out_bufsize=1,
        _err_bufsize=1,
        _ok_code=[21],
    )

    time.sleep(1)  # so "cryptsetup close" doesnt throw an error

    close_command = _cryptsetup.rebake("close", device.name)
    ic(close_command)
    if ask:
        _ask(close_command)
    close_command()


@cli.command()
@click.argument(
    "device",
    required=True,
    nargs=1,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--size",
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
@click.option("--no-backup", is_flag=True, required=False)
@click.option("--note", is_flag=False, type=str)
@click.option("--ask", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def destroy_block_device_head(
    ctx: click.Context,
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
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    device = Path(device)
    assert path_is_block_special(device, symlink_ok=True)
    assert not block_special_path_is_mounted(device)
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
    "device",
    required=True,
    nargs=1,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--size",
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
@click.option("--ask", is_flag=True, required=False)
@click.option("--no-backup", is_flag=True, required=False)
@click.option("--note", is_flag=False, type=str)
@click_add_options(click_global_options)
@click.pass_context
def destroy_block_device_tail(
    ctx: click.Context,
    *,
    device: Path,
    size: int,
    source: str,
    no_backup: bool,
    ask: bool,
    note: str,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    device = Path(device)
    assert size > 0
    device_size = get_block_device_size(device=device)
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
    ctx: click.Context,
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
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

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
        elif source == "urandom":
            urandom_bytes = os.urandom(bytes_to_zero)
            assert len(urandom_bytes) == bytes_to_zero
            dfh.write(urandom_bytes)
        else:
            raise ValueError(f"unknown source: {source}")


@cli.command()
@click.argument(
    "device",
    required=True,
    nargs=1,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--size",
    is_flag=False,
    type=int,
    default=2048,
)
@click.option(
    "--source",
    is_flag=False,
    required=True,
    type=click.Choice(["urandom", "zero"]),
)
@click.option("--note", is_flag=False, type=str)
@click.option("--ask", is_flag=True, required=False)
@click.option("--force", is_flag=True, required=False)
@click.option("--no-backup", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def destroy_block_device_head_and_tail(
    ctx: click.Context,
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
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    device = Path(device)
    assert device_is_not_a_partition(device=device)
    eprint("destroying device:", device)
    assert path_is_block_special(device, symlink_ok=True)
    assert not block_special_path_is_mounted(device)
    if not force:
        warn(
            (device,),
            symlink_ok=True,
        )
    if not note:
        note = f"{time.time()}_{device.as_posix().replace('/', '_')}"
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
    "devices",
    required=True,
    nargs=-1,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--size",
    is_flag=False,
    type=int,
    default=1024 * 1024 * 128,
)
@click.option("--note", is_flag=False, type=str)
@click.option("--force", is_flag=True, required=False)
@click.option("--ask", is_flag=True, required=False)
@click.option("--no-backup", is_flag=True, required=False)
@click_add_options(click_global_options)
@click.pass_context
def destroy_block_devices_head_and_tail(
    ctx: click.Context,
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
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    assert isinstance(devices, tuple)
    for device in devices:
        device = Path(device)
        assert device_is_not_a_partition(device=device)
        eprint("destroying device:", device)
        assert path_is_block_special(device, symlink_ok=True)
        assert not block_special_path_is_mounted(device)

    if not force:
        warn(
            devices,
            symlink_ok=True,
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
    "partition",
    required=True,
    nargs=1,
    type=click.Path(exists=True, path_type=Path),
)
@click_add_options(click_global_options)
@click.pass_context
def partuuid(
    ctx: click.Context,
    *,
    partition: Path,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    print(get_partuuid_for_partition(partition=partition))


@cli.command("get-root-device")
@click_add_options(click_global_options)
@click.pass_context
def _get_root_device(
    ctx: click.Context,
    *,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    print(get_root_device())

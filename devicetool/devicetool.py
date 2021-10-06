#!/usr/bin/env python3
# -*- coding: utf8 -*-

# pylint: disable=C0111  # docstrings are always outdated and wrong
# pylint: disable=W0511  # todo is encouraged
# pylint: disable=C0301  # line too long
# pylint: disable=R0902  # too many instance attributes
# pylint: disable=C0302  # too many lines in module
# pylint: disable=C0103  # single letter var names, func name too descriptive
# pylint: disable=R0911  # too many return statements
# pylint: disable=R0912  # too many branches
# pylint: disable=R0915  # too many statements
# pylint: disable=R0913  # too many arguments
# pylint: disable=R1702  # too many nested blocks
# pylint: disable=R0914  # too many local variables
# pylint: disable=R0903  # too few public methods
# pylint: disable=E1101  # no member for base
# pylint: disable=W0201  # attribute defined outside __init__
# pylint: disable=R0916  # Too many boolean expressions in if statement


import os
import sys
import time
from pathlib import Path
from typing import ByteString
from typing import Generator
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

import click
import sh
from asserttool import eprint
from asserttool import ic
from mounttool import block_special_path_is_mounted
from pathtool import path_exists
from pathtool import path_is_block_special
from run_command import run_command
from timetool import get_timestamp
from warntool import warn


def write_output(buf):
    sys.stderr.write(buf)


def get_block_device_size(device: Path,
                          verbose: bool,
                          debug: bool,
                          ):
    assert Path(device).is_block_device()
    fd = os.open(device, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)


def safety_check_devices(boot_device: Path,
                         root_devices: Tuple[Path, ...],
                         verbose: bool,
                         debug: bool,
                         boot_device_partition_table: str,
                         boot_filesystem: str,
                         root_device_partition_table: str,
                         root_filesystem: str,
                         force: bool,
                         ):
    if boot_device:
        assert device_is_not_a_partition(device=boot_device,
                                         verbose=verbose,
                                         debug=debug,)

    for device in root_devices:
        assert device_is_not_a_partition(device=device,
                                         verbose=verbose,
                                         debug=debug,)

    if boot_device:
        eprint("installing gentoo on boot device: {boot_device} {boot_device_partition_table} {boot_filesystem}".format(boot_device=boot_device, boot_device_partition_table=boot_device_partition_table, boot_filesystem=boot_filesystem))
        assert path_is_block_special(boot_device)
        assert not block_special_path_is_mounted(boot_device, verbose=verbose, debug=debug,)

    if root_devices:
        eprint("installing gentoo on root device(s):", root_devices, '(' + root_device_partition_table + ')', '(' + root_filesystem + ')')
        for device in root_devices:
            assert path_is_block_special(device)
            assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)

    for device in root_devices:
        eprint("boot_device:", boot_device)
        eprint("device:", device)
        eprint("get_block_device_size(boot_device):", get_block_device_size(boot_device, verbose=verbose, debug=debug,))
        eprint("get_block_device_size(device):     ", get_block_device_size(device, verbose=verbose, debug=debug,))
        assert get_block_device_size(boot_device, verbose=verbose, debug=debug,) <= get_block_device_size(device, verbose=verbose, debug=debug,)

    if root_devices:
        first_root_device_size = get_block_device_size(root_devices[0], verbose=verbose, debug=debug,)

        for device in root_devices:
            assert get_block_device_size(device, verbose=verbose, debug=debug,) == first_root_device_size

    if boot_device or root_devices:
        if not force:
            warn((boot_device,), verbose=verbose, debug=debug,)
            warn(root_devices, verbose=verbose, debug=debug,)


def device_is_not_a_partition(*,
                              device: Path,
                              verbose: bool,
                              debug: bool,
                              ):
    device = Path(device)
    if not (device.name.startswith('nvme') or device.name.startswith('mmcblk')):
        assert not device.name[-1].isdigit()
    if (device.name.startswith('nvme') or device.name.startswith('mmcblk')):
        assert device.name[-2] != 'p'
    return True


def wait_for_block_special_device_to_exist(*,
                                           device: Path,
                                           timeout: int = 5,
                                           ):
    device = Path(device)
    eprint("waiting for block special device: {} to exist".format(device.as_posix()))
    start = time.time()
    if path_exists(device):
        assert path_is_block_special(device)
        return True

    while not path_exists(device):
        time.sleep(0.1)
        if time.time() - start > timeout:
            raise TimeoutError("timeout waiting for block special device: {} to exist".format(device))
        if path_is_block_special(device):
            break
    return True


def add_partition_number_to_device(*,
                                   device: Path,
                                   partition_number: int,
                                   verbose: bool = False,
                                   debug: bool = False,
                                   ):
    device = Path(device)
    if device.name.startswith('nvme') or device.name.startswith('mmcblk'):
        devpath = device.as_posix() + 'p' + partition_number
    else:
        devpath = device.as_posix() + partition_number
    return Path(devpath)


@click.group()
@click.option('--verbose', is_flag=True)
@click.option('--debug', is_flag=True)
@click.pass_context
def cli(ctx,
              verbose: bool,
              debug: bool,
              ):

    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug


@cli.command()
@click.argument('device', required=True, nargs=1)
@click.option('--start', is_flag=False, required=True, type=int)
@click.option('--end', is_flag=False, required=True, type=int)
@click.option('--note', is_flag=False, type=str)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
def backup_byte_range(*,
                      device: Path,
                      start: int,
                      end: int,
                      note: str,
                      verbose: bool,
                      debug: bool,
                      ):

    device = Path(device)
    with open(device, 'rb') as dfh:
        bytes_to_read = end - start
        assert bytes_to_read > 0
        dfh.seek(start)
        bytes_read = dfh.read(bytes_to_read)
        assert len(bytes_read) == bytes_to_read

    time_stamp = str(get_timestamp())
    running_on_hostname = os.uname()[1]
    device_string = device.as_posix().replace('/', '_')
    backup_file_tail = '_.' \
        + device_string + '.' \
        + time_stamp + '.' \
        + running_on_hostname \
        + '_start_' + str(start) + '_end_' + str(end) + '.bak'
    if note:
        backup_file = '_backup_' + note + backup_file_tail
    else:
        backup_file = '_backup__.' + backup_file_tail
    with open(backup_file, 'xb') as bfh:
        bfh.write(bytes_read)
    print(backup_file)


@cli.command()
@click.option('--device', is_flag=False, required=True)
@click.option('--backup-file', is_flag=False, required=True)
@click.option('--start', is_flag=False, type=int)
@click.option('--end', is_flag=False, type=int)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
def compare_byte_range(*,
                       device: Path,
                       backup_file: str,
                       start: int,
                       end: int,
                       verbose: bool,
                       debug: bool,
                       ):

    device = Path(device)
    if not start:
        start = int(backup_file.split('start_')[1].split('_')[0])
    if not end:
        end = int(backup_file.split('end_')[1].split('_')[0].split('.')[0])
    assert isinstance(start, int)
    assert isinstance(end, int)
    current_copy = backup_byte_range(device=device,
                                     start=start,
                                     end=end,
                                     note='current',
                                     verbose=verbose,
                                     debug=debug,)
    vbindiff_command = "vbindiff " + current_copy + ' ' + backup_file
    eprint(vbindiff_command)
    os.system(vbindiff_command)


@cli.command()
@click.option('--device', is_flag=False, required=True)
@click.option('--force', is_flag=True, required=False)
@click.option('--no-wipe', is_flag=True, required=False)
@click.option('--no-backup', is_flag=True, required=False)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
@click.pass_context
def write_gpt(ctx, *,
              device: Path,
              force: bool,
              no_wipe: bool,
              no_backup: bool,
              verbose: bool,
              debug: bool,
              ):

    device = Path(device)
    eprint("writing GPT to:", device)

    assert device_is_not_a_partition(device=device, verbose=verbose, debug=debug,)

    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)
    if not force:
        warn((device,), verbose=verbose, debug=debug,)
    if not no_wipe:
        assert False  ## cant import below right now
        #ctx.invoke(destroy_block_device_head_and_tail,
        #           device=device,
        #           force=force,
        #           no_backup=no_backup,
        #           verbose=verbose,
        #           debug=debug,)
        ##run_command("sgdisk --zap-all " + boot_device)
    else:
        eprint("skipping wipe")

    run_command("parted " + device.as_posix() + " --script -- mklabel gpt", verbose=True)
    #run_command("sgdisk --clear " + device) #alt way to greate gpt label


@cli.command()
@click.option('--device', is_flag=False, required=True)
@click.option('--force', is_flag=True, required=False)
@click.option('--no-wipe', is_flag=True, required=False)
@click.option('--no-backup', is_flag=True, required=False)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
@click.pass_context
def write_mbr(ctx, *,
              device: Path,
              force: bool,
              no_wipe: bool,
              no_backup: bool,
              verbose: bool,
              debug: bool,
              ):
    device = Path(device)
    eprint("writing MBR to:", device)
    assert device_is_not_a_partition(device=device, verbose=verbose, debug=debug,)
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)
    if not force:
        warn((device,), verbose=verbose, debug=debug,)
    if not no_wipe:
        assert False  # fixme
        #ctx.invoke(destroy_block_device_head_and_tail,
        #           device=device,
        #           force=force,
        #           no_backup=no_backup,
        #           verbose=verbose,
        #           debug=debug,)
        ##run_command("sgdisk --zap-all " + boot_device)

    run_command("parted " + device.as_posix() + " --script -- mklabel msdos")
    #run_command("parted " + device + " --script -- mklabel gpt")
    #run_command("sgdisk --clear " + device) #alt way to greate gpt label


@cli.command()
@click.option('--device', is_flag=False, required=True)
@click.option('--start', is_flag=False, required=True, type=str)
@click.option('--end', is_flag=False, required=True, type=str)
@click.option('--partition-number', is_flag=False, required=True, type=str)
@click.option('--force', is_flag=True, required=False)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
@click.pass_context
def write_efi_partition(ctx, *,
                        device: Path,
                        start: int,
                        end: int,
                        partition_number: str,
                        force: bool,
                        verbose: bool,
                        debug: bool,
                        ):
    device = Path(device)
    ic('creating efi partition on:', device, partition_number, start, end)
    assert device_is_not_a_partition(device=device, verbose=verbose, debug=debug,)
    #assert not device.endswith('/')  # Path() fixed that
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)
    assert int(partition_number)

    if not force:
        warn((device,), verbose=verbose, debug=debug,)

    #output = run_command("parted " + device + " --align optimal --script -- mkpart primary " + start + ' ' + end)
    run_command("parted --align minimal " + device.as_posix() + " --script -- mkpart primary " + str(start) + ' ' + str(end), verbose=True)
    run_command("parted " + device.as_posix() + " --script -- name " + partition_number + " EFI", verbose=True)
    run_command("parted " + device.as_posix() + " --script -- set " + partition_number + " boot on", verbose=True)

    fat16_partition_device = add_partition_number_to_device(device=device, partition_number=partition_number)
    wait_for_block_special_device_to_exist(device=fat16_partition_device)
    #while not path_is_block_special(fat16_partition_device):
    #    eprint("fat16_partition_device", fat16_partition_device, "is not block special yet, waiting a second.")
    #    time.sleep(1)

    ctx.invoke(create_filesystem, device=fat16_partition_device, filesystem='fat16', force=True)

    # 127488 /mnt/sdb2/EFI/BOOT/BOOTX64.EFI


@cli.command()
@click.option('--device', is_flag=False, required=True)
@click.option('--start', is_flag=False, required=True, type=str)
@click.option('--end', is_flag=False, required=True, type=str)
@click.option('--partition_number', is_flag=False, required=True, type=str)
@click.option('--force', is_flag=True, required=False)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
def write_grub_bios_partition(*,
                              device: Path,
                              start: int,
                              end: int,
                              force: int,
                              partition_number: str,
                              verbose: bool,
                              debug: bool,
                              ):
    device = Path(device)
    ic('creating grub_bios partition on:', device, partition_number, start, end)
    assert device_is_not_a_partition(device=device, verbose=verbose, debug=debug,)
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)
    assert int(partition_number)

    if not force:
        warn((device,), verbose=verbose, debug=debug,)

    #run_command("parted " + device + " --align optimal --script -- mkpart primary " + str(start) + ' ' + str(end), verbose=True)
    run_command("parted " + device.as_posix() + " --align minimal --script -- mkpart primary " + str(start) + ' ' + str(end), verbose=True)
    run_command("parted " + device.as_posix() + " --script -- name " + partition_number + " BIOSGRUB", verbose=True)
    run_command("parted " + device.as_posix() + " --script -- set " + partition_number + " bios_grub on", verbose=True)
    grub_bios_partition_device = add_partition_number_to_device(device=device, partition_number=partition_number)
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


@cli.command()
@click.argument('device', required=True, nargs=1, type=str)
@click.option('--filesystem', "filesystem", is_flag=False, required=True, type=click.Choice(['fat16', 'fat32', 'ext4']))
@click.option('--force', is_flag=True, required=False)
@click.option('--raw-device', is_flag=True, required=False)
@click.option('--verbose', is_flag=True)
@click.option('--debug', is_flag=True)
def create_filesystem(*,
                      device: Path,
                      filesystem: str,
                      force: bool,
                      raw_device: bool,
                      verbose: bool,
                      debug: bool,
                      ):

    device = Path(device)
    eprint("creating", filesystem, "filesystem on:", device)
    if not raw_device:
        assert device.as_posix()[-1].isdigit()
    # oddly, this failed on '/dev/sda2', maybe the kernel was not done
    # digesting the previous table change? (using fat16)
    wait_for_block_special_device_to_exist(device=device)
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)

    if not force:
        warn((device,), verbose=verbose, debug=debug,)

    if filesystem == 'fat16':
        run_command("mkfs.fat -F16 -s2 " + device.as_posix())
    elif filesystem == 'fat32':
        run_command("mkfs.fat -F32 -s2 " + device.as_posix())
    elif filesystem == 'ext4':
        run_command("mkfs.ext4 " + device.as_posix())
    else:
        assert False


@cli.command()
@click.argument('device', nargs=1,)
@click.option('--force', is_flag=True,)
@click.option('--ask', is_flag=True,)
@click.option('--verbose', is_flag=True,)
@click.option('--debug', is_flag=True,)
@click.pass_context
def destroy_block_device(ctx, *,
                         device: Path,
                         force: bool,
                         ask: bool,
                         verbose: bool,
                         debug: bool,
                         ):

    device = Path(device)
    assert isinstance(force, bool)
    #assert source in ['urandom', 'zero']
    assert not device.name.endswith('/')
    assert device_is_not_a_partition(device=device,
                                     verbose=verbose,
                                     debug=debug,)
    assert device.as_posix().startswith('/dev/')
    ic('destroying device:', device)
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)
    if not force:
        warn((device,), verbose=verbose, debug=debug,)
    #device_name = device.split('/')[-1]
    assert len(device.name) >= 3
    assert '/' not in device.name
    assert device.as_posix().endswith(device.name)
    luks_mapper = Path("/dev/mapper") / Path(device.name)
    ic(luks_mapper)
    assert not path_is_block_special(luks_mapper, follow_symlinks=True)
    assert not luks_mapper.exists()

    # zero out any partition or existing LUKS header... otherwise cryptsetup throws warning and asks for comfirmation
    # the LUKS signature "SKUL" is at bytes 16384-16387
    ctx.invoke(destroy_block_device_head,
               device=device.as_posix(),
               source='zero',
               size=16387,
               verbose=True,)

    luks_command = "cryptsetup open --type plain -d /dev/urandom " + device.as_posix() + " " + device.name
    ic(luks_command)
    run_command(luks_command, verbose=True, expected_exit_status=0, ask=ask)
    #sh.cryptsetup('open', '--type', 'plain', '-d', '/dev/urandom', device.as_posix(), device.name)

    assert path_is_block_special(luks_mapper, follow_symlinks=True)
    assert not block_special_path_is_mounted(luks_mapper, verbose=verbose, debug=debug,)
    sh.ls('-alh', luks_mapper)

    # sys-fs/dd-rescue
    # --abort_we: makes dd_rescue abort on any write errors
    #wipe_command = "dd_rescue --color=0 --abort_we /dev/zero " + luks_mapper.as_posix()
    #ic(wipe_command)
    #run_command(wipe_command, verbose=True, expected_exit_status=0, ask=ask)
    sh.dd_rescue('--verbose',
                 '--color=1',
                 '--abort_we',
                 '/dev/zero',
                 luks_mapper,
                 _out=write_output,
                 _err=write_output,
                 _out_bufsize=1,
                 _err_bufsize=1,
                 _ok_code=[21],)

    time.sleep(1) # so "cryptsetup close" doesnt throw an error

    close_command = "cryptsetup close " + device.name
    ic(close_command)
    run_command(close_command, verbose=True, expected_exit_status=0, ask=ask)


@cli.command()
@click.argument('device', required=True, nargs=1, type=str)
@click.option('--size', is_flag=False, required=True, type=int)
@click.option('--source', is_flag=False, required=True, type=click.Choice(['urandom', 'zero']))
@click.option('--no-backup', is_flag=True, required=False)
@click.option('--note', is_flag=False, type=str)
@click.option('--ask', is_flag=True, required=False)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
@click.pass_context
def destroy_block_device_head(ctx, *,
                              device: Path,
                              size: int,
                              source: str,
                              ask: bool,
                              no_backup: bool,
                              note: str,
                              verbose: bool,
                              debug: bool,
                              ):
    device = Path(device)
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)
    if verbose:
        ic(device, size, source)
    ctx.invoke(destroy_byte_range,
               device=device,
               start=0,
               end=size,
               source=source,
               no_backup=no_backup,
               note=note,
               verbose=verbose,
               debug=debug,)


@cli.command()
@click.argument('device', required=True, nargs=1, type=str)
@click.option('--size', is_flag=False, required=True, type=int)
@click.option('--source', is_flag=False, required=True, type=click.Choice(['urandom', 'zero']))
@click.option('--ask', is_flag=True, required=False)
@click.option('--no-backup', is_flag=True, required=False)
@click.option('--note', is_flag=False, type=str)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
@click.pass_context
def destroy_block_device_tail(ctx, *,
                              device: Path,
                              size: int,
                              source,
                              no_backup: bool,
                              ask: bool,
                              note: str,
                              verbose: bool,
                              debug: bool,
                              ):
    device = Path(device)
    assert size > 0
    device_size = get_block_device_size(device=device, verbose=verbose, debug=debug,)
    assert size <= device_size
    start = device_size - size
    assert start > 0
    end = start + size
    ctx.invoke(destroy_byte_range,
               device=device,
               start=start,
               end=end,
               ask=ask,
               source=source,
               no_backup=no_backup,
               note=note,
               verbose=verbose,
               debug=debug,)


@cli.command()
@click.argument('device', required=True, nargs=1, type=str,)
@click.option('--start', is_flag=False, required=True, type=int,)
@click.option('--end', is_flag=False, required=True, type=int,)
@click.option('--source', is_flag=False, required=True, type=click.Choice(['urandom', 'zero']),)
@click.option('--ask', is_flag=True,)
@click.option('--no-backup', is_flag=True,)
@click.option('--note', is_flag=False, type=str,)
@click.option('--verbose', is_flag=True,)
@click.option('--debug', is_flag=True,)
@click.pass_context
def destroy_byte_range(ctx, *,
                       device: Path,
                       start: int,
                       end: int,
                       source: str,
                       ask: bool,
                       no_backup: bool,
                       note: str,
                       verbose: bool,
                       debug: bool,
                       ):
    device = Path(device)
    assert start >= 0
    assert end > 0
    assert start < end
    eprint("source:", source)
    if not no_backup:
        ctx.invoke(backup_byte_range,
                   device=device,
                   start=start,
                   end=end,
                   note=note,
                   verbose=verbose,
                   debug=debug,)
    bytes_to_zero = end - start
    assert bytes_to_zero > 0
    with open(device, 'wb') as dfh:
        dfh.seek(start)
        if source == 'zero':
            dfh.write(bytearray(bytes_to_zero))
        if source == 'urandom':
            urandom_bytes = os.urandom(bytes_to_zero)
            assert len(urandom_bytes) == bytes_to_zero
            dfh.write(urandom_bytes)


@cli.command()
@click.argument('device', required=True, nargs=1)
@click.option('--size', is_flag=False, type=int, default=(2048))
@click.option('--source', is_flag=False, required=True, type=click.Choice(['urandom', 'zero']))
@click.option('--note', is_flag=False, type=str)
@click.option('--ask', is_flag=True, required=False)
@click.option('--force', is_flag=True, required=False)
@click.option('--no-backup', is_flag=True, required=False)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
@click.pass_context
def destroy_block_device_head_and_tail(ctx, *,
                                       device: Path,
                                       size: int,
                                       source: str,
                                       note: str,
                                       ask: bool,
                                       force: bool,
                                       no_backup: bool,
                                       verbose: bool,
                                       debug: bool,
                                       ):
    #run_command("sgdisk --zap-all " + device) #alt method
    device = Path(device)
    #assert isinstance(device, str)
    assert device_is_not_a_partition(device=device,
                                     verbose=verbose,
                                     debug=debug,)
    eprint("destroying device:", device)
    assert path_is_block_special(device)
    assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)
    if not force:
        warn((device,), verbose=verbose, debug=debug,)
    if not note:
        note = str(time.time()) + '_' + device.as_posix().replace('/', '_')
        eprint("note:", note)

    ctx.invoke(destroy_block_device_head,
               device=device,
               size=size,
               source=source,
               note=note,
               ask=ask,
               no_backup=no_backup,
               verbose=verbose,
               debug=debug,)
    ctx.invoke(destroy_block_device_tail,
               device=device,
               size=size,
               source=source,
               note=note,
               ask=ask,
               no_backup=no_backup,
               verbose=verbose,
               debug=debug,)


@cli.command()
@click.argument('devices', required=True, nargs=-1)
@click.option('--size', is_flag=False, type=int, default=(1024 * 1024 * 128))
@click.option('--note', is_flag=False, type=str)
@click.option('--force', is_flag=True, required=False)
@click.option('--ask', is_flag=True, required=False)
@click.option('--no-backup', is_flag=True, required=False)
@click.option('--verbose', is_flag=True, required=False)
@click.option('--debug', is_flag=True, required=False)
@click.pass_context
def destroy_block_devices_head_and_tail(ctx, *,
                                        devices: tuple[Path, ...],
                                        size: int,
                                        note: str,
                                        ask: bool,
                                        force: bool,
                                        no_backup: bool,
                                        verbose: bool,
                                        debug: bool,
                                        ):

    assert (isinstance(devices, list) or isinstance(devices, tuple))
    for device in devices:
        device = Path(device)
        assert device_is_not_a_partition(device=device,
                                         verbose=verbose,
                                         debug=debug,)
        eprint("destroying device:", device)
        assert path_is_block_special(device)
        assert not block_special_path_is_mounted(device, verbose=verbose, debug=debug,)

    if not force:
        warn(devices, verbose=verbose, debug=debug,)

    for device in devices:
        ctx.invoke(destroy_block_device_head_and_tail,
                   device=device,
                   size=size,
                   note=note,
                   ask=ask,
                   force=force,
                   no_backup=no_backup,
                   verbose=verbose,
                   debug=debug,)


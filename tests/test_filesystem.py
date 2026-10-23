import os
from pathlib import Path

import pytest

from scpi.dispatcher import Dispatcher
from scpi.events import EventCode
from scpi.filesystem import (
    create_initial_structure,
    register_filesystem_commands,
    virtual_to_real,
)
from scpi.state import FileSystemState, InstrumentState


@pytest.fixture
def fs(tmp_path: Path) -> FileSystemState:
    state = FileSystemState(cwd=r"C:\TekScope", root=str(tmp_path))
    return state


def test_virtual_to_real_absolute_path_maps_under_drive_dir(
    fs: FileSystemState, tmp_path: Path
) -> None:
    result = virtual_to_real(r"C:\TekScope\Waveforms", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "Waveforms")
    assert result == expected


def test_virtual_to_real_drive_d_maps_under_d_dir(fs: FileSystemState, tmp_path: Path) -> None:
    result = virtual_to_real(r"D:\Data\file.txt", fs)
    expected = os.path.join(str(tmp_path), "D", "Data", "file.txt")
    assert result == expected


def test_virtual_to_real_dot_relative_path_resolves_against_cwd(
    fs: FileSystemState, tmp_path: Path
) -> None:
    result = virtual_to_real(r".\newfile.txt", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "newfile.txt")
    assert result == expected


def test_virtual_to_real_implied_relative_path_resolves_against_cwd(
    fs: FileSystemState, tmp_path: Path
) -> None:
    result = virtual_to_real("newfile.txt", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "newfile.txt")
    assert result == expected


def test_virtual_to_real_forward_slashes_map_like_backslashes(
    fs: FileSystemState, tmp_path: Path
) -> None:
    result = virtual_to_real("C:/TekScope/Waveforms", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "Waveforms")
    assert result == expected


def test_virtual_to_real_single_component_path_maps_under_drive_dir(
    fs: FileSystemState, tmp_path: Path
) -> None:
    result = virtual_to_real(r"C:\TekScope", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope")
    assert result == expected


def test_virtual_to_real_changed_cwd_resolves_relative_against_new_cwd(tmp_path: Path) -> None:
    fs = FileSystemState(cwd=r"C:\TekScope\Waveforms", root=str(tmp_path))
    result = virtual_to_real("wfm1.wfm", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "Waveforms", "wfm1.wfm")
    assert result == expected


def make_fs_state(tmp_path: Path) -> FileSystemState:
    return FileSystemState(cwd=r"C:\TekScope", root=str(tmp_path))


def make_state(tmp_path: Path) -> InstrumentState:
    fs = make_fs_state(tmp_path)
    return InstrumentState(filesystem=fs)


def make_dispatcher() -> Dispatcher:
    d = Dispatcher()
    register_filesystem_commands(d)
    return d


# --- create_initial_structure ---


def test_virtual_to_real_dotdot_component_moves_up_one_dir(
    fs: FileSystemState, tmp_path: Path
) -> None:
    result = virtual_to_real(r"C:\TekScope\Waveforms\..\Images", fs)
    assert result == os.path.join(str(tmp_path), "C", "TekScope", "Images")


def test_virtual_to_real_dotdot_past_drive_root_stays_at_drive_root(
    fs: FileSystemState, tmp_path: Path
) -> None:
    result = virtual_to_real(r"C:\..\..\..\etc\hostname", fs)
    assert result == os.path.join(str(tmp_path), "C", "etc", "hostname")


def test_virtual_to_real_relative_dotdot_resolves_against_cwd(tmp_path: Path) -> None:
    fs = FileSystemState(cwd=r"C:\TekScope\Waveforms", root=str(tmp_path))
    result = virtual_to_real(r"..\Images", fs)
    assert result == os.path.join(str(tmp_path), "C", "TekScope", "Images")


def test_virtual_to_real_dot_components_are_ignored(fs: FileSystemState, tmp_path: Path) -> None:
    result = virtual_to_real(r"C:\TekScope\.\Waveforms", fs)
    assert result == os.path.join(str(tmp_path), "C", "TekScope", "Waveforms")


def test_virtual_to_real_rooted_path_without_drive_uses_cwd_drive(
    fs: FileSystemState, tmp_path: Path
) -> None:
    result = virtual_to_real(r"\Data\f.txt", fs)
    assert result == os.path.join(str(tmp_path), "C", "Data", "f.txt")


def test_create_initial_structure_creates_tekscope_tree(tmp_path: Path) -> None:
    fs = make_fs_state(tmp_path)
    create_initial_structure(fs)
    for vpath in [
        r"C:\TekScope",
        r"C:\TekScope\Waveforms",
        r"C:\TekScope\Images",
        r"C:\TekScope\Settings",
    ]:
        assert os.path.isdir(virtual_to_real(vpath, fs))


# --- CWD ---


def test_cwd_query_initially_returns_quoted_default(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:CWD", True, [], state)
    assert resp == r'"C:\TekScope"'


def test_cwd_set_absolute_path_updates_cwd(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, [r"C:\TekScope\Waveforms"], state)
    assert state.filesystem.cwd == r"C:\TekScope\Waveforms"


def test_cwd_query_after_set_returns_quoted_new_cwd(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, [r"C:\TekScope\Waveforms"], state)
    resp = d.dispatch("FILESYSTEM:CWD", True, [], state)
    assert resp == r'"C:\TekScope\Waveforms"'


def test_cwd_set_relative_path_stores_absolute_path(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, ["Waveforms"], state)
    assert state.filesystem.cwd == r"C:\TekScope\Waveforms"


def test_cwd_set_dotdot_moves_to_parent(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, [".."], state)
    assert state.filesystem.cwd == "C:\\"


def test_cwd_set_forward_slashes_stores_backslash_path(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, ["C:/TekScope/Images"], state)
    assert state.filesystem.cwd == r"C:\TekScope\Images"


def test_cwd_set_missing_dir_pushes_file_name_not_found_and_keeps_cwd(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, ["NoSuchDir"], state)
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue
    assert state.filesystem.cwd == r"C:\TekScope"


def test_cwd_set_file_path_pushes_file_name_not_found_and_keeps_cwd(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    open(virtual_to_real(r"C:\TekScope\setup.set", state.filesystem), "w").close()
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, ["setup.set"], state)
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue
    assert state.filesystem.cwd == r"C:\TekScope"


# --- DIR? ---


def test_dir_query_includes_dot_entries(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:DIR", True, [], state)
    assert isinstance(resp, str)
    # Should include "." and ".." at minimum, and subdirs
    assert '"."' in resp
    assert '".."' in resp


def test_dir_query_with_file_lists_quoted_file(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    # Create a test file in CWD
    real_cwd = virtual_to_real(state.filesystem.cwd, state.filesystem)
    open(os.path.join(real_cwd, "test.wfm"), "w").close()
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:DIR", True, [], state)
    assert isinstance(resp, str)
    assert '"test.wfm"' in resp


def test_filesystem_query_matches_dir_query(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    resp_dir = d.dispatch("FILESYSTEM:DIR", True, [], state)
    resp_alias = d.dispatch("FILESYSTEM", True, [], state)
    assert resp_dir == resp_alias


# --- MKDir ---


def test_mkdir_new_path_creates_directory(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:MKDIR", False, [r"C:\TekScope\NewDir"], state)
    assert os.path.isdir(virtual_to_real(r"C:\TekScope\NewDir", state.filesystem))


def test_mkdir_existing_path_pushes_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:MKDIR", False, [r"C:\TekScope\Waveforms"], state)
    assert EventCode.FILE_NAME_ERROR in state.event_queue


# --- RMDir ---


def test_rmdir_empty_dir_removes_it(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:MKDIR", False, [r"C:\TekScope\Empty"], state)
    d.dispatch("FILESYSTEM:RMDIR", False, [r"C:\TekScope\Empty"], state)
    assert not os.path.exists(virtual_to_real(r"C:\TekScope\Empty", state.filesystem))


def test_rmdir_non_empty_dir_pushes_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    real = virtual_to_real(r"C:\TekScope\Waveforms", state.filesystem)
    open(os.path.join(real, "x.wfm"), "w").close()
    d.dispatch("FILESYSTEM:RMDIR", False, [r"C:\TekScope\Waveforms"], state)
    assert EventCode.MASS_STORAGE_ERROR in state.event_queue


# --- DELEte ---


def test_delete_existing_file_removes_it(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    fpath = os.path.join(real, "todelete.wfm")
    open(fpath, "w").close()
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:DELETE", False, [r"C:\TekScope\todelete.wfm"], state)
    assert not os.path.exists(fpath)


def test_delete_missing_file_pushes_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:DELETE", False, [r"C:\TekScope\nosuchfile.wfm"], state)
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


# --- RENAme ---


def test_rename_existing_file_moves_it(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    open(os.path.join(real, "old.wfm"), "w").close()
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:RENAME", False, [r"C:\TekScope\old.wfm", r"C:\TekScope\new.wfm"], state)
    assert not os.path.exists(os.path.join(real, "old.wfm"))
    assert os.path.exists(os.path.join(real, "new.wfm"))


def test_rename_missing_file_pushes_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch(
        "FILESYSTEM:RENAME", False, [r"C:\TekScope\ghost.wfm", r"C:\TekScope\new.wfm"], state
    )
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


# --- COPy ---


def test_copy_existing_file_duplicates_contents(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    src = os.path.join(real, "src.wfm")
    with open(src, "w") as f:
        f.write("data")
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:COPY", False, [r"C:\TekScope\src.wfm", r"C:\TekScope\dst.wfm"], state)
    dst = os.path.join(real, "dst.wfm")
    assert os.path.exists(dst)
    assert open(dst).read() == "data"


def test_copy_missing_file_pushes_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:COPY", False, [r"C:\TekScope\ghost.wfm", r"C:\TekScope\dst.wfm"], state)
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


# --- READFile / PRInt ---


def test_readfile_existing_file_returns_raw_bytes(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    fpath = os.path.join(real, "wave.wfm")
    with open(fpath, "wb") as f:
        f.write(b"\x00\x01\x02\x03")
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:READFILE", False, [r"C:\TekScope\wave.wfm", "GPIB"], state)
    assert resp == b"\x00\x01\x02\x03"


def test_print_existing_file_returns_same_bytes_as_readfile(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    fpath = os.path.join(real, "wave.wfm")
    with open(fpath, "wb") as f:
        f.write(b"hello")
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:PRINT", False, [r"C:\TekScope\wave.wfm", "GPIB"], state)
    assert resp == b"hello"


def test_readfile_missing_file_pushes_error_and_returns_none(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:READFILE", False, [r"C:\TekScope\nope.wfm", "GPIB"], state)
    assert resp is None
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


# --- WRITEFile ---


def test_writefile_block_data_creates_file(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\out.wfm", b"\xde\xad\xbe\xef"], state)
    real = virtual_to_real(r"C:\TekScope\out.wfm", state.filesystem)
    assert os.path.exists(real)
    assert open(real, "rb").read() == b"\xde\xad\xbe\xef"


def test_writefile_existing_file_overwrites_contents(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\out.wfm", b"first"], state)
    d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\out.wfm", b"second"], state)
    real = virtual_to_real(r"C:\TekScope\out.wfm", state.filesystem)
    assert open(real, "rb").read() == b"second"


def test_writefile_missing_parent_dir_pushes_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    # Try to write to a directory that doesn't exist
    d.dispatch(
        "FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\NonExistentDir\file.wfm", b"data"], state
    )
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


def test_mkdir_block_data_path_pushes_data_type_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:MKDIR", False, [b"C:\\TekScope\\NewDir"], state)
    assert EventCode.DATA_TYPE_ERROR in state.event_queue


def test_cwd_set_block_data_path_pushes_data_type_error_and_keeps_cwd(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, [b"C:\\TekScope\\Waveforms"], state)
    assert EventCode.DATA_TYPE_ERROR in state.event_queue
    assert state.filesystem.cwd == r"C:\TekScope"


def test_cwd_set_without_path_pushes_missing_parameter(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, [], state)
    assert EventCode.MISSING_PARAMETER in state.event_queue


def test_writefile_without_data_pushes_missing_parameter(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\out.wfm"], state)
    assert EventCode.MISSING_PARAMETER in state.event_queue


def test_mkdir_missing_parent_pushes_file_name_not_found(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:MKDIR", False, [r"C:\TekScope\Missing\Child"], state)
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue
    assert not os.path.exists(virtual_to_real(r"C:\TekScope\Missing", state.filesystem))


def test_delete_directory_pushes_file_name_error_and_keeps_dir(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:DELETE", False, [r"C:\TekScope\Images"], state)
    assert EventCode.FILE_NAME_ERROR in state.event_queue
    assert os.path.isdir(virtual_to_real(r"C:\TekScope\Images", state.filesystem))


def test_readfile_directory_pushes_file_name_error_and_returns_none(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:READFILE", False, [r"C:\TekScope\Images", "GPIB"], state)
    assert resp is None
    assert EventCode.FILE_NAME_ERROR in state.event_queue


def test_copy_directory_source_pushes_file_name_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:COPY", False, [r"C:\TekScope\Images", r"C:\TekScope\Copy"], state)
    assert EventCode.FILE_NAME_ERROR in state.event_queue


def test_writefile_directory_path_pushes_file_name_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\Images", b"data"], state)
    assert EventCode.FILE_NAME_ERROR in state.event_queue


def test_writefile_read_only_dir_pushes_mass_storage_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    read_only = virtual_to_real(r"C:\TekScope\Settings", state.filesystem)
    os.chmod(read_only, 0o500)
    try:
        d = make_dispatcher()
        d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\Settings\x.set", b"x"], state)
    finally:
        os.chmod(read_only, 0o700)
    assert EventCode.MASS_STORAGE_ERROR in state.event_queue


def test_readfile_path_through_a_file_pushes_file_name_not_found(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    open(virtual_to_real(r"C:\TekScope\setup.set", state.filesystem), "w").close()
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:READFILE", False, [r"C:\TekScope\setup.set\child", "GPIB"], state)
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


def test_readfile_without_port_pushes_missing_parameter(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    open(virtual_to_real(r"C:\TekScope\wave.wfm", state.filesystem), "w").close()
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:READFILE", False, [r"C:\TekScope\wave.wfm"], state)
    assert resp is None
    assert EventCode.MISSING_PARAMETER in state.event_queue


def test_readfile_unsupported_port_pushes_invalid_character_data(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    open(virtual_to_real(r"C:\TekScope\wave.wfm", state.filesystem), "w").close()
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:READFILE", False, [r"C:\TekScope\wave.wfm", "RS232"], state)
    assert resp is None
    assert EventCode.INVALID_CHARACTER_DATA in state.event_queue


def test_readfile_short_form_port_returns_bytes(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    with open(virtual_to_real(r"C:\TekScope\wave.wfm", state.filesystem), "wb") as f:
        f.write(b"abc")
    d = make_dispatcher()
    resp = d.dispatch("FILESYSTEM:READFILE", False, [r"C:\TekScope\wave.wfm", "gpi"], state)
    assert resp == b"abc"


def test_mkdir_path_with_nul_byte_pushes_file_name_error(tmp_path: Path) -> None:
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:MKDIR", False, ["bad\x00name"], state)
    assert EventCode.FILE_NAME_ERROR in state.event_queue


def test_dir_query_after_cwd_removed_resets_cwd_to_default(tmp_path: Path) -> None:
    # Manual: deleting the CWD resets it to C:\TekScope on the next file system command.
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher()
    d.dispatch("FILESYSTEM:CWD", False, [r"C:\TekScope\Images"], state)
    d.dispatch("FILESYSTEM:RMDIR", False, [r"C:\TekScope\Images"], state)
    resp = d.dispatch("FILESYSTEM:DIR", True, [], state)
    assert state.filesystem.cwd == r"C:\TekScope"
    assert resp == '".","..","Settings","Waveforms"'

import os

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
def fs(tmp_path):
    state = FileSystemState(cwd=r"C:\TekScope", root=str(tmp_path))
    return state


def test_virtual_to_real_absolute_path_maps_under_drive_dir(fs, tmp_path):
    result = virtual_to_real(r"C:\TekScope\Waveforms", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "Waveforms")
    assert result == expected


def test_virtual_to_real_drive_d_maps_under_d_dir(fs, tmp_path):
    result = virtual_to_real(r"D:\Data\file.txt", fs)
    expected = os.path.join(str(tmp_path), "D", "Data", "file.txt")
    assert result == expected


def test_virtual_to_real_dot_relative_path_resolves_against_cwd(fs, tmp_path):
    result = virtual_to_real(r".\newfile.txt", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "newfile.txt")
    assert result == expected


def test_virtual_to_real_implied_relative_path_resolves_against_cwd(fs, tmp_path):
    result = virtual_to_real("newfile.txt", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "newfile.txt")
    assert result == expected


def test_virtual_to_real_forward_slashes_map_like_backslashes(fs, tmp_path):
    result = virtual_to_real("C:/TekScope/Waveforms", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "Waveforms")
    assert result == expected


def test_virtual_to_real_single_component_path_maps_under_drive_dir(fs, tmp_path):
    result = virtual_to_real(r"C:\TekScope", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope")
    assert result == expected


def test_virtual_to_real_changed_cwd_resolves_relative_against_new_cwd(tmp_path):
    fs = FileSystemState(cwd=r"C:\TekScope\Waveforms", root=str(tmp_path))
    result = virtual_to_real("wfm1.wfm", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "Waveforms", "wfm1.wfm")
    assert result == expected


def make_fs_state(tmp_path):
    return FileSystemState(cwd=r"C:\TekScope", root=str(tmp_path))


def make_state(tmp_path):
    fs = make_fs_state(tmp_path)
    return InstrumentState(filesystem=fs)


def make_dispatcher(state):
    d = Dispatcher()
    register_filesystem_commands(d)
    return d


# --- create_initial_structure ---


def test_virtual_to_real_dotdot_component_moves_up_one_dir(fs, tmp_path):
    result = virtual_to_real(r"C:\TekScope\Waveforms\..\Images", fs)
    assert result == os.path.join(str(tmp_path), "C", "TekScope", "Images")


def test_virtual_to_real_dotdot_past_drive_root_stays_at_drive_root(fs, tmp_path):
    result = virtual_to_real(r"C:\..\..\..\etc\hostname", fs)
    assert result == os.path.join(str(tmp_path), "C", "etc", "hostname")


def test_virtual_to_real_relative_dotdot_resolves_against_cwd(tmp_path):
    fs = FileSystemState(cwd=r"C:\TekScope\Waveforms", root=str(tmp_path))
    result = virtual_to_real(r"..\Images", fs)
    assert result == os.path.join(str(tmp_path), "C", "TekScope", "Images")


def test_virtual_to_real_dot_components_are_ignored(fs, tmp_path):
    result = virtual_to_real(r"C:\TekScope\.\Waveforms", fs)
    assert result == os.path.join(str(tmp_path), "C", "TekScope", "Waveforms")


def test_virtual_to_real_rooted_path_without_drive_uses_cwd_drive(fs, tmp_path):
    result = virtual_to_real(r"\Data\f.txt", fs)
    assert result == os.path.join(str(tmp_path), "C", "Data", "f.txt")


def test_create_initial_structure_creates_tekscope_tree(tmp_path):
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


def test_cwd_query_initially_returns_quoted_default(tmp_path):
    state = make_state(tmp_path)
    d = make_dispatcher(state)
    resp = d.dispatch("FILESYSTEM:CWD", True, [], state)
    assert resp == r'"C:\TekScope"'


def test_cwd_set_absolute_path_updates_cwd(tmp_path):
    state = make_state(tmp_path)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:CWD", False, [r"C:\TekScope\Waveforms"], state)
    assert state.filesystem.cwd == r"C:\TekScope\Waveforms"


def test_cwd_query_after_set_returns_quoted_new_cwd(tmp_path):
    state = make_state(tmp_path)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:CWD", False, [r"C:\TekScope\Waveforms"], state)
    resp = d.dispatch("FILESYSTEM:CWD", True, [], state)
    assert resp == r'"C:\TekScope\Waveforms"'


# --- DIR? ---


def test_dir_query_includes_dot_entries(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    resp = d.dispatch("FILESYSTEM:DIR", True, [], state)
    # Should include "." and ".." at minimum, and subdirs
    assert '"."' in resp
    assert '".."' in resp


def test_dir_query_with_file_lists_quoted_file(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    # Create a test file in CWD
    real_cwd = virtual_to_real(state.filesystem.cwd, state.filesystem)
    open(os.path.join(real_cwd, "test.wfm"), "w").close()
    d = make_dispatcher(state)
    resp = d.dispatch("FILESYSTEM:DIR", True, [], state)
    assert '"test.wfm"' in resp


def test_filesystem_query_matches_dir_query(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    resp_dir = d.dispatch("FILESYSTEM:DIR", True, [], state)
    resp_alias = d.dispatch("FILESYSTEM", True, [], state)
    assert resp_dir == resp_alias


# --- MKDir ---


def test_mkdir_new_path_creates_directory(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:MKDIR", False, [r"C:\TekScope\NewDir"], state)
    assert os.path.isdir(virtual_to_real(r"C:\TekScope\NewDir", state.filesystem))


def test_mkdir_existing_path_pushes_error(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:MKDIR", False, [r"C:\TekScope\Waveforms"], state)
    assert EventCode.FILE_NAME_ERROR in state.event_queue


# --- RMDir ---


def test_rmdir_empty_dir_removes_it(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:MKDIR", False, [r"C:\TekScope\Empty"], state)
    d.dispatch("FILESYSTEM:RMDIR", False, [r"C:\TekScope\Empty"], state)
    assert not os.path.exists(virtual_to_real(r"C:\TekScope\Empty", state.filesystem))


def test_rmdir_non_empty_dir_pushes_error(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    real = virtual_to_real(r"C:\TekScope\Waveforms", state.filesystem)
    open(os.path.join(real, "x.wfm"), "w").close()
    d.dispatch("FILESYSTEM:RMDIR", False, [r"C:\TekScope\Waveforms"], state)
    assert EventCode.MASS_STORAGE_ERROR in state.event_queue


# --- DELEte ---


def test_delete_existing_file_removes_it(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    fpath = os.path.join(real, "todelete.wfm")
    open(fpath, "w").close()
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:DELETE", False, [r"C:\TekScope\todelete.wfm"], state)
    assert not os.path.exists(fpath)


def test_delete_missing_file_pushes_error(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:DELETE", False, [r"C:\TekScope\nosuchfile.wfm"], state)
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


# --- RENAme ---


def test_rename_existing_file_moves_it(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    open(os.path.join(real, "old.wfm"), "w").close()
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:RENAME", False, [r"C:\TekScope\old.wfm", r"C:\TekScope\new.wfm"], state)
    assert not os.path.exists(os.path.join(real, "old.wfm"))
    assert os.path.exists(os.path.join(real, "new.wfm"))


def test_rename_missing_file_pushes_error(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch(
        "FILESYSTEM:RENAME", False, [r"C:\TekScope\ghost.wfm", r"C:\TekScope\new.wfm"], state
    )
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


# --- COPy ---


def test_copy_existing_file_duplicates_contents(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    src = os.path.join(real, "src.wfm")
    with open(src, "w") as f:
        f.write("data")
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:COPY", False, [r"C:\TekScope\src.wfm", r"C:\TekScope\dst.wfm"], state)
    dst = os.path.join(real, "dst.wfm")
    assert os.path.exists(dst)
    assert open(dst).read() == "data"


def test_copy_missing_file_pushes_error(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:COPY", False, [r"C:\TekScope\ghost.wfm", r"C:\TekScope\dst.wfm"], state)
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


# --- READFile / PRInt ---


def test_readfile_existing_file_returns_raw_bytes(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    fpath = os.path.join(real, "wave.wfm")
    with open(fpath, "wb") as f:
        f.write(b"\x00\x01\x02\x03")
    d = make_dispatcher(state)
    resp = d.dispatch("FILESYSTEM:READFILE", False, [r"C:\TekScope\wave.wfm", "GPIB"], state)
    assert resp == b"\x00\x01\x02\x03"


def test_print_existing_file_returns_same_bytes_as_readfile(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    fpath = os.path.join(real, "wave.wfm")
    with open(fpath, "wb") as f:
        f.write(b"hello")
    d = make_dispatcher(state)
    resp = d.dispatch("FILESYSTEM:PRINT", False, [r"C:\TekScope\wave.wfm", "GPIB"], state)
    assert resp == b"hello"


def test_readfile_missing_file_pushes_error_and_returns_none(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    resp = d.dispatch("FILESYSTEM:READFILE", False, [r"C:\TekScope\nope.wfm"], state)
    assert resp is None
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


# --- WRITEFile ---


def test_writefile_block_data_creates_file(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\out.wfm", b"\xde\xad\xbe\xef"], state)
    real = virtual_to_real(r"C:\TekScope\out.wfm", state.filesystem)
    assert os.path.exists(real)
    assert open(real, "rb").read() == b"\xde\xad\xbe\xef"


def test_writefile_existing_file_overwrites_contents(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\out.wfm", b"first"], state)
    d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\out.wfm", b"second"], state)
    real = virtual_to_real(r"C:\TekScope\out.wfm", state.filesystem)
    assert open(real, "rb").read() == b"second"


def test_writefile_missing_parent_dir_pushes_error(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    # Try to write to a directory that doesn't exist
    d.dispatch(
        "FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\NonExistentDir\file.wfm", b"data"], state
    )
    assert EventCode.FILE_NAME_NOT_FOUND in state.event_queue


def test_mkdir_block_data_path_pushes_data_type_error(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:MKDIR", False, [b"C:\\TekScope\\NewDir"], state)
    assert EventCode.DATA_TYPE_ERROR in state.event_queue


def test_cwd_set_block_data_path_pushes_data_type_error_and_keeps_cwd(tmp_path):
    state = make_state(tmp_path)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:CWD", False, [b"C:\\TekScope\\Waveforms"], state)
    assert EventCode.DATA_TYPE_ERROR in state.event_queue
    assert state.filesystem.cwd == r"C:\TekScope"


def test_cwd_set_without_path_pushes_missing_parameter(tmp_path):
    state = make_state(tmp_path)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:CWD", False, [], state)
    assert EventCode.MISSING_PARAMETER in state.event_queue


def test_writefile_without_data_pushes_missing_parameter(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:WRITEFILE", False, [r"C:\TekScope\out.wfm"], state)
    assert EventCode.MISSING_PARAMETER in state.event_queue

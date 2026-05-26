import os
import tempfile
import pytest
from scpi.filesystem import FileSystemState, virtual_to_real


@pytest.fixture
def fs(tmp_path):
    state = FileSystemState(cwd=r"C:\TekScope", root=str(tmp_path))
    return state


def test_absolute_path_mapping(fs, tmp_path):
    result = virtual_to_real(r"C:\TekScope\Waveforms", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "Waveforms")
    assert result == expected


def test_absolute_path_drive_d(fs, tmp_path):
    result = virtual_to_real(r"D:\Data\file.txt", fs)
    expected = os.path.join(str(tmp_path), "D", "Data", "file.txt")
    assert result == expected


def test_relative_path_dot_backslash(fs, tmp_path):
    result = virtual_to_real(r".\newfile.txt", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "newfile.txt")
    assert result == expected


def test_relative_path_no_prefix(fs, tmp_path):
    result = virtual_to_real("newfile.txt", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "newfile.txt")
    assert result == expected


def test_forward_slash_separator(fs, tmp_path):
    result = virtual_to_real("C:/TekScope/Waveforms", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "Waveforms")
    assert result == expected


def test_root_of_drive(fs, tmp_path):
    result = virtual_to_real(r"C:\TekScope", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope")
    assert result == expected


def test_cwd_changes_relative_resolution(tmp_path):
    fs = FileSystemState(cwd=r"C:\TekScope\Waveforms", root=str(tmp_path))
    result = virtual_to_real("wfm1.wfm", fs)
    expected = os.path.join(str(tmp_path), "C", "TekScope", "Waveforms", "wfm1.wfm")
    assert result == expected


# --- New tests for Task 8 ---

from scpi.dispatcher import Dispatcher
from scpi.instrument import InstrumentState
from scpi.filesystem import (
    FileSystemState, virtual_to_real,
    register_filesystem_commands, create_initial_structure
)


def make_fs_state(tmp_path):
    return FileSystemState(cwd=r"C:\TekScope", root=str(tmp_path))


def make_state(tmp_path):
    fs = make_fs_state(tmp_path)
    return InstrumentState(filesystem=fs)


def make_dispatcher(state):
    d = Dispatcher()
    register_filesystem_commands(d, state)
    return d


# --- create_initial_structure ---

def test_create_initial_structure(tmp_path):
    fs = make_fs_state(tmp_path)
    create_initial_structure(fs)
    for vpath in [r"C:\TekScope", r"C:\TekScope\Waveforms",
                  r"C:\TekScope\Images", r"C:\TekScope\Settings"]:
        assert os.path.isdir(virtual_to_real(vpath, fs))


# --- CWD ---

def test_cwd_query_returns_default(tmp_path):
    state = make_state(tmp_path)
    d = make_dispatcher(state)
    resp = d.dispatch("FILESYSTEM:CWD", True, [], state)
    assert resp == r'"C:\TekScope"'


def test_cwd_set(tmp_path):
    state = make_state(tmp_path)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:CWD", False, [r"C:\TekScope\Waveforms"], state)
    assert state.filesystem.cwd == r"C:\TekScope\Waveforms"


def test_cwd_query_after_set(tmp_path):
    state = make_state(tmp_path)
    d = make_dispatcher(state)
    d.dispatch("FILESYSTEM:CWD", False, [r"C:\TekScope\Waveforms"], state)
    resp = d.dispatch("FILESYSTEM:CWD", True, [], state)
    assert resp == r'"C:\TekScope\Waveforms"'


# --- DIR? ---

def test_dir_query_empty_dir(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    resp = d.dispatch("FILESYSTEM:DIR", True, [], state)
    # Should include "." and ".." at minimum, and subdirs
    assert '"."' in resp
    assert '".."' in resp


def test_dir_query_lists_files(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    # Create a test file in CWD
    real_cwd = virtual_to_real(state.filesystem.cwd, state.filesystem)
    open(os.path.join(real_cwd, "test.wfm"), 'w').close()
    d = make_dispatcher(state)
    resp = d.dispatch("FILESYSTEM:DIR", True, [], state)
    assert '"test.wfm"' in resp


def test_filesystem_query_alias(tmp_path):
    state = make_state(tmp_path)
    create_initial_structure(state.filesystem)
    d = make_dispatcher(state)
    resp_dir = d.dispatch("FILESYSTEM:DIR", True, [], state)
    resp_alias = d.dispatch("FILESYSTEM", True, [], state)
    assert resp_dir == resp_alias

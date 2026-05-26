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

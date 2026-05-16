"""
Regression test for etingof/pysnmp#363.

A directory named 'pysnmp_mibs' (or any DEFAULT_MISC_MIBS name) present in the
working directory without an __init__.py forms a Python namespace package.
Namespace packages have __file__ == None, which caused os.path.split(None) to
raise TypeError inside ZipMibSource._init().

The fix: detect the namespace-package case via __spec__.submodule_search_locations
and fall through to DirMibSource with the first resolved path.
"""

import os
import sys
import tempfile

import pytest

from pysnmp.smi import builder


def test_namespace_package_pysnmp_mibs_dir_does_not_crash(tmp_path, monkeypatch):
    """
    MibBuilder() must not raise TypeError when a bare 'pysnmp_mibs' directory
    (no __init__.py) exists on sys.path and is importable as a namespace package.
    """
    mibs_dir = tmp_path / "pysnmp_mibs"
    mibs_dir.mkdir()

    # Make it importable as a namespace package from tmp_path
    monkeypatch.syspath_prepend(str(tmp_path))

    # Must not raise TypeError: expected str, bytes or os.PathLike object, not NoneType
    b = builder.MibBuilder()

    # The namespace package directory must appear in the resolved MIB sources
    sources = b.get_mib_sources()
    source_paths = [getattr(s, "_srcName", "") for s in sources]
    assert any(
        os.path.normpath(str(mibs_dir)) == os.path.normpath(p) for p in source_paths
    ), f"Expected {mibs_dir} in MIB sources, got: {source_paths}"


def test_namespace_package_pysnmp_mibs_dir_loads_mibs(tmp_path, monkeypatch):
    """
    After fixing the TypeError, standard MIB symbols must still load correctly
    when a bare 'pysnmp_mibs' directory is on sys.path.
    """
    mibs_dir = tmp_path / "pysnmp_mibs"
    mibs_dir.mkdir()
    monkeypatch.syspath_prepend(str(tmp_path))

    b = builder.MibBuilder()
    (sysDescr,) = b.import_symbols("SNMPv2-MIB", "sysDescr")
    assert sysDescr.name == (1, 3, 6, 1, 2, 1, 1, 1)


def test_normal_package_pysnmp_mibs_still_works(tmp_path, monkeypatch):
    """
    A 'pysnmp_mibs' directory WITH __init__.py (regular package) must continue
    to work as before.
    """
    mibs_dir = tmp_path / "pysnmp_mibs"
    mibs_dir.mkdir()
    (mibs_dir / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))

    b = builder.MibBuilder()
    (sysDescr,) = b.import_symbols("SNMPv2-MIB", "sysDescr")
    assert sysDescr.name == (1, 3, 6, 1, 2, 1, 1, 1)

"""Tests for the start page ``Home.py`` and the license shown on it.

The start page runs from the installed package. CI installs the package
regularly, so these tests check what the built package ships.
"""
from importlib import metadata
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import owp_milp_optimization
from owp_milp_optimization import helpers

PKG_DIR = Path(owp_milp_optimization.__file__).parent


def _not_installed(name):
    raise metadata.PackageNotFoundError(name)


# %% read_license

def test_license_of_installed_package():
    """The installed package ships its license, special characters intact."""
    text = helpers.read_license()
    assert text.startswith('MIT License')
    assert 'Copyright (c) 2024 Malte Fritz and Jonas Freißmann' in text


@pytest.mark.parametrize(
    'folder', ['licenses', ''], ids=['new_backend', 'old_backend']
)
def test_license_from_metadata(tmp_path, monkeypatch, folder):
    """Finds the license in the metadata of new and old build backends.

    New build backends list the file as License-File and store it in a
    "licenses" folder, old ones store it in the metadata folder itself.
    """
    dist_info = tmp_path / 'owp_milp_optimization-1.0.dist-info'
    (dist_info / folder).mkdir(parents=True, exist_ok=True)
    (dist_info / folder / 'LICENSE').write_text('Lizenz ß', encoding='utf-8')
    header = 'License-File: LICENSE\n' if folder else ''
    (dist_info / 'METADATA').write_text(
        'Metadata-Version: 2.1\nName: owp_milp_optimization\n' + header,
        encoding='utf-8'
    )
    monkeypatch.setattr(
        metadata, 'distribution',
        lambda name: metadata.PathDistribution(dist_info)
    )
    assert helpers.read_license() == 'Lizenz ß'


def test_license_from_source_checkout(tmp_path, monkeypatch):
    """Without an installation, it reads the LICENSE of the source checkout."""
    (tmp_path / 'LICENSE').write_text('Lizenz ß', encoding='utf-8')
    module = tmp_path / 'src' / 'owp_milp_optimization' / 'helpers.py'
    monkeypatch.setattr(metadata, 'distribution', _not_installed)
    monkeypatch.setattr(helpers, '__file__', str(module))
    assert helpers.read_license() == 'Lizenz ß'


def test_no_license_found(tmp_path, monkeypatch):
    """Returns None instead of failing if there is no license file at all."""
    module = tmp_path / 'site-packages' / 'owp_milp_optimization' / 'helpers.py'
    monkeypatch.setattr(metadata, 'distribution', _not_installed)
    monkeypatch.setattr(helpers, '__file__', str(module))
    assert helpers.read_license() is None


# %% Start page

def test_home_page_runs_from_installed_package(monkeypatch):
    """The start page runs from the installed package and shows the license."""
    # streamlit run puts the folder of the main script on the import path
    monkeypatch.syspath_prepend(str(PKG_DIR))
    at = AppTest.from_file(str(PKG_DIR / 'Home.py'), default_timeout=60)
    at.run()

    assert not at.exception
    license_boxes = [
        box.value for box in at.success if 'Softwarelizenz' in box.value
    ]
    assert len(license_boxes) == 1
    assert '© 2024 Malte Fritz and Jonas Freißmann' in license_boxes[0]

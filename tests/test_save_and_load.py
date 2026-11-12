"""Tests for saving and loading data in the dashboard.

The dashboard runs from the installed package, whose directory can be
read-only, e.g. in a system-wide installation. Therefore, the pages build
downloads in memory and read uploads from memory instead of using folders in
the package directory. CI installs the package regularly, so the page tests
run the pages of the built package.
"""
import contextlib
import copy
import io
import json
import os
import shutil
import zipfile
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import owp_milp_optimization
from owp_milp_optimization import helpers

PKG_DIR = Path(owp_milp_optimization.__file__).parent
ES_FILES = ['data_input.csv', 'param_opt.json', 'param_units.json']
RESULT_FILES = [
    'Ergebnisse_Zeitreihen.csv',
    'Ergebnisse_Kapazitäten.csv',
    'Ergebnisse_Allgemein.csv',
]
BOM = b'\xef\xbb\xbf'


@pytest.fixture
def energy_system():
    """Input data, optimization and unit parameters of a small system."""
    data = pd.DataFrame(
        {'heat_demand': [10.5, 12.0, 0.0], 'el_spot_price': [80.25, -5.0, 0.0]},
        index=pd.to_datetime(
            ['2024-01-01 00:00', '2024-01-01 01:00', '2024-01-01 02:00']
        ),
    )
    param_opt = {'Solver': 'HiGHS', 'MIPGap': 0.01, 'TimeLimit': 3600}
    param_units = {
        'hp1': {'cap_N': 40.0, 'invest_mode': False},
        'tes1': {'Q_N': 200.0, 'invest_mode': True},
    }
    return data, param_opt, param_units


def _zip_contents(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


# %% Zip archives

def test_zip_files():
    """Text is stored as UTF-8, bytes unchanged, umlauts in names work."""
    data = helpers.zip_files({
        'text.csv': 'a;b\nä;ß\n',
        'Kapazitäten.csv': 'ä'.encode('utf-8-sig'),
    })
    assert _zip_contents(data) == {
        'text.csv': 'a;b\nä;ß\n'.encode('utf-8'),
        'Kapazitäten.csv': BOM + 'ä'.encode('utf-8'),
    }


def test_energy_system_zip_round_trip(energy_system):
    """A saved energy system loads again with the same data."""
    data, param_opt, param_units = energy_system
    archive = helpers.energy_system_to_zip(data, param_opt, param_units)

    assert sorted(_zip_contents(archive)) == ES_FILES
    loaded = helpers.energy_system_from_zip(io.BytesIO(archive))
    pd.testing.assert_frame_equal(loaded[0], data)
    assert loaded[1:] == (param_opt, param_units)


def test_energy_system_from_zip_of_older_versions(tmp_path, energy_system):
    """Energy systems saved by older versions of the dashboard still load.

    These versions wrote the files into a folder and zipped the folder.
    """
    data, param_opt, param_units = energy_system
    folder = tmp_path / 'energysystem'
    folder.mkdir()
    data.to_csv(folder / 'data_input.csv', sep=';')
    for name, params in [
            ('param_opt.json', param_opt), ('param_units.json', param_units)]:
        with open(folder / name, 'w', encoding='utf-8') as file:
            json.dump(params, file, indent=4, sort_keys=True)
    archive = shutil.make_archive(str(folder), 'zip', str(folder))

    loaded = helpers.energy_system_from_zip(archive)
    pd.testing.assert_frame_equal(loaded[0], data)
    assert loaded[1:] == (param_opt, param_units)


# %% Pages

def _package_dir_snapshot():
    """Return all paths in the package directory except bytecode caches."""
    return {
        path.relative_to(PKG_DIR) for path in PKG_DIR.rglob('*')
        if '__pycache__' not in path.parts
    }


@contextlib.contextmanager
def _read_only_package_dir():
    """Remove the write permission of all folders of the package.

    Only POSIX systems refuse to create files in such a folder. On Windows,
    the comparison of the package directory before and after remains.
    """
    if os.name != 'posix':
        yield
        return

    folders = [PKG_DIR, *(p for p in PKG_DIR.rglob('*') if p.is_dir())]
    modes = {folder: folder.stat().st_mode for folder in folders}
    try:
        for folder, mode in modes.items():
            folder.chmod(mode & ~0o222)
        yield
    finally:
        for folder, mode in modes.items():
            folder.chmod(mode)


@contextlib.contextmanager
def _installed_app():
    """Prepare running the pages of the installed package with AppTest.

    Yields a dict, which collects the data offered for download by file name.
    """
    downloads = {}
    download_button = st.download_button

    def recording_download_button(*args, **kwargs):
        data = kwargs['data']
        if hasattr(data, 'read'):
            content = data.read()
            data.seek(0)
            data = content
        downloads[kwargs['file_name']] = data
        return download_button(*args, **kwargs)

    with pytest.MonkeyPatch.context() as mp, _read_only_package_dir():
        # streamlit run puts the folder of the main script on the import path
        mp.syspath_prepend(str(PKG_DIR))
        mp.setattr(st, 'download_button', recording_download_button)
        yield downloads


def _configure_energy_system():
    """Open the energy system page and select all units."""
    at = AppTest.from_file(str(PKG_DIR / 'Home.py'), default_timeout=120)
    at.run()
    at.switch_page('pages/00_Energiesystem.py').run()
    units = at.multiselect(key='units_multiselect')
    units.set_value(list(units.options)).run()
    return at


def _click(at, label):
    [button for button in at.button if label in button.label][0].click().run()


def _session_energy_system(at):
    """Return a copy of the energy system in the session state."""
    return copy.deepcopy((
        at.session_state['data'],
        at.session_state['param_opt'],
        at.session_state['param_units'],
    ))


@pytest.fixture(scope='module')
def user_session():
    """Save the energy system, optimize and export the results.

    The steps run once for all tests of this module, because the optimization
    is the expensive part.
    """
    snapshot = _package_dir_snapshot()
    exceptions = {}
    with _installed_app() as downloads:
        at = _configure_energy_system()
        exceptions['configure'] = list(at.exception)

        data = at.session_state['data'].iloc[:48].copy()
        param_opt = dict(at.session_state['param_opt'])
        param_opt.update({'Solver': 'HiGHS', 'TimeLimit': 30, 'MIPGap': 0.05})
        at.switch_page('pages/01_Optimierung.py')
        at.session_state['data'] = data
        at.session_state['param_opt'] = param_opt
        at.run()
        exceptions['open optimization'] = list(at.exception)

        _click(at, 'Energiesystem speichern')
        exceptions['save energy system'] = list(at.exception)
        energy_system = _session_energy_system(at)

        _click(at, 'Optimierung starten')
        exceptions['optimize'] = list(at.exception)
        at.switch_page('pages/02_Simulationsergebnisse.py').run()
        exceptions['open results'] = list(at.exception)
        _click(at, 'Daten exportieren')
        exceptions['export results'] = list(at.exception)

    return {
        'snapshot': (snapshot, _package_dir_snapshot()),
        'exceptions': exceptions,
        'downloads': downloads,
        'energy_system': energy_system,
    }


def test_pages_run_without_errors(user_session):
    """All steps run, even if the package directory is read-only."""
    assert all(not e for e in user_session['exceptions'].values()), (
        user_session['exceptions']
    )


def test_pages_leave_package_directory_unchanged(user_session):
    """Saving and exporting writes nothing into the package directory."""
    before, after = user_session['snapshot']
    assert after == before


def test_energy_system_download(user_session):
    """The energy system download contains the data of the session."""
    archive = user_session['downloads']['Energiesystem']
    assert sorted(_zip_contents(archive)) == ES_FILES

    data, param_opt, param_units = user_session['energy_system']
    loaded = helpers.energy_system_from_zip(io.BytesIO(archive))
    pd.testing.assert_frame_equal(loaded[0], data, check_freq=False)
    assert loaded[1:] == (param_opt, param_units)


def test_results_download(user_session):
    """The results download contains the three result tables.

    The tables with umlauts start with a BOM, so that Excel detects UTF-8.
    """
    files = _zip_contents(user_session['downloads']['Ergebnisse'])
    assert sorted(files) == sorted(RESULT_FILES)
    assert not files['Ergebnisse_Zeitreihen.csv'].startswith(BOM)
    assert files['Ergebnisse_Kapazitäten.csv'].startswith(BOM)
    assert files['Ergebnisse_Allgemein.csv'].startswith(BOM)
    general = pd.read_csv(
        io.BytesIO(files['Ergebnisse_Allgemein.csv']), sep=';',
        encoding='utf-8-sig'
    )
    assert 'Wärmegestehungskosten' in general.columns


def _upload_energy_system():
    """Upload a saved energy system on the energy system page."""
    snapshot = _package_dir_snapshot()
    with _installed_app():
        at = _configure_energy_system()
        energy_system = _session_energy_system(at)
        archive = helpers.energy_system_to_zip(*energy_system)

        at = AppTest.from_file(str(PKG_DIR / 'Home.py'), default_timeout=120)
        at.run()
        at.switch_page('pages/00_Energiesystem.py').run()
        uploader = [u for u in at.get('file_uploader') if u.key == 'own_es'][0]
        if not hasattr(uploader, 'upload'):
            pytest.skip('AppTest of this Streamlit version cannot upload files')
        uploader.upload('Energiesystem.zip', archive, 'application/zip')
        at.run()
    return at, energy_system, (snapshot, _package_dir_snapshot())


def test_energy_system_upload():
    """An uploaded energy system is read without using the package directory."""
    at, (data, param_opt, param_units), snapshot = _upload_energy_system()

    pd.testing.assert_frame_equal(
        at.session_state['data'], data, check_freq=False
    )
    assert at.session_state['param_opt'] == param_opt
    assert at.session_state['param_units'] == param_units
    before, after = snapshot
    assert after == before


@pytest.mark.xfail(
    reason=(
        'BUG: page 00 maps the unit keys of the uploaded param_units (e.g. '
        '"hp1") with longnames, which only knows the unit types (e.g. "hp"). '
        'Loading a saved energy system therefore raises KeyError.'
    )
)
def test_energy_system_upload_runs_without_error():
    """The energy system page works with an uploaded energy system."""
    at, _, _ = _upload_energy_system()
    assert not at.exception

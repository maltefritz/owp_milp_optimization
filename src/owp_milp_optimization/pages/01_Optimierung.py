import base64
import json
import os
import shutil

import pandas as pd
import streamlit as st
from helpers import footer, get_language, load_icon_base64s, txt
from model import EnergySystem
from streamlit import session_state as ss

st.set_page_config(
    layout='wide',
    page_title=txt('optimization.page_title'),
    page_icon=os.path.join(os.path.dirname(__file__), '..', 'img',  'page_icon_ZNES.png')
    )

@st.dialog(txt('optimization.dialog.save_energy_system'))
def download_energy_system():
    """Temporarely save data and zip it, then let user download zip archive."""
    with st.spinner(txt('optimization.spinner.processing_data')):
        tmppath = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), '..', '_tmp'
            )
        )
        if not os.path.exists(tmppath):
            os.mkdir(tmppath)

        zippath = os.path.join(tmppath, 'energysystem')
        if not os.path.exists(zippath):
            os.mkdir(zippath)

        tspath = os.path.join(zippath, 'data_input.csv')
        ss.data.to_csv(tspath, sep=';')

        optpath = os.path.join(zippath, 'param_opt.json')
        with open(optpath, 'w', encoding='utf-8') as file:
            json.dump(ss.param_opt, file, indent=4, sort_keys=True)

        unitpath = os.path.join(zippath, 'param_units.json')
        with open(unitpath, 'w', encoding='utf-8') as file:
            json.dump(ss.param_units, file, indent=4, sort_keys=True)

        shutil.make_archive(zippath, 'zip', zippath)

    with open(f'{zippath}.zip', 'rb') as file:
        btn = st.download_button(
            label=txt('optimization.download.save_energy_system'),
            data=file,
            file_name='Energiesystem',
            mime='application/zip'
        )

    shutil.rmtree(tmppath)

UNIT_LABEL_KEYS = {
    'hp': 'energy_system.unit.heat_pump',
    'ccet': 'energy_system.unit.combined_cycle',
    'ice': 'energy_system.unit.chp',
    'sol': 'energy_system.unit.solar_thermal',
    'gb': 'energy_system.unit.gas_boiler',
    'eb': 'energy_system.unit.electrode_boiler',
    'exhs': 'energy_system.unit.external_heat_source',
    'tes': 'energy_system.unit.thermal_storage',
}

shortnames = {
    txt(UNIT_LABEL_KEYS['hp']): 'hp',
    txt(UNIT_LABEL_KEYS['ccet']): 'ccet',
    txt(UNIT_LABEL_KEYS['ice']): 'ice',
    txt(UNIT_LABEL_KEYS['sol']): 'sol',
    txt(UNIT_LABEL_KEYS['gb']): 'gb',
    txt(UNIT_LABEL_KEYS['eb']): 'eb',
    txt(UNIT_LABEL_KEYS['exhs']): 'exhs',
    txt(UNIT_LABEL_KEYS['tes']): 'tes',
}
longnames = {
    code: txt(key)
    for code, key in UNIT_LABEL_KEYS.items()
}

# %% MARK: Sidebar
with st.sidebar:
    st.subheader(txt('app.sidebar_title'))

    logo_inno = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_InnoNord_OWP.png'
        )
    st.image(logo_inno, width='stretch')

    logo = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_ZNES_mitUnisV2.svg'
        )
    st.image(logo, width='stretch')

    st.markdown('''---''')

    st.subheader(txt('app.associated_project_partners'))
    logo_bo = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_Boben_Op.svg'
        )
    st.image(logo_bo, width='stretch')

    logo_gp = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_GP_Joule.svg'
        )
    st.image(logo_gp, width='stretch')

    logo_sw = os.path.join(
        os.path.dirname(__file__), '..', 'img',
        'Logo_Kreis_Schleswig-Flensburg.svg'
        )
    st.image(logo_sw, width='stretch')

    logo_sw = os.path.join(
        os.path.dirname(__file__), '..', 'img',
        'Logo_Klimaschutzmanagement.svg'
        )
    st.image(logo_sw, width='stretch')

    logo_sw = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_SW_Flensburg.svg'
        )
    st.image(logo_sw, width='stretch')


# %% Overview
st.header(txt('optimization.overview.header'))

if 'param_units' not in ss:
    st.error(txt('optimization.error.no_parameters'))

    with st.container(border=True):
        st.page_link(
            'pages/00_Energiesystem.py', label=txt('optimization.navigation.configure_energy_system'),
            icon='📝', width='stretch'
            )

    icon_path = os.path.join(os.path.dirname(__file__), '..', 'img', 'icons')
    icon_base64s = load_icon_base64s(icon_path)

    footer(icon_base64s)
    st.stop()

col_es, col_over = st.columns([1, 4], gap='large')

col_es.subheader(txt('optimization.overview.energy_system.subheader'))

topopath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'img', get_language(), 'es_topology_')
    )

col_es.image(f'{topopath}header.png', width='stretch')
for unit in ss.param_units.keys():
    unit = unit.rstrip('0123456789')
    col_es.image(
        f'{topopath+unit}.png', width='stretch'
        )

col_over.subheader(txt('optimization.overview.timeseries.subheader'))

data_overview = ss.data.describe()
data_overview.drop(index=['count', 'std', '25%', '75%'], inplace=True)
data_overview.rename(
    index={
        'mean': txt('common.statistics.mean'), 'min': txt('common.statistics.minimum'),
        '50%': txt('common.statistics.median'), 'max': txt('common.statistics.maximum')
        },
    columns={
        'heat_demand': txt('optimization.overview.timeseries.heat_demand'),
        'el_spot_price': txt('optimization.overview.timeseries.electricity_spot_price'),
        'ef_om': txt('optimization.overview.timeseries.electricity_emission_factor'),
        'gas_price': txt('optimization.overview.timeseries.gas_price'),
        'co2_price': txt('optimization.overview.timeseries.co2_price')
        }, inplace=True
    )

if longnames['sol'] in ss.units:
    data_overview['solar_heat_flow'] *= 1e6
    data_overview.rename(columns={
        'solar_heat_flow': txt('optimization.overview.timeseries.solar_heat_flow')
        }, inplace=True
    )

col_over.dataframe(data_overview.T.style.format('{:.2f}'), width='stretch')

col_over.subheader(txt('optimization.overview.parameters.subheader'))

param_overview = pd.DataFrame.from_dict(
    ss.param_opt, orient='index', columns=[txt('common.value')]
    )
if ss.param_opt['calc_network'] == 'specific':
    param_overview.drop(
        index=[
            'MIPGap', 'TimeLimit', 'heat_price',
            'net_op_cost_fix', 'net_op_cost_var', 'net_inv_total',
            'net_op_cost_fix_total', 'net_op_cost_var_total', 'calc_network'
            ], inplace=True
        )
elif ss.param_opt['calc_network'] == 'total':
    param_overview.drop(
        index=[
            'MIPGap', 'TimeLimit', 'heat_price',
            'net_op_cost_fix', 'net_op_cost_var', 'net_dist', 'net_inv_spez',
            'calc_network', 'net_op_cost_fix_total', 'net_op_cost_var_total'
            ], inplace=True
        )
param_overview.loc['ef_gas'] *= 1000
param_overview.loc['capital_interest'] *= 100
param_overview.rename(
    index={
        'net_inv_spez': txt('optimization.overview.parameter.network_specific_investment'),
        'net_inv_total': txt('optimization.overview.parameter.network_total_investment'),
        'ef_gas': txt('optimization.overview.parameter.gas_emission_factor'),
        'elec_consumer_charges_grid': txt('optimization.overview.parameter.electricity_charges_grid'),
        'elec_consumer_charges_self': txt('optimization.overview.parameter.electricity_charges_self'),
        'energy_tax': txt('optimization.overview.parameter.energy_tax'),
        'vNNE': txt('optimization.overview.parameter.vnne'),
        'capital_interest': txt('optimization.overview.parameter.capital_interest'),
        'lifetime': txt('optimization.overview.parameter.lifetime'),
        'net_dist': txt('optimization.overview.parameter.network_distance')
        }, inplace=True
    )
param_overview[txt('common.value')] = param_overview[txt('common.value')].astype(str)
col_over.dataframe(param_overview, width='stretch')

# %% MARK: Save Data
# _, col_save, col_reset, _ = st.columns([1.05, 1, 1, 2], gap='large')
# col_save, col_reset = col_over.columns([1, 1], gap='large')
col_save, col_dl_es, col_reset = col_over.columns([1, 1, 1], gap='large')
savepath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'save')
    )

if not os.path.exists(savepath):
    os.mkdir(savepath)

download = False
download = col_save.button(
    label=txt('optimization.button.save_input_data'),
    key='download_button', width='stretch'
    )

if download:
    tspath = os.path.join(savepath, 'data_input.csv')
    ss.data.to_csv(tspath, sep=';')

    optpath = os.path.join(savepath, 'param_opt.json')
    with open(optpath, 'w', encoding='utf-8') as file:
        json.dump(ss.param_opt, file, indent=4, sort_keys=True)

    unitpath = os.path.join(savepath, 'param_units.json')
    with open(unitpath, 'w', encoding='utf-8') as file:
        json.dump(ss.param_units, file, indent=4, sort_keys=True)

download_es_btn = col_dl_es.button(
    label=txt('optimization.button.save_energy_system'),
    key='download_es_button_overview',
    width='stretch'
    )
if download_es_btn:
    download_energy_system()

reset_es = col_reset.button(
    label=txt('optimization.button.reset_energy_system'),
    key='reset_button_overview',
    width='stretch'
    )

if reset_es:
    keys = list(ss.keys())
    exceptions = [
        'all_heat_load',
        'eco_data',
        'all_el_prices',
        'all_el_emissions',
        'all_gas_prices',
        'all_co2_prices',
        'all_solar_heat_flow'
        ]
    for key in keys:
        if key not in exceptions:
            ss.pop(key)
    st.switch_page('pages/00_Energiesystem.py')

with st.container(border=True):
    solver_status = None
    opt = st.button(label=txt('optimization.button.start'), width='stretch')
    if opt:
        with st.spinner(txt('optimization.spinner.running')):
            ss.energy_system = EnergySystem(
                ss.data, ss.param_units, ss.param_opt
                )
            st.toast(txt('optimization.toast.energy_system_initialized'), duration=8)

            ss.energy_system.generate_buses()
            ss.energy_system.generate_sources()
            ss.energy_system.generate_sinks()
            ss.energy_system.generate_components()
            st.toast(txt('optimization.toast.model_created'), duration=8)

            st.toast(txt('optimization.toast.started'), duration=8)
            solver_status = ss.energy_system.solve_model()

            if solver_status == 'ok':
                st.toast(txt('optimization.toast.problem_solved'), duration=8)
                ss.energy_system.get_results()
                st.toast(txt('optimization.toast.results_loaded'), duration=8)

                ss.energy_system.calc_econ_params()
                ss.energy_system.calc_ecol_params()
                st.toast(txt('optimization.toast.postprocessing_done'), duration=8)

if solver_status is not None:
    if solver_status == 'infeasable':
        st.error(txt('optimization.error.infeasible'))
    elif solver_status == 'unknown solver error':
        st.error(txt('optimization.error.unknown_solver'))
if opt:
    if solver_status is not None and solver_status == 'ok':
        with st.container(border=True):
            st.page_link(
                'pages/02_Simulationsergebnisse.py',
                label=txt('optimization.navigation.to_results'),
                icon='📊', width='stretch'
                )

# %% MARK: Footer
icon_path = os.path.join(os.path.dirname(__file__), '..', 'img', 'icons')
icon_base64s = load_icon_base64s(icon_path)

footer(icon_base64s)

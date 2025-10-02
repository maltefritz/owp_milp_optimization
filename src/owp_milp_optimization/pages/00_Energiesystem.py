import base64
import datetime as dt
import json
import os
import shutil
import zipfile
from copy import deepcopy

import altair as alt
import pandas as pd
import pyomo.environ as pyo
import streamlit as st
from helpers import footer, format_sep, load_icon_base64s
from pyomo.contrib.appsi.solvers import Highs
from pyomo.opt import check_available_solvers
from streamlit import session_state as ss


# %% MARK: Read Input Data
@st.cache_data
def read_input_data():
    '''Read in input data all at once.'''
    inputpath = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', 'input'
        ))
    all_heat_load = pd.read_csv(
        os.path.join(inputpath, 'heat_load.csv'),
        sep=';', index_col=0, parse_dates=True
        )
    eco_data = pd.read_csv(
        os.path.join(inputpath, 'eco_data.csv'),
        sep=';', index_col=0, parse_dates=True
        )

    return all_heat_load, eco_data


# %% MARK: Parameters
shortnames = {
    'Wärmepumpe': 'hp',
    'Gas- und Dampfkraftwerk': 'ccet',
    'Blockheizkraftwerk': 'ice',
    'Solarthermie': 'sol',
    'Spitzenlastkessel': 'plb',
    'Elektrodenheizkessel': 'eb',
    'Externe Wärmequelle': 'exhs',
    'Wärmespeicher': 'tes'
}
longnames = {
    'hp': 'Wärmepumpe',
    'ccet': 'Gas- und Dampfkraftwerk',
    'ice': 'Blockheizkraftwerk',
    'sol': 'Solarthermie',
    'plb': 'Spitzenlastkessel',
    'eb': 'Elektrodenheizkessel',
    'exhs': 'Externe Wärmequelle',
    'tes': 'Wärmespeicher'
}

if 'eco_data' not in ss:
    ss.all_heat_load, ss.eco_data = read_input_data()

    ss.all_el_prices = ss.eco_data['el_spot_price'].to_frame()
    ss.all_el_emissions = ss.eco_data['ef_om'].to_frame()
    ss.all_gas_prices = ss.eco_data['gas_price'].to_frame()
    ss.all_co2_prices = ss.eco_data['co2_price'].to_frame()
    ss.all_solar_heat_flow = ss.eco_data['solar_heat_flow'].to_frame()

unitpath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'input', 'param_units.json')
    )
with open(unitpath, 'r', encoding='utf-8') as file:
    ss.param_units_all = json.load(file)

optpath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'input', 'param_opt.json')
    )
with open(optpath, 'r', encoding='utf-8') as file:
    ss.param_opt = json.load(file)

unitinputpath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'input', 'unit_inputs.json')
    )
with open(unitinputpath, 'r', encoding='utf-8') as file:
    ss.unit_inputs = json.load(file)

boundinputpath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'input', 'param_bound.json')
    )
with open(boundinputpath, 'r', encoding='utf-8') as file:
    ss.bound_inputs = json.load(file)

tooltippath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'input', 'tooltips.json')
    )
with open(tooltippath, 'r', encoding='utf-8') as file:
    ss.tt = json.load(file)

# %% MARK: Sidebar
with st.sidebar:
    st.subheader('Offene Wärmespeicherplanung')

    logo_inno = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_InnoNord_OWP.png'
        )
    st.image(logo_inno, width='stretch')

    logo = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_ZNES_mitUnisV2.svg'
        )
    st.image(logo, width='stretch')

    st.divider()

    st.subheader('Befragung und Feedback')

    col_qr, _ = st.columns([2, 1])
    link_url = 'https://app.edkimo.com/feedback/sotneblun?utm_source=pwa&utm_medium=fbc-copy'
    image_path = os.path.join(os.path.dirname(__file__), '..', 'img', 'Edkimo_Befragung.png')

    with open(image_path, 'rb') as f:
        data = f.read()
    img_base64 = base64.b64encode(data).decode()

    col_qr.markdown(
        f'<a href="{link_url}" target="_blank">'
        f'<img src="data:image/png;base64,{img_base64}" alt="Edkimo Befragung">'
        f'</a>',
        unsafe_allow_html=True
    )
    col_qr.write('Scannen oder anklicken')
    st.markdown('''---''')

    st.subheader('Assoziierte Projektpartner')
    logo_bo = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_Boben_Op.svg'
        )
    st.image(logo_bo, width='stretch')

    logo_gp = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_GP_Joule.png'
        )
    st.image(logo_gp, width='stretch')

    logo_sw = os.path.join(
        os.path.dirname(__file__), '..', 'img', 'Logo_SW_Flensburg.svg'
        )
    st.image(logo_sw, width='stretch')


tab_heat, tab_net, tab_system, tab_units, tab_supply, tab_misc = st.tabs(
    ['Wärme', 'Netz', 'System', 'Anlagen', 'Versorgung', 'Sonstiges']
)

# %% MARK: Heat Load
with tab_heat:
    st.header('Wärmeversorgungsdaten')

    col_sel, col_vis = st.columns([1, 2], gap='large')

    dataset_name = col_sel.selectbox(
        'Wähle die Wärmelastdaten aus, die im System zu verwenden sind',
        [*ss.all_heat_load.columns, 'Eigene Daten'],
        placeholder='Wärmelastendaten', help=ss.tt['select_heat_load'],
        key='select_heat_load'
    )

    heat_load = pd.DataFrame()
    if dataset_name == 'Eigene Daten':
        heat_load_year = None
        user_file = col_sel.file_uploader(
            'Datensatz einlesen', type=['csv', 'xlsx'],
            help=ss.tt['own_data_heat_load'], key='own_data_heat_load'
            )
        if user_file is None:
            col_sel.info(
                'Bitte fügen Sie eine Datei ein.'
                )
            heat_load = pd.DataFrame({
                    'Date': [pd.Timestamp('2025-01-01')],
                    'heat_demand': [0.0],
                })
        else:
            filename = user_file.name.lower()
            if filename.endswith('csv'):
                heat_load = pd.read_csv(
                    user_file, sep=";", index_col=0, parse_dates=True
                )
            elif filename.endswith('xlsx'):
                heat_load = pd.read_excel(user_file, index_col=0)

    else:
        user_file = None
        heat_load_years = ss.all_heat_load.loc[
            ~ss.all_heat_load[dataset_name].isna(), dataset_name
            ].index.year.unique()
        heat_load_year = col_sel.selectbox(
            'Wähle das Jahr der Wärmelastdaten aus',
            heat_load_years, index=len(heat_load_years)-1,
            placeholder='Betrachtungsjahr'
        )
        yearmask = ss.all_heat_load.index.year == heat_load_year
        heat_load = ss.all_heat_load.loc[
            yearmask, dataset_name
            ].copy().to_frame()

        dates = None
        if dataset_name != 'Eigene Daten':
            precise_dates = col_sel.toggle(
                'Exakten Zeitraum wählen', key='prec_dates_heat_load'
            )
            if precise_dates:
                dates = col_sel.date_input(
                    'Zeitraum auswählen:',
                    value=(
                        dt.date(int(heat_load_year), 3, 28),
                        dt.date(int(heat_load_year), 7, 2)
                        ),
                    min_value=dt.date(int(heat_load_year), 1, 1),
                    max_value=dt.date(int(heat_load_year), 12, 31),
                    format='DD.MM.YYYY', help=ss.tt['date_picker_heat_load'],
                    key='date_picker_heat_load'
                    )
                dates = [
                    dt.datetime(year=d.year, month=d.month, day=d.day) for d in dates
                    ]
                heat_load = heat_load.loc[dates[0]:dates[1], :]

            scale_hl = col_sel.toggle('Daten skalieren', key='scale_hl')
            if scale_hl:
                scale_method_hl = col_sel.selectbox(
                    'Methode', ['Haushalte', 'Faktor', 'Erweitert'],
                    help=ss.tt['scale_method_hl'], key='scale_method_hl'
                    )
                if scale_method_hl == 'Haushalte':
                    if dataset_name == 'Flensburg':
                        base_households = 50000
                        tt_households = ss.tt['scale_households_hl_fl']
                    elif dataset_name == 'Sonderburg':
                        base_households = 13000
                        tt_households = ss.tt['scale_households_hl_so']
                    scale_households_hl = col_sel.number_input(
                        'Anzahl Haushalte', value=base_households,
                        min_value=1, step=100, help=tt_households,
                        key='scale_households_hl'
                        )
                    heat_load[dataset_name] *= scale_households_hl / base_households
                elif scale_method_hl == 'Faktor':
                    scale_factor_hl = col_sel.number_input(
                        'Skalierungsfaktor', value=1.0, step=0.1, min_value=0.0,
                        help=ss.tt['scale_factor_hl'], key='scale_factor_hl'
                        )
                    heat_load[dataset_name] *= scale_factor_hl
                elif scale_method_hl == 'Erweitert':
                    scale_amp_hl = col_sel.number_input(
                        'Stauchungsfaktor', value=1.0, step=0.1, min_value=0.0,
                        help=ss.tt['scale_amp_hl'], key='scale_amp_hl'
                        )
                    scale_off_hl = col_sel.number_input(
                        'Offset', value=1.0, step=0.1, help=ss.tt['scale_off_hl'],
                        key='scale_off_hl'
                        )
                    heat_load_median = heat_load[dataset_name].median()
                    heat_load[dataset_name] = (
                        (heat_load[dataset_name] - heat_load_median) * scale_amp_hl
                        + heat_load_median + scale_off_hl
                        )
                    # negative_mask = heat_load[dataset_name] < 0
                    if (heat_load[dataset_name] < 0).values.any():
                        st.error(
                            'Durch die Skalierung resultiert eine negative '
                            + 'Wärmelast. Bitte den Offset anpassen.'
                            )

    col_vis.subheader('Wärmelastdaten')

    if user_file is not None or dataset_name != 'Eigene Daten':
        heat_load.rename(
            columns={heat_load.columns[0]: 'heat_demand'}, inplace=True
            )
        heat_load.index.names = ['Date']
        heat_load.reset_index(inplace=True)

        col_vis.altair_chart(
            alt.Chart(heat_load).mark_line(color='#EC6707').encode(
                y=alt.Y('heat_demand', title='Stündliche Wärmelast in MWh'),
                x=alt.X('Date', title='Datum')
            ),
            use_container_width=True
        )

    col_sel.subheader('Wärmeerlöse')

    ss.param_opt['heat_price'] = col_sel.number_input(
        'Wärmeerlös in €/MWh', value=ss.param_opt['heat_price'],
        help=ss.tt['heat_revenue'], key='heat_revenue'
        )

    # %% Solarthermie wird anhand der Wärmelastdaten ausgewählt
    solar_heat_flow = ss.all_solar_heat_flow[
        ss.all_solar_heat_flow.index.year == heat_load_year
        ].copy()
    if "precise_dates" not in st.session_state:
        st.session_state["precise_dates"] = False

    if st.session_state["precise_dates"]:
        solar_heat_flow = solar_heat_flow.loc[dates[0]:dates[1], :]
    solar_heat_flow.reset_index(inplace=True)
    solar_heat_flow['solar_heat_flow'] *= 1e6

# %% MARK: Network
with tab_net:
    st.header('Wärmenetz')

    # col_system, col_unit = st.columns([1, 2], gap='large')
    col_spec_mw, col_spec_km, col_abs = st.columns([1, 1, 1], gap='large')

    ss.param_opt['net_dist'] = col_spec_mw.number_input(
        'Netzlänge in km', value=ss.param_opt['net_dist'],
        help=ss.tt['net_dist'], key='net_dist'
    )


    # Invest cost
    col_spec_mw, col_spec_km, col_abs = st.columns([1, 1, 1], gap='large')
    ss.param_opt['net_inv_spez'] = col_spec_mw.number_input(
        'Spez. Investitionskosten in €/MW/m',
        value=ss.param_opt['net_inv_spez'],
        help=ss.tt['net_inv_spez_mw'], key='net_inv_spez_mw'
    )

    net_inv_spec_km = (
        ss.param_opt['net_inv_spez'] * heat_load['heat_demand'].max()
    )
    net_inv_spec_km = format_sep(net_inv_spec_km, dec=0)
    col_spec_km.metric(
        'Spez. Investitionskosten in €/m', value=net_inv_spec_km
    )

    net_inv_abs = (
        ss.param_opt['net_inv_spez']
        * heat_load['heat_demand'].max()
        * ss.param_opt['net_dist'] * 1000
    )
    net_inv_abs = format_sep(net_inv_abs, dec=0)
    col_abs.metric(
        'Gesamte Investitionskosten in €', value=net_inv_abs
    )

    # Fixed operation cost
    col_spec_mw, col_spec_km, col_abs = st.columns([1, 1, 1], gap='large')
    ss.param_opt['net_op_cost_fix'] = col_spec_mw.number_input(
        'Spez. Fixkosten in €/MW/km',
        value=ss.param_opt['net_op_cost_fix'],
        help=ss.tt['net_op_cost_fix_mw'], key='net_op_cost_fix_mw'
    )

    net_fix_spec_km = (
        ss.param_opt['net_op_cost_fix'] * heat_load['heat_demand'].max()
    )
    net_fix_spec_km = format_sep(net_fix_spec_km, dec=0)
    col_spec_km.metric(
        'Spez. Fixkosten in €/km', value=net_fix_spec_km
    )

    net_fix_abs = (
        ss.param_opt['net_op_cost_fix']
        * heat_load['heat_demand'].max()
        * ss.param_opt['net_dist']
    )
    net_fix_abs = format_sep(net_fix_abs, dec=0)
    col_abs.metric(
        'Gesamte Fixkosten in €/a', value=net_fix_abs
    )

    # Variable operation cost
    col_spec_mw, col_spec_km, col_abs = st.columns([1, 1, 1], gap='large')
    ss.param_opt['net_op_cost_var'] = col_spec_mw.number_input(
        'Spez. variable Kosten in €/MWh/km',
        value=ss.param_opt['net_op_cost_var'],
        help=ss.tt['net_op_cost_var_mw'], key='net_op_cost_var_mw'
    )

    net_var_spec_km = (
        ss.param_opt['net_op_cost_var'] * heat_load['heat_demand'].sum()
    )
    net_var_spec_km = format_sep(net_var_spec_km, dec=0)
    col_spec_km.metric(
        'Spez. variable Kosten in €/km', value=net_var_spec_km
    )

    net_var_abs = (
        ss.param_opt['net_op_cost_var']
        * heat_load['heat_demand'].sum()
        * ss.param_opt['net_dist']
    )
    net_var_abs = format_sep(net_var_abs, dec=0)
    col_abs.metric(
        'Gesamte variable Kosten in €', value=net_var_abs
    )

# %% MARK: Energy System
with tab_system:
    st.header('Auswahl des Wärmeversorgungssystem')

    col_system, col_unit = st.columns([1, 2], gap='large')

    # st.elements.utils._shown_default_value_warning = True

    if 'param_units' not in ss:
        ss.param_units = {}
    if 'units_multiselect' not in ss:
        if 'units' in ss:
            ss.units_multiselect = ss.units
        else:
            ss.units_multiselect = []
    if 'units' not in ss:
        ss.units = []

    ss.units = col_unit.multiselect(
        'Wähle die Wärmeversorgungsanlagen aus, die im System verwendet werden '
        + 'können.',
        options=list(shortnames.keys()),
        placeholder='Wärmeversorgungsanlagen',
        key='units_multiselect'
        )

    col_vis_unit, col_nr_unit = col_system.columns([0.8, 0.2])

    topopath = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'img', 'es_topology_')
        )
    col_vis_unit.image(f'{topopath}header.png', width='stretch')
    if 'nr_units' not in ss:
        ss.nr_units = {}
    if ss.units:
        for unit in ss.units:
            col_vis_unit, col_nr_unit = col_system.columns(
                [0.8, 0.2], vertical_alignment='center'
            )
            col_vis_unit.image(
                f'{topopath+shortnames[unit]}.png', width='stretch'
                )

            if unit in ss.nr_units:
                init_nr_units = ss.nr_units[unit]
            else:
                init_nr_units = 1

            ss.nr_units[unit] = col_nr_unit.number_input(
                f'Anzahl {unit}', value=init_nr_units, 
                min_value=1, max_value=99, step=1,
                label_visibility='collapsed', key=f'nr_units{unit}'
            )

        removed_units = [u for u in ss.nr_units.keys() if u not in ss.units]
        for unit_cat in removed_units:
            ss.nr_units.pop(unit_cat, None)
            to_delete = [
                u for u in ss.param_units
                if longnames[u.rstrip('0123456789')] == unit_cat
                ]
            for key in to_delete:
                ss.param_units.pop(key, None)

        for u, params in ss.param_units_all.items():
            if longnames[u] in ss.units:
                for i in range(1, ss.nr_units[longnames[u]]+1):
                    if f'{u}{i}' not in ss.param_units.keys():
                        ss.param_units[f'{u}{i}'] = deepcopy(params)

        for unit_cat in ss.units:
            current_count = ss.nr_units[unit_cat]
            to_delete = [
                u for u in ss.param_units
                if longnames[u.rstrip('0123456789')] == unit_cat
                and int(u[len(u.rstrip('0123456789')):]) > current_count
                ]
            for key in to_delete:
                ss.param_units.pop(key, None)

    st.header('Eigenes Wärmeversorgungssystem laden')

    own_es = False
    esfile = st.file_uploader(
        'Datei auswählen:', type='zip',
        help=ss.tt['own_es'], key='own_es'
    )
    if esfile is not None:
        tmppath = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), '..', '_tmp'
            )
        )
        if not os.path.exists(tmppath):
            os.mkdir(tmppath)

        zippath = os.path.join(tmppath, esfile.name.split('.')[0])
        with zipfile.ZipFile(esfile, 'r') as z:
            z.extractall(zippath)

        tspath = os.path.join(zippath, 'data_input.csv')
        ss.data = pd.read_csv(tspath, sep=';', index_col=0, parse_dates=True)

        optpath = os.path.join(zippath, 'param_opt.json')
        with open(optpath, 'r', encoding='utf-8') as file:
            ss.param_opt = json.load(file)

        unitpath = os.path.join(zippath, 'param_units.json')
        with open(unitpath, 'r', encoding='utf-8') as file:
            ss.param_units = json.load(file)

        ss.units = [longnames[u] for u in ss.param_units.keys()]

        shutil.rmtree(tmppath)
        own_es = True

# %% MARK: Unit Parameters
comb_opt_params = ['cap_max', 'cap_min', 'Q_max', 'Q_min', 'A_max', 'A_min']
disp_opt_params = ['cap_N', 'Q_N', 'A_N']

with tab_units:
    st.header('Parametrisierung der Wärmeversorgungsanlagen')

    placeholder_infeasable = st.empty()

    if ss.param_units:
        ss.param_units = dict(sorted(ss.param_units.items()))

    for unit, unit_params in ss.param_units.items():
        unit_cat = unit.rstrip('0123456789')
        unit_nr = unit[len(unit_cat):]

        with st.expander(f'{longnames[unit_cat]} {unit_nr}'):
            col_tech, col_econ = st.columns(2, gap='large')

            col_tech.subheader('Technische Parameter')
            unit_params['invest_mode'] = col_tech.toggle(
                'Kapazität optimieren', value=unit_params['invest_mode'],
                key=f'toggle_{unit}_invest_mode',
                help=ss.tt.get(f'toggle_invest', None)
            )
            for uinput, uinfo in ss.unit_inputs['Technische Parameter'].items():
                if uinput in unit_params:
                    if unit_params['invest_mode'] and uinput in disp_opt_params:
                        continue
                    if not unit_params['invest_mode'] and uinput in comb_opt_params:
                        continue

                    if uinfo['type'] == 'bool':
                        unit_params[uinput] = col_tech.toggle(
                            uinfo['name'],
                            value=unit_params[uinput],
                            key=f'toggle_{unit}_{uinput}',
                            help=ss.tt.get(f'toggle_{uinput}', None)
                        )
                    else:
                        if uinfo['unit'] == '%':
                            unit_params[uinput] *= 100
                        if uinfo['unit'] == '':
                            label = uinfo['name']
                        else:
                            label = f"{uinfo['name']} in {uinfo['unit']}"
                        unit_params[uinput] = (
                            col_tech.number_input(
                                label,
                                value=float(
                                    unit_params[uinput]
                                    ),
                                min_value=uinfo['min'],
                                max_value=uinfo['max'],
                                step=(uinfo['max']-uinfo['min'])/100,
                                key=f'input_{unit}_{uinput}',
                                help=ss.tt.get(f'input_{uinput}', None)
                                )
                            )
                        if uinfo['unit'] == '%':
                            unit_params[uinput] /= 100

            col_econ.subheader('Ökonomische Parameter')
            for uinput, uinfo in ss.unit_inputs['Ökonomische Parameter'].items():
                if uinput in unit_params:
                    if unit_cat == 'sol':
                        if uinput == 'inv_spez':
                            label = f"{uinfo['name']} in €/m²"
                        elif uinput == 'op_cost_fix':
                            label = f"{uinfo['name']} in €/MWh"
                        else:
                            label = f"{uinfo['name']} in {uinfo['unit']}"
                    elif unit_cat == 'tes':
                        label = f"{uinfo['name']} in €/MWh"
                    else:
                        label = f"{uinfo['name']} in {uinfo['unit']}"

                    tooltip = ss.tt.get(f'input_{uinput}', None)
                    if unit_cat == 'sol' and uinput == 'op_cost_var':
                        tooltip = ss.tt.get(f'input_{uinput}_{unit_cat}', None)

                    if uinfo['unit'] == '%':
                        unit_params[uinput] *= 100
                    unit_params[uinput] = (
                        col_econ.number_input(
                            label,
                            value=float(
                                unit_params[uinput]
                                ),
                            min_value=uinfo['min'],
                            max_value=uinfo['max'],
                            step=(uinfo['max']-uinfo['min'])/100,
                            key=f'input_{unit}_{uinput}',
                            help=tooltip
                            )
                        )
                    if uinfo['unit'] == '%':
                        unit_params[uinput] /= 100

    Q_tot_max = 0
    residual_heat_demand = heat_load.copy()
    for unit, unit_params in ss.param_units.items():
        unit_cat = unit.rstrip('0123456789')
        if unit_params['invest_mode']:
            if unit_cat not in ['sol', 'tes']:
                Q_tot_max += unit_params['cap_max']
            elif unit_cat == 'sol':
                residual_heat_demand['heat_demand'] -= (
                    unit_params['A_max'] * solar_heat_flow['solar_heat_flow']
                    )
            elif unit_cat == 'tes':
                Q_tot_max += unit_params['Q_max'] * unit_params['Q_out_to_cap']
        else:
            if unit_cat not in ['sol', 'tes']:
                Q_tot_max += unit_params['cap_N']
            elif unit_cat == 'sol':
                residual_heat_demand['heat_demand'] -= (
                    unit_params['A_N'] * solar_heat_flow['solar_heat_flow']
                    )
            elif unit_cat == 'tes':
                Q_tot_max += unit_params['Q_N'] * unit_params['Q_out_to_cap']

    if Q_tot_max != 0:
        if residual_heat_demand['heat_demand'].max() > Q_tot_max:
            placeholder_infeasable.error(
                'Die gewählten Wärmeanlagen genügen nicht um den maximalen '
                + 'Wärmebedarf zu decken. Mögliche Ansätze zur Lösung des '
                + 'Problems könnten sein:\n\n'
                + '- Erhöhe die installierte oder maximal zu installierende'
                + ' Leistung der Anlagen\n\n'
                + '- Füge andere Anlagen hinzu oder erhöhe die Anzahl der '
                + 'vorhandenen Anlagen\n\n'
                + '- Füge einen Wärmespeicher hinzu'
                )

# %% MARK: Solar Thermal
# if 'Solarthermie' in ss.units:
with tab_supply:
    if 'Solarthermie' in ss.units:
        with st.expander('Solarthermiedaten'):
            # solar_heat_flow wird bei der heat load berechnet
            st.subheader('Solarthermiedaten')
            st.altair_chart(
                alt.Chart(solar_heat_flow).mark_line(color='#EC6707').encode(
                    y=alt.Y('solar_heat_flow',
                            title='Spezifische Einstrahlung in Wh/m²'),
                    x=alt.X('Date', title='Datum')
                ),
                use_container_width=True
            )
            solar_heat_flow['solar_heat_flow'] *= 1e-6

# %% MARK: Electricity
    el_units = [
        'Wärmepumpe', 'Elektrodenheizkessel', 'Gas- und Dampfkraftwerk',
        'Blockheizkraftwerk'
        ]
    if any(unit in ss.units for unit in el_units):
        with st.expander('Elektrizitätsversorgungsdaten'):
            st.subheader('Elektrizitätsversorgungsdaten')
            col_elp, col_vis_el = st.columns([1, 2], gap='large')

            select_el = col_elp.selectbox(
                'Preisvariante', 
                ['Variabel', 'Konstant', 'Eigene Daten'],
                key='select_el'
            )

            if select_el == 'Variabel':
                el_prices_years = list(ss.all_el_prices.index.year.unique())
                if heat_load_year:
                    el_year_idx = el_prices_years.index(heat_load_year)
                else:
                    el_year_idx = len(el_prices_years) - 1
                el_prices_year = col_elp.selectbox(
                    'Wähle das Jahr der Strompreisdaten aus',
                    el_prices_years, index=el_year_idx,
                    placeholder='Betrachtungsjahr'
                )
                el_prices = ss.all_el_prices[
                    ss.all_el_prices.index.year == el_prices_year
                    ].copy()
                el_em = ss.all_el_emissions[
                    ss.all_el_emissions.index.year == el_prices_year
                    ].copy()

                precise_dates = col_elp.toggle(
                    'Exakten Zeitraum wählen', key='prec_dates_el_prices'
                    )
                if precise_dates:
                    el_dates = col_elp.date_input(
                        'Zeitraum auswählen:',
                        value=dates if dates is not None else (
                            dt.date(int(heat_load_year), 3, 28),
                            dt.date(int(heat_load_year), 7, 2)
                            ),
                        min_value=dt.date(int(heat_load_year), 1, 1),
                        max_value=dt.date(int(heat_load_year), 12, 31),
                        format='DD.MM.YYYY',
                        help=ss.tt['date_picker_el_prices'],
                        key='date_picker_el_prices'
                        )
                    el_dates = [
                        dt.datetime(year=d.year, month=d.month, day=d.day) for d in el_dates
                        ]
                    el_prices = el_prices.loc[el_dates[0]:el_dates[1], :]
                    el_em = el_em.loc[el_dates[0]:el_dates[1], :]

                scale_el = col_elp.toggle('Daten skalieren', key='scale_el')
                if scale_el:
                    scale_method_el = col_elp.selectbox(
                        'Methode', ['Faktor', 'Erweitert'],
                        help=ss.tt['scale_method_el'], key='scale_method_el'
                        )
                    if scale_method_el == 'Faktor':
                        scale_factor_el = col_elp.number_input(
                            'Skalierungsfaktor', value=1.0, step=0.1,
                            min_value=0.0, help=ss.tt['scale_factor_el'],
                            key='scale_factor_el'
                            )
                        el_prices['el_spot_price'] *= scale_factor_el
                    elif scale_method_el == 'Erweitert':
                        scale_amp_el = col_elp.number_input(
                            'Stauchungsfaktor', value=1.0, step=0.1,
                            min_value=0.0, help=ss.tt['scale_amp_el'],
                            key='scale_amp_el'
                            )
                        scale_off_el = col_elp.number_input(
                            'Offset', value=1.0, step=0.1,
                            help=ss.tt['scale_off_el'], key='scale_off_el'
                            )
                        el_prices_median = el_prices['el_spot_price'].median()
                        el_prices['el_spot_price'] = (
                            (el_prices['el_spot_price'] - el_prices_median)
                            * scale_amp_el + el_prices_median + scale_off_el
                            )

                if any(heat_load):
                    nr_steps_hl = len(heat_load.index)
                    nr_steps_el = len(el_prices.index)
                    if nr_steps_hl != nr_steps_el:
                        st.error(
                            'Die Anzahl der Zeitschritte der Wärmelastdaten '
                            + f'({nr_steps_hl}) stimmt nicht mit denen der '
                            + f' Strompreiszeitreihe ({nr_steps_el}) überein. '
                            + 'Bitte die Daten angleichen.'
                            )

            elif select_el == 'Konstant':
                el_prices = ss.all_el_prices.loc[heat_load['Date']]
                el_em = ss.all_el_emissions.loc[heat_load['Date']]

                constant_el_value = col_elp.number_input(
                    'Spotmarktpreis in €/MWh', value=80.00, step=1.00,
                    key='constant_el_value'
                )
                el_prices['el_spot_price'] = constant_el_value

                constant_el_em_value = col_elp.number_input(
                    'Emissionsfaktor Strommix in kg CO₂/MWh', value=55.00,
                    step=1.00, key='constant_el_em_value'
                )
                el_em['ef_om'] = constant_el_em_value

            elif select_el == 'Eigene Daten':
                user_file_el = col_elp.file_uploader(
                    'Datensatz einlesen', type=['csv', 'xlsx'],
                    help=ss.tt['own_data_el'], key='own_data_el'
                    )
                if user_file_el is None:
                    col_elp.info(
                        'Bitte fügen Sie eine Datei ein.'
                        )        
                    el_prices = pd.DataFrame({
                            'Date': [pd.Timestamp('2025-01-01')],
                            'el_spot_price': [0.0],
                        })
                    el_em = pd.DataFrame({
                            'Date': [pd.Timestamp('2025-01-01')],
                            'ef_om': [0.0],
                        })
                else:
                    filename = user_file_el.name.lower()
                    if filename.endswith('csv'):
                        user_file_el = pd.read_csv(
                            user_file_el, sep=';', index_col=0,
                            parse_dates=True
                            )
                    elif filename.endswith('xlsx'):
                        user_file_el = pd.read_excel(user_file_el, index_col=0)
                    el_prices = user_file_el[['el_spot_price']].copy()
                    el_em = user_file_el[['ef_om']].copy()

            col_elp.subheader(
                'Strompreisbestandteile in ct/kWh', help=ss.tt['el_elements']
                )

            if "edited_elp" not in st.session_state:
                st.session_state["edited_elp"] = {
                    k: v for k, v in ss.bound_inputs[
                            str(el_prices_year)
                        ].items()
                }

            st.session_state["edited_elp"] = col_elp.data_editor(
                st.session_state["edited_elp"],
                width="stretch",
                disabled=["index", 0],
                key="el_elements"
            )

            edited_elp = st.session_state["edited_elp"]

            ss.param_opt['elec_consumer_charges_grid'] = round(
                sum(val * 10 for val in edited_elp["Netzbezug"].values()), 2
            )
            ss.param_opt['elec_consumer_charges_self'] = round(
                sum(val * 10 for val in edited_elp["Eigennutzung"].values()), 2
            )

            col_vis_el.subheader('Spotmarkt Strompreise')
            el_prices.reset_index(inplace=True)
            col_vis_el.altair_chart(
                alt.Chart(el_prices).mark_line(color='#00395B').encode(
                    y=alt.Y(
                        'el_spot_price',
                        title='Day-Ahead Spotmarkt Strompreise in €/MWh'
                        ),
                    x=alt.X('Date', title='Datum')
                    ),
                use_container_width=True
                )

            col_vis_el.subheader('Emissionsfaktoren des Strommixes')
            el_em.reset_index(inplace=True)
            col_vis_el.altair_chart(
                alt.Chart(el_em).mark_line(color='#74ADC0').encode(
                    y=alt.Y(
                        'ef_om',
                        title='Emissionsfaktor des Gesamtmix kg/MWh'
                        ),
                    x=alt.X('Date', title='Datum')
                    ),
                use_container_width=True
                )

# %% MARK: Gas & CO₂
    gas_units = [
        'Spitzenlastkessel', 'Gas- und Dampfkraftwerk', 'Blockheizkraftwerk'
        ]
    if any(unit in ss.units for unit in gas_units):
        with st.expander('Gasversorgungsdaten'):
            st.subheader('Gasversorgungsdaten')
            col_gas, col_vis_gas = st.columns([1, 2], gap='large')

            select_gas = col_gas.selectbox(
                'Preisvariante', 
                ['Variabel', 'Konstant', 'Eigene Daten'],
                key='select_gas'
            )

            if select_gas == 'Variabel':
                gas_prices_years = list(ss.all_el_prices.index.year.unique())
                if heat_load_year:
                    gas_year_idx = gas_prices_years.index(heat_load_year)
                else:
                    gas_year_idx = len(gas_prices_years) - 1
                gas_prices_year = col_gas.selectbox(
                    'Wähle das Jahr der Gaspreisdaten aus',
                    gas_prices_years, index=gas_year_idx,
                    placeholder='Betrachtungsjahr'
                )
                gas_prices = ss.all_gas_prices[
                    ss.all_gas_prices.index.year == gas_prices_year
                    ].copy()
                co2_prices = ss.all_co2_prices[
                    ss.all_co2_prices.index.year == gas_prices_year
                    ].copy()
                precise_dates = col_gas.toggle(
                    'Exakten Zeitraum wählen', key='prec_dates_gas_prices'
                    )
                if precise_dates:
                    gas_dates = col_gas.date_input(
                        'Zeitraum auswählen:',
                        value=dates if dates is not None else (
                            dt.date(int(heat_load_year), 3, 28),
                            dt.date(int(heat_load_year), 7, 2)
                            ),
                        min_value=dt.date(int(heat_load_year), 1, 1),
                        max_value=dt.date(int(heat_load_year), 12, 31),
                        format='DD.MM.YYYY',
                        help=ss.tt['date_picker_gas_prices'],
                        key='date_picker_gas_prices'
                        )
                    gas_dates = [
                        dt.datetime(
                            year=d.year, month=d.month, day=d.day
                        ) for d in gas_dates
                    ]
                    gas_prices = gas_prices.loc[gas_dates[0]:gas_dates[1], :]
                    co2_prices = co2_prices.loc[gas_dates[0]:gas_dates[1], :]

                scale_gas = col_gas.toggle('Daten skalieren', key='scale_gas')
                if scale_gas:
                    scale_method_gas = col_gas.selectbox(
                        'Methode', ['Faktor', 'Erweitert'],
                        help=ss.tt['scale_method_gas'], key='scale_method_gas'
                        )
                    if scale_method_gas == 'Faktor':
                        scale_factor_gas = col_gas.number_input(
                            'Skalierungsfaktor', value=1.0, step=0.1,
                            min_value=0.0, help=ss.tt['scale_factor_gas'],
                            key='scale_factor_gas'
                            )
                        gas_prices['gas_price'] *= scale_factor_gas
                    elif scale_method_gas == 'Erweitert':
                        scale_amp_gas = col_gas.number_input(
                            'Stauchungsfaktor', value=1.0, step=0.1,
                            min_value=0.0, help=ss.tt['scale_amp_gas'],
                            key='scale_amp_gas'
                            )
                        scale_off_gas = col_gas.number_input(
                            'Offset', value=1.0, step=0.1,
                            help=ss.tt['scale_amp_gas'], key='scale_off_gas'
                            )
                        gas_prices_median = gas_prices['gas_price'].median()
                        gas_prices['gas_price'] = (
                            (gas_prices['gas_price'] - gas_prices_median)
                            * scale_amp_gas + gas_prices_median + scale_off_gas
                            )

                if any(heat_load):
                    nr_steps_hl = len(heat_load.index)
                    nr_steps_gas = len(gas_prices.index)
                    if nr_steps_hl != nr_steps_gas:
                        st.error(
                            'Die Anzahl der Zeitschritte der Wärmelastdaten '
                            + f'({nr_steps_hl}) stimmt nicht mit denen der '
                            + f' Gaspreiszeitreihe ({nr_steps_gas}) überein. '
                            + 'Bitte die Daten angleichen.'
                            )

            elif select_gas == 'Konstant':
                gas_prices = ss.all_gas_prices.loc[heat_load['Date']]
                co2_prices = ss.all_co2_prices.loc[heat_load['Date']]

                constant_gas_value = col_gas.number_input(
                    'Gaspreis in €/MWh', value=75.00, step=1.00,
                    key='constant_gas_value'
                )
                gas_prices['gas_price'] = constant_gas_value

                constant_co2_value = col_gas.number_input(
                    'CO₂-Zertifikatpreis in €/t CO₂', value=30.00, step=1.00,
                    key='constant_co2_value'
                )
                co2_prices['co2_price'] = constant_co2_value

            elif select_gas == 'Eigene Daten':
                user_file_gas = col_gas.file_uploader(
                    'Datensatz einlesen', type=['csv', 'xlsx'],
                    help=ss.tt['own_data_gas'], key='own_data_gas'
                    )
                if user_file_gas is None:
                    col_gas.info(
                        'Bitte fügen Sie eine Datei ein.'
                        )
                    gas_prices = pd.DataFrame({
                            'Date': [pd.Timestamp('2025-01-01')],
                            'gas_price': [0.0],
                        })
                    co2_prices = pd.DataFrame({
                            'Date': [pd.Timestamp('2025-01-01')],
                            'co2_price': [0.0],
                        })
                else:
                    filename = user_file_gas.name.lower()
                    if filename.endswith('csv'):
                        user_data_gas = pd.read_csv(
                            user_file_gas, sep=';', index_col=0,
                            parse_dates=True
                            )
                    elif filename.endswith('xlsx'):
                        user_data_gas = pd.read_excel(user_file_gas, index_col=0)
                    gas_prices = user_data_gas[['gas_price']].copy()
                    co2_prices = user_data_gas[['co2_price']].copy()

            col_vis_gas.subheader('Gaspreis')
            gas_prices.reset_index(inplace=True)
            col_vis_gas.altair_chart(
                alt.Chart(gas_prices).mark_line(color='#B54036').encode(
                    y=alt.Y(
                        'gas_price', title='Gaspreise in €/MWh'
                        ),
                    x=alt.X('Date', title='Datum')
                    ),
                use_container_width=True
                )

            col_gas.subheader('Emissionsfaktor Gas')
            ss.param_opt['ef_gas'] = col_gas.number_input(
                'Emissionsfatkor in t CO₂/MWh',
                value=ss.param_opt['ef_gas'], help=ss.tt['ef_gas'],
                format='%.4f', key='ef_gas'
                )

            col_vis_gas.subheader('CO₂-Preise')
            co2_prices['co2_price'] *= ss.param_opt['ef_gas']
            co2_prices.reset_index(inplace=True)
            col_vis_gas.altair_chart(
                alt.Chart(co2_prices).mark_line(color='#74ADC0').encode(
                    y=alt.Y(
                        'co2_price',
                        title='CO₂-Preise in €/MWh'
                        ),
                    x=alt.X('Date', title='Datum')
                    ),
                use_container_width=True
                )

# %% MARK: Aggregate Data
if not own_es:
    ss.data = heat_load
    if 'Solarthermie' in ss.units:
        ss.data['solar_heat_flow'] = solar_heat_flow['solar_heat_flow']
    if any(unit in ss.units for unit in el_units):
        ss.data['el_spot_price'] = el_prices['el_spot_price']
        ss.data['ef_om'] = el_em['ef_om']
    if any(unit in ss.units for unit in gas_units):
        ss.data['gas_price'] = gas_prices['gas_price']
        ss.data['co2_price'] = co2_prices['co2_price']
    ss.data.set_index('Date', inplace=True, drop=True)

# %% MARK: Sonstiges
with tab_misc:
    st.header('Sonstige Parameter')

    col_econ, col_opt = st.columns([1, 1], gap='large')

    col_econ.subheader('Wirtschaft')
    ss.param_opt['capital_interest'] *= 100
    ss.param_opt['capital_interest'] = col_econ.number_input(
        'Kapitalzins in %', value=ss.param_opt['capital_interest'],
        help=ss.tt['capital_interest'], key='capital_interest'
        )
    ss.param_opt['capital_interest'] *= 1/100

    ss.param_opt['lifetime'] = col_econ.number_input(
        'Betrachtungsdauer in Jahre', value=ss.param_opt['lifetime'],
        help=ss.tt['capital_interest'], key='lifetime'
        )

    ss.param_opt['energy_tax'] = col_econ.number_input(
        'Energiesteuer in €/MWh', value=ss.param_opt['energy_tax'],
        help=ss.tt['energy_tax'], key='energy_tax'
        )

    ss.param_opt['vNNE'] = col_econ.number_input(
        'Vermiedene Netznutzungsentgelte in €/MWh', value=ss.param_opt['vNNE'],
        help=ss.tt['vNNE'], key='vNNE'
        )


    col_opt.subheader('Optimierung')

    ss.param_opt['Solver'] = col_opt.selectbox(
        'Solver', options=['HiGHS'], help=ss.tt['solver'],
        key='solver'
        )

    if ss.param_opt['Solver'] == 'HiGHS':
        if not Highs().available():
            col_opt.error(
                'Der Solver `HiGHS` ist auf diesem System nicht verfügbar. '
                + 'Bitte verwenden Sie einen anderen Solver.'
                )
    else:
        if not check_available_solvers(ss.param_opt['Solver'].lower()):
            col_opt.error(
                f'Der Solver `{ss.param_opt["Solver"]}` ist auf diesem System '
                + 'nicht verfügbar. Bitte verwenden Sie einen anderen Solver.'
                )

    ss.param_opt['MIPGap'] *= 100
    ss.param_opt['MIPGap'] = col_opt.number_input(
        'MIP Gap in %', value=ss.param_opt['MIPGap'], help=ss.tt['MIPGap'],
        key='MIPGap'
        )
    ss.param_opt['MIPGap'] *= 1/100

    ss.param_opt['TimeLimit'] = None
    timelimit = col_opt.toggle(
        'Simulationsdauer begrenzen', help=ss.tt['ToggleTimeLimit'],
        key='ToggleTimeLimit'
        )
    if timelimit:
        ss.param_opt['TimeLimit'] = col_opt.number_input(
            'Zeitlimit in Minuten', value=ss.param_opt['TimeLimit'],
            key='TimeLimit'
            )
        if ss.param_opt['TimeLimit'] is not None:
            ss.param_opt['TimeLimit'] *= 60

    st.markdown('''---''')

    with st.container(border=True):
        st.page_link(
            'pages/01_Optimierung.py', label='**Zur Optimierung**',
            icon='📝', width='stretch'
            )

# %% MARK: Footer
icon_path = os.path.join(os.path.dirname(__file__), '..', 'img', 'icons')
icon_base64s = load_icon_base64s(icon_path)

footer(icon_base64s)

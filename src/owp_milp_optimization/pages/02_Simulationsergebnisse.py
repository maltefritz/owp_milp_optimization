import base64
import datetime as dt
import io
import json
import os
import re
import shutil

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from helpers import footer, format_sep, get_language, load_icon_base64s, txt
from reporting import generate_html_report
from streamlit import session_state as ss

st.set_page_config(
    layout='wide',
    page_title=txt('results.page_title'),
    page_icon=os.path.join(os.path.dirname(__file__), '..', 'img',  'page_icon_ZNES.png')
    )

@st.dialog(txt('results.dialog.save_results'))
def save_results():
    """Temporarely save results and zip them, then let user download it."""
    with st.spinner(txt('optimization.spinner.processing_data')):
        tmppath = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), '..', '_tmp'
            )
        )
        if not os.path.exists(tmppath):
            os.mkdir(tmppath)

        zippath = os.path.join(tmppath, 'results')
        if not os.path.exists(zippath):
            os.mkdir(zippath)

        tspath = os.path.join(zippath, txt('results.export.filename.timeseries'))
        ss.energy_system.data_all.to_csv(tspath, sep=';')

        cappath = os.path.join(zippath, txt('results.export.filename.capacities'))
        ss.overview_caps.to_csv(cappath, sep=';', encoding='utf-8-sig')

        kpdf = pd.DataFrame.from_dict(
            {k: [v] for k, v in ss.energy_system.key_params.items()}
        )
        kprename = {
            'op_cost_total': txt('results.export.operating_costs'),
            'invest_total': txt('results.export.investment_costs'),
            'cost_gas': txt('results.export.gas_costs'),
            'cost_el_grid': txt('results.export.electricity_costs_grid'),
            'cost_el_internal': txt('results.export.electricity_costs_internal'),
            'cost_el': txt('results.export.electricity_costs_total'),
            'cost_total': txt('results.export.total_costs'),
            'revenues_spotmarket': txt('results.export.electricity_revenues'),
            'revenues_heat': txt('results.export.heat_revenues'),
            'revenues_total': txt('results.export.total_revenues'),
            'balance_total': txt('results.export.total_balance'),
            'LCOH': txt('results.export.lcoh'),
            'total_heat_demand': txt('results.export.total_heat_demand'),
            'Emissions OM (Gas)': txt('results.export.emissions_gas'),
            'Emissions OM (Electricity)': txt('results.export.emissions_electricity'),
            'Emissions OM (Spotmarket)': txt('results.export.emission_credits_electricity_feed_in'),
            'Total Emissions OM': txt('results.export.total_emissions')
        }
        kpdf.rename(columns=kprename, inplace=True)

        kppath = os.path.join(zippath, txt('results.export.filename.general'))
        kpdf.to_csv(kppath, sep=';', encoding='utf-8-sig', index=False)

        shutil.make_archive(zippath, 'zip', zippath)

    with open(f'{zippath}.zip', 'rb') as file:
        btn = st.download_button(
            label=txt('results.download.save_results'),
            data=file,
            file_name=txt('results.download.results_file_name'),
            mime='application/zip'
        )

    shutil.rmtree(tmppath)


@st.dialog(txt('results.dialog.download_report', _language='de'))
def download_report():
    """Generate and download HTML report."""
    with st.spinner(txt('results.spinner.generating_report')):
        try:
            # Get image path
            img_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', 'img', get_language())
            )
            
            # Generate HTML report
            html_content = generate_html_report(
                energy_system=ss.energy_system,
                overview_caps=ss.overview_caps,
                param_units=ss.param_units,
                param_opt=ss.param_opt,
                img_path=img_path,
            )
            
            # Create download button
            timestamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label=txt('results.download.report'),
                data=html_content.encode('utf-8'),
                file_name=f'{txt("results.download.report_file_prefix")}{timestamp}.html',
                mime='text/html',
                key='report_download_btn'
            )
            
            st.success(txt('results.success.report_generated'))
            
        except Exception as e:
            st.error(txt('results.error.report_generation', error=str(e)))


# %% MARK: Parameters
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

colors = {
    txt(UNIT_LABEL_KEYS['hp']): '#B54036',
    txt(UNIT_LABEL_KEYS['ccet']): '#00395B',
    txt(UNIT_LABEL_KEYS['ice']): '#00395B',
    txt(UNIT_LABEL_KEYS['gb']): '#EC6707',
    txt(UNIT_LABEL_KEYS['sol']): '#EC6707',
    txt('results.storage.flow_in'): 'slategrey',
    txt('results.storage.flow_out'): 'dimgrey',
    txt('results.common.heat_demand'): '#31333f',
    txt(UNIT_LABEL_KEYS['eb']): '#EC6707',
    txt(UNIT_LABEL_KEYS['exhs']): '#74ADC0'
}

tooltippath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'input', 'tooltips.json')
    )
with open(tooltippath, 'r', encoding='utf-8') as file:
    ss.tt = json.load(file)

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

    st.markdown("""---""")

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

# %% MARK: Main Window
if 'energy_system' not in ss:
    st.header(txt('results.page_title'))
    st.error(txt('results.error.no_results'))

    with st.container(border=True):
        st.page_link(
            'pages/01_Optimierung.py', label=txt('energy_system.navigation.to_optimization'),
            icon='📝', width='stretch'
            )

    icon_path = os.path.join(os.path.dirname(__file__), '..', 'img', 'icons')
    icon_base64s = load_icon_base64s(icon_path)

    footer(icon_base64s)
    st.stop()

tes_used = any(
    [u.rstrip('0123456789') == 'tes' for u in ss.param_units.keys()]
    )
chp_used = (
    any([u.rstrip('0123456789') == 'ice' for u in ss.param_units.keys()])
    or any([u.rstrip('0123456789') == 'ccet' for u in ss.param_units.keys()])
    )


if chp_used:
    if tes_used:
        tab_ov, tab_unit, tab_el, tab_tes, tab_pro = st.tabs([
            txt('results.tabs.overview'),
            txt('results.tabs.unit_commitment'),
            txt('results.tabs.electricity_production'),
            txt('results.tabs.storage_content'),
            txt('results.tabs.advanced')
            ]
            )
    else:
        tab_ov, tab_unit, tab_el, tab_pro = st.tabs(
            [
                txt('results.tabs.overview'),
                txt('results.tabs.unit_commitment'),
                txt('results.tabs.electricity_production'),
                txt('results.tabs.advanced')
            ]
            )
else:
    if tes_used:
        tab_ov, tab_unit, tab_tes, tab_pro = st.tabs(
            [
                txt('results.tabs.overview'),
                txt('results.tabs.unit_commitment'),
                txt('results.tabs.storage_content'),
                txt('results.tabs.advanced')
            ]
            )
    else:
        tab_ov, tab_unit, tab_pro = st.tabs(
            [
                txt('results.tabs.overview'),
                txt('results.tabs.unit_commitment'),
                txt('results.tabs.advanced')
            ]
            )

# %% MARK: Overview
with tab_ov:
    st.markdown(
        txt('results.overview.description'),
        unsafe_allow_html=True
    )
    with st.expander(txt('results.overview.design.expander'), expanded=True):
        col_cap, col_sum = st.columns([3, 2], gap='large')

        col_cap.subheader(
            txt('results.overview.optimized_capacities.subheader'), help=ss.tt['results_design']
            )
        col_cap1, col_cap2 = col_cap.columns([2, 3], gap='large')

        topopath = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), '..', 'img', get_language(), 'es_topology_'
                )
            )
        col_cap1.image(f'{topopath}header.png', width='stretch')

        for unit in ss.param_units.keys():
            if ss.energy_system.data_caps.loc[0, f'cap_{unit}'] > 0:
                unit_cat = unit.rstrip('0123456789')

                col_cap1.image(
                    f'{topopath+unit_cat}.png', width='stretch'
                    )

        ss.overview_caps = ss.energy_system.data_caps.copy()
        if tes_used:
            drop_cols = []
            for col in ss.overview_caps.columns:
                if 'cap_in_tes' in col or 'cap_out_tes' in col:
                    drop_cols.append(col)
            ss.overview_caps.drop(columns=drop_cols, inplace=True)
        renamedict = {}
        for col in ss.overview_caps.columns:
            ucat = col.split('_')[-1].rstrip('0123456789')
            unr = col.split('_')[-1][len(ucat):]
            if 'tes' in col:
                renamedict[col] = f'{longnames[ucat]} {unr} (MWh)'
            elif 'sol' in col:
                renamedict[col] = f'{longnames[ucat]} {unr} (m²)'
            else:
                renamedict[col] = f'{longnames[ucat]} {unr} (MW)'

        ss.overview_caps.rename(columns=renamedict, inplace=True)
        ss.overview_caps.rename(index={0: txt('results.overview.capacity.row_label')}, inplace=True)
        ss.overview_caps = ss.overview_caps.apply(lambda x: round(x, 1))

        col_cap2.dataframe(ss.overview_caps.T, width='stretch')

        col_sum.subheader(
            txt('results.overview.heat_production.subheader'), help=ss.tt['results_heat_production']
            )
        qsum = pd.DataFrame(columns=['unit', 'qsum'])
        idx = 0
        for unit in ss.param_units.keys():
            ucat = unit.rstrip('0123456789')
            unr = unit[len(ucat):]
            if ucat == 'tes':
                tl = {'in': txt('results.storage.charge_label'), 'out': txt('results.storage.discharge_label')}
                for var in ['in', 'out']:
                    unit_col = f'Q_{var}_{unit}'
                    qsum.loc[idx, 'unit'] = (
                        f'{longnames[ucat]} {unr} {tl[var]}'
                        )
                    qsum.loc[idx, 'qsum'] = (
                        ss.energy_system.data_all[unit_col].sum()
                        )
                    idx += 1
            else:
                if (ucat == 'hp') or (ucat == 'tes'):
                    unit_col = f'Q_out_{unit}'
                else:
                    unit_col = f'Q_{unit}'
                qsum.loc[idx, 'unit'] = f'{longnames[ucat]} {unr}'
                qsum.loc[idx, 'qsum'] = ss.energy_system.data_all[unit_col].sum()
                idx += 1

        col_sum.altair_chart(
            alt.Chart(qsum).mark_bar(color='#B54036').encode(
                y=alt.Y('unit', title=None, axis=alt.Axis(labelLimit=300)),
                x=alt.X('qsum', title=txt('results.chart.total_heat_supply_mwh'))
                ),
            width='stretch'
            )

    with st.expander(txt('results.overview.economic.expander')):
        st.subheader(txt('results.overview.economic.subheader'))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            txt('results.metric.lcoh_generation'),
            format_sep(ss.energy_system.key_params['LCOH']),
            border=True, help=ss.tt['lcoh_heat']
            )
        col1.metric(
            txt('results.metric.lcoh_including_network'),
            format_sep(ss.energy_system.key_params['LCOH_incl_net']),
            border=True, help=ss.tt['lcoh_incl_net']
            )
        col2.metric(
            txt('results.metric.heat_revenues_eur'),
            format_sep(ss.energy_system.key_params['revenues_heat']),
            border=True, help=ss.tt['rev_heat']
            )
        col2.metric(
            txt('results.metric.electricity_revenues_eur'),
            format_sep(ss.energy_system.key_params['revenues_spotmarket']),
            border=True, help=ss.tt['rev_el']
            )
        col3.metric(
            txt('results.metric.electricity_costs_eur'),
            format_sep(ss.energy_system.key_params['cost_el']),
            border=True, help=ss.tt['cost_el']
            )
        col3.metric(
            txt('results.metric.gas_costs_eur'),
            format_sep(ss.energy_system.key_params['cost_gas']),
            border=True, help=ss.tt['cost_gas']
            )
        col4.metric(
            txt('results.metric.unit_costs_total'),
            format_sep(ss.energy_system.cost_df.loc[[
                'invest', 'op_cost_fix', 'op_cost_var'
            ]].sum().sum()),
            border=True, help=ss.tt['cost_units']
            )
        col4.metric(
            txt('results.metric.network_costs_total'),
            format_sep(
                ss.energy_system.key_params['invest_net_total']
                + ss.energy_system.key_params['cost_net_fix_total']
                + ss.energy_system.key_params['cost_net_var_total']
            ),
            border=True, help=ss.tt['cost_units']
            )

        unit_cost = ss.energy_system.cost_df.copy()
        unit_cost.loc['invest', txt('energy_system.network.header')] = (
            ss.energy_system.key_params['invest_net_total']
        )
        unit_cost.loc['op_cost_fix', txt('energy_system.network.header')] = (
            ss.energy_system.key_params['cost_net_fix_total']
        )
        unit_cost.loc['op_cost_var', txt('energy_system.network.header')] = (
            ss.energy_system.key_params['cost_net_var_total']
        )
        unit_cost.loc['op_cost', txt('energy_system.network.header')] = (
            ss.energy_system.key_params['cost_net_fix_total']
            + ss.energy_system.key_params['cost_net_var_total']
        )

        renamedict = {}
        for unit in ss.param_units.keys():
            ucat = unit.rstrip('0123456789')
            unr = unit[len(ucat):]
            renamedict[unit] = f'{longnames[ucat]} {unr}'
        unit_cost.rename(columns=renamedict, inplace=True)
        unit_cost.rename(
            index={
                'invest': txt('results.costs.investment'),
                'op_cost_var': txt('results.costs.variable_operating'),
                'op_cost_fix': txt('results.costs.fixed_operating'),
                'op_cost': txt('results.costs.total_operating')
                },
            inplace=True
            )

        unit_cost.drop(txt('results.costs.total_operating'), axis=0, inplace=True)
        unit_cost = unit_cost.map(format_sep)

        st.dataframe(unit_cost, width='stretch')

    with st.expander(txt('results.overview.ecological.expander')):
    # st.subheader('Ökologische Kennzahlen', help=ss.tt['results_ecol'])
        met1, met2, met3, met4= st.columns([1, 1, 1, 1])
        met1.metric(
            txt('results.metric.total_emissions_t'),
            format_sep(ss.energy_system.key_params['Total Emissions OM']/1e3, 1),
            border=True, help=ss.tt['em_ges']
            )
        met2.metric(
            txt('results.metric.gas_emissions_t'),
            format_sep(ss.energy_system.key_params['Emissions OM (Gas)']/1e3, 1),
            border=True, help=ss.tt['em_gas']
            )
        met3.metric(
            txt('results.metric.electricity_emissions_t'),
            format_sep(ss.energy_system.key_params['Emissions OM (Electricity)']/1e3, 1),
            border=True, help=ss.tt['em_el']
            )

        met4.metric(
            txt('results.metric.electricity_credit_emissions_t'),
            format_sep(ss.energy_system.key_params['Emissions OM (Spotmarket)']/1e3, 1),
            border=True, help=ss.tt['em_spot']
            )

    with st.container(border=True):

        col_left, col_mid, col_right = st.columns([1, 1, 1])
        reset_es = col_left.button(
            label=txt('results.button.reset_energy_system'),
            key='reset_button_results',
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

        report_btn = col_mid.button(
            label=txt('results.button.download_report'),
            key='report_download_button',
            width='stretch'
            )
        if report_btn:
            download_report()

        save_results_btn = col_right.button(
            label=txt('results.button.export_data'),
            width='stretch'
            )
        if save_results_btn:
            save_results()

# %% MARK: Unit Commitment
with tab_unit:
    st.markdown(
        txt('results.unit_commitment.description'),
        unsafe_allow_html=True
    )
    col_sel, col_unit = st.columns([1, 2], gap='large')

    col_unit.subheader(
        txt('results.unit_commitment.sorted_duration_curves.subheader'), help=ss.tt['oadl']
        )

    heatprod = pd.DataFrame()
    for col in ss.energy_system.data_all.columns:
        if 'Q_' in col and ss.energy_system.data_all[col].sum() > 0:
            this_unit = None
            for unit in ss.param_units.keys():
                if unit in col:
                    this_unit = unit
                    this_unit_cat = this_unit.rstrip('0123456789')
                    this_unit_nr = this_unit[len(this_unit_cat):]
            if this_unit is None:
                collabel = txt('results.common.heat_demand')
            elif this_unit.rstrip('0123456789') == 'tes':
                if '_in' in col:
                    collabel = f"{longnames[this_unit_cat]} {this_unit_nr} {txt('results.storage.charge_label')}"
                elif '_out' in col:
                    collabel = f"{longnames[this_unit_cat]} {this_unit_nr} {txt('results.storage.discharge_label')}"
            else:
                collabel = f'{longnames[this_unit_cat]} {this_unit_nr}'
            heatprod[collabel] = ss.energy_system.data_all[col].copy()

    selection = col_sel.multiselect(
        txt('results.unit_commitment.select_units.label'),
        list(heatprod.columns),
        default=list(heatprod.columns),
        placeholder=txt('energy_system.system.units.placeholder')
        )

    dates = col_sel.date_input(
        txt('common.select_period'),
        value=(
            ss.energy_system.data_all.index[0],
            ss.energy_system.data_all.index[-1]
            ),
        min_value=ss.energy_system.data_all.index[0],
        max_value=ss.energy_system.data_all.index[-1],
        format='DD.MM.YYYY', key='date_picker_heat_production'
        )
    dates = [
        dt.datetime(year=d.year, month=d.month, day=d.day) for d in dates
        ]
    # Avoid error while only one date is picked
    if len(dates) == 1:
        dates.append(dates[0] + dt.timedelta(days=1))

    heatprod = heatprod.loc[dates[0]:dates[1], :]

    agg_results = col_sel.toggle(
        txt('results.aggregation.toggle'),
        help=ss.tt['toggle_agg_results'],
        key='toggle_agg_results'
    )

    agg_period_options = {
        'hourly': {
            'label': txt('results.aggregation.period.hourly'),
            'chart_label': txt('results.aggregation.period_label.hourly'),
            'freq': 'h',
        },
        'daily': {
            'label': txt('results.aggregation.period.daily'),
            'chart_label': txt('results.aggregation.period_label.daily'),
            'freq': 'd',
        },
        'weekly': {
            'label': txt('results.aggregation.period.weekly'),
            'chart_label': txt('results.aggregation.period_label.weekly'),
            'freq': 'W',
        },
        'monthly': {
            'label': txt('results.aggregation.period.monthly'),
            'chart_label': txt('results.aggregation.period_label.monthly'),
            'freq': 'ME',
        },
        'quarterly': {
            'label': txt('results.aggregation.period.quarterly'),
            'chart_label': txt('results.aggregation.period_label.quarterly'),
            'freq': 'QE',
        },
    }

    if agg_results:
        agg_period_key = col_sel.selectbox(
            txt('results.aggregation.period.label'),
            options=list(agg_period_options.keys()),
            format_func=lambda key: agg_period_options[key]['label'],
            key='select_agg_time_span_dispatch'
        )

        agg_period = agg_period_options[agg_period_key]['freq']
        agg_period_label = agg_period_options[agg_period_key]['chart_label']

        agg_method_options = {
            'mean': txt('common.statistics.mean'),
            'sum': txt('common.sum'),
        }

        agg_method_key = col_sel.selectbox(
            txt('results.aggregation.method.label'),
            options=list(agg_method_options.keys()),
            format_func=lambda key: agg_method_options[key],
            help=ss.tt['agg_method'],
            key='agg_method_dispatch'
        )

        if agg_method_key == 'mean':
            heatprod = heatprod.resample(agg_period).mean()
        elif agg_method_key == 'sum':
            heatprod = heatprod.resample(agg_period).sum()

    else:
        agg_period = 'h'
        agg_period_label = agg_period_options['hourly']['chart_label']

    duration_col = 'duration_rank'
    supply_unit_col = 'supply_unit'

    heatprod_sorted = pd.DataFrame(
        np.sort(heatprod.values, axis=0)[::-1],
        columns=heatprod.columns
    )
    heatprod_sorted.index.names = [duration_col]
    heatprod_sorted.reset_index(inplace=True)

    hprod_sorted_melt = heatprod_sorted[[duration_col] + selection].melt(duration_col)
    hprod_sorted_melt.rename(
        columns={'variable': supply_unit_col},
        inplace=True
    )

    ylabel = txt(
        'results.chart.heat_production_mwh',
        period=agg_period_label
    )

    col_unit.altair_chart(
        alt.Chart(hprod_sorted_melt).mark_line().encode(
            y=alt.Y('value', title=ylabel),
            x=alt.X(duration_col, title=txt('results.chart.count_axis')),
            color=alt.Color(supply_unit_col).scale(
                domain=selection,
                range=[colors[re.sub(r'\s\d', '', s)] for s in selection]
            )
        ),
        width='stretch'
    )

    col_unit.subheader(txt('results.unit_commitment.actual_dispatch.subheader'), help=ss.tt['adl'])

    if tes_used:
        for col in heatprod.columns:
            if txt('energy_system.unit.thermal_storage') in col and txt('results.storage.charge_label') in col:
                heatprod[col] *= -1
    # heatprod.drop('Wärmebedarf', axis=1, inplace=True)
    heatprod.index.names = ['Date']
    heatprod.reset_index(inplace=True)

    if agg_results and txt('results.common.heat_demand') in selection:
        selection.remove(txt('results.common.heat_demand'))

    hprod_melt = heatprod[['Date'] + selection].melt('Date')
    hprod_melt.rename(
        columns={'variable': supply_unit_col},
        inplace=True
    )

    if not agg_results:
        col_unit.altair_chart(
            alt.Chart(hprod_melt).mark_line().encode(
                y=alt.Y('value', title=ylabel),
                x=alt.X('Date', title=txt('common.date')),
                color=alt.Color(supply_unit_col).scale(
                    domain=selection,
                    range=[colors[re.sub(r'\s\d', '', s)] for s in selection]
                )
            ),
            width='stretch'
        )
    else:
        time_units = {
            'h': 'yearmonthdatehours(Date):O',
            'd': 'yearmonthdate(Date):O',
            'W': 'yearweek(Date):O',
            'ME': 'yearmonth(Date):O',
            'QE': 'yearquarter(Date):O'
        }
        col_unit.altair_chart(
            alt.Chart(hprod_melt).mark_bar().encode(
                y=alt.Y('value', title=ylabel),
                x=alt.X(time_units[agg_period], title=txt('common.date')),
                color=alt.Color(supply_unit_col).scale(
                    domain=selection,
                    range=[colors[re.sub(r'\s\d', '', s)] for s in selection]
                )
            ),
            width='stretch'
        )

# %% MARK: Electricity Production
if chp_used:
    with tab_el:
        st.markdown(
            txt('results.electricity_production.description'),
            unsafe_allow_html=True
        )
        col_sel, col_el = st.columns([1, 2], gap='large')

        dates = col_sel.date_input(
            txt('common.select_period'),
            value=(
                ss.energy_system.data_all.index[0],
                ss.energy_system.data_all.index[-1]
                ),
            min_value=ss.energy_system.data_all.index[0],
            max_value=ss.energy_system.data_all.index[-1],
            format='DD.MM.YYYY', key='date_picker_el_production'
            )
        dates = [
            dt.datetime(year=d.year, month=d.month, day=d.day) for d in dates
            ]
        # Avoid error while only one date is picked
        if len(dates) == 1:
            dates.append(dates[0] + dt.timedelta(days=1))

        elprod = pd.DataFrame(
            columns=['P_spotmarket', 'P_internal', 'el_spot_price']
            )

        elprod['P_spotmarket'] = ss.energy_system.data_all.loc[
            dates[0]:dates[1], 'P_spotmarket'
            ]
        elprod['P_internal'] = ss.energy_system.data_all.loc[
            dates[0]:dates[1], 'P_internal'
            ]
        elprod['el_spot_price'] = ss.data['el_spot_price']

        elprod.index.names = ['Date']
        elprod.reset_index(inplace=True)

        agg_results = col_sel.toggle(
                txt('results.aggregation.toggle'), help=ss.tt['toggle_agg_results'],
                key='toggle_agg_results_el'
            )
        if agg_results:
            agg_periods = {
                txt('results.aggregation.period.hourly'): 'h',
                txt('results.aggregation.period.daily'): 'd',
                txt('results.aggregation.period.weekly'): 'W',
                txt('results.aggregation.period.monthly'): 'ME',
                txt('results.aggregation.period.quarterly'): 'QE'
            }
            agg_period_name = col_sel.selectbox(
                txt('results.aggregation.period.label'),
                options=list(agg_periods.keys()),
                key='select_agg_time_span_el'
            )
            agg_period = agg_periods[agg_period_name]

            agg_method = col_sel.selectbox(
                txt('results.aggregation.method.label'), options=[txt('common.statistics.mean'), txt('common.sum')],
                help=ss.tt['agg_method'], key='agg_method_el'
            )
        else:
            agg_period_name = txt('results.aggregation.period.hourly')

        if agg_results:
            elprod.set_index('Date', inplace=True)
            if agg_method == txt('common.statistics.mean'):
                elprod = elprod.resample(agg_period).mean().reset_index()
            elif agg_method == txt('common.sum'):
                elprod = elprod.resample(agg_period).sum().reset_index()

        elprod_sorted = pd.DataFrame(
            np.sort(elprod.values, axis=0)[::-1], columns=elprod.columns
            )
        elprod_sorted.index.names = ['Stunde']
        elprod_sorted.reset_index(inplace=True)

        col_sel.subheader(txt('results.common.metrics'))
        col_sel.metric(
            txt('results.metric.electricity_revenues_eur'),
            format_sep(ss.energy_system.key_params['revenues_spotmarket'], 2),
            border=True, help=ss.tt['rev_el']
        )
        col_sel.metric(
            txt('results.metric.electricity_costs_eur'),
            format_sep(ss.energy_system.key_params['cost_el'], 2),
            border=True, help=ss.tt['cost_el']
        )
        col_sel.metric(
            txt('results.metric.electricity_costs_grid_eur'),
            format_sep(ss.energy_system.key_params['cost_el_grid'], 2),
            border=True, help=ss.tt['cost_el_int']
        )
        col_sel.metric(
            txt('results.metric.electricity_costs_internal_eur'),
            format_sep(ss.energy_system.key_params['cost_el_internal'], 2),
            border=True, help=ss.tt['cost_el_ext']
        )
        col_sel.metric(
            txt('results.metric.electricity_production_spotmarket_mwh'),
            format_sep(elprod['P_spotmarket'].sum(), 1),
            border=True, help=ss.tt['el_ext']
        )
        col_sel.metric(
            txt('results.metric.electricity_production_internal_mwh'),
            format_sep(elprod['P_internal'].sum(), 1),
            border=True, help=ss.tt['el_int']
        )

        col_el.subheader(txt('results.electricity_production.feed_in.subheader'))
        col_el.altair_chart(
            alt.Chart(elprod).mark_line(color='#00395B').encode(
                y=alt.Y(
                    'P_spotmarket',
                    title=txt('results.electricity_production.feed_in.chart_title')
                    ),
                x=alt.X('Date', title=txt('common.date'))
            ),
            width='stretch'
            )

        col_el.subheader(txt('results.electricity_production.internal_use.subheader'))
        col_el.altair_chart(
            alt.Chart(elprod).mark_line(color='#74ADC0').encode(
                y=alt.Y(
                    'P_internal',
                    title=txt('results.electricity_production.internal_use.chart_title')
                    ),
                x=alt.X('Date', title=txt('common.date'))
            ),
            width='stretch'
            )

        col_el.subheader(txt('results.electricity_production.spot_prices.subheader'))
        col_el.altair_chart(
            alt.Chart(elprod).mark_line(color='#00395B').encode(
                y=alt.Y('el_spot_price', title=txt('results.electricity_production.spot_prices.chart_title')),
                x=alt.X('Date', title=txt('common.date'))
            ),
            width='stretch'
            )

# %% MARK: TES Content
if tes_used:
    with tab_tes:
        st.markdown(
            txt('results.storage.description'),
            unsafe_allow_html=True
        )
        st.subheader(txt('results.storage.content.subheader'))

        col_sel, col_tes = st.columns([1, 2], gap='large')

        dates = col_sel.date_input(
            txt('common.select_period'),
            value=(
                ss.energy_system.data_all.index[0],
                ss.energy_system.data_all.index[-1]
                ),
            min_value=ss.energy_system.data_all.index[0],
            max_value=ss.energy_system.data_all.index[-1],
            format='DD.MM.YYYY', key='date_picker_storage_content'
            )
        dates = [
            dt.datetime(year=d.year, month=d.month, day=d.day) for d in dates
            ]
        # Avoid error while only one date is picked
        if len(dates) == 1:
            dates.append(dates[0] + dt.timedelta(days=1))

        # for col in ss.overview_caps:
        #     if "Wärmespeicher" in col:
        #         col_sel.metric(
        #             f'Kapazität {col}', format_sep(ss.overview_caps[col].iloc[0], 1),
        #             border=True, help=ss.tt['el_ext']
        #         )

        i = 0
        for unit in ss.param_units.keys():
            ucat = unit.rstrip('0123456789')
            unr = unit[len(ucat):]

            if ucat == 'tes':
                if i > 0:
                    col_sel, col_tes = st.columns([1, 2], gap='large')
                i += 1

                tesdata = ss.energy_system.data_all.loc[
                    dates[0]:dates[1],
                    [f'storage_content_{unit}', f'Q_in_{unit}', f'Q_out_{unit}']
                    ].copy()
                tesdata[f'Q_in_{unit}'] *= -1
                tesdata.rename(
                    columns={
                        f'Q_in_{unit}': txt('results.storage.unit_flow_in', unit=unr),
                        f'Q_out_{unit}': txt('results.storage.unit_flow_out', unit=unr)},
                    inplace=True
                    )
                tesdata.index.names = ['Date']
                tesdata.reset_index(inplace=True)

                col_tes.subheader(txt('results.storage.unit_label', unit=unr))

                col_tes.altair_chart(
                    alt.Chart(tesdata).mark_line(color='#EC6707').encode(
                        y=alt.Y(
                            f'storage_content_{unit}',
                            title=txt('results.storage.chart.content_mwh')
                            ),
                        x=alt.X('Date', title=txt('common.date')),
                        ),
                    width='stretch'
                    )

                domain = [
                    txt('results.storage.unit_flow_out', unit=unr), txt('results.storage.unit_flow_in', unit=unr)
                    ]
                col_tes.altair_chart(
                    alt.Chart(tesdata[['Date', *domain]].melt('Date')).mark_bar(size=0.5).encode(
                        y=alt.Y('value', title=txt('results.storage.chart.charge_discharge_mwh')),
                        x=alt.X('Date', title=txt('common.date')),
                        color=alt.Color('variable').scale(
                            domain=domain,
                            range=[colors[re.sub(r'\s\d', '', d)] for d in domain]
                            ).legend(None)
                        ),
                    width='stretch'
                    )

                col_sel.markdown(txt('results.storage.unit_heading', unit=unr))
                if txt('results.storage.unit_capacity_column', unit=unr) in ss.overview_caps.columns:
                    col_sel.metric(
                        txt('results.storage.metric.capacity_mwh'),
                        format_sep(ss.overview_caps[txt('results.storage.unit_capacity_column', unit=unr)].iloc[0], 1),
                        border=True
                    )
                col_sel.metric(
                    txt('results.storage.metric.total_discharge_mwh'),
                    format_sep(tesdata[txt('results.storage.unit_flow_out', unit=unr)].sum(), 1),
                    border=True
                )
                col_sel.metric(
                    txt('results.storage.metric.total_charge_mwh'),
                    format_sep(abs(tesdata[txt('results.storage.unit_flow_in', unit=unr)].sum()), 1),
                    border=True
                )
                losses = (
                    abs(tesdata[txt('results.storage.unit_flow_in', unit=unr)].sum())
                    - tesdata[txt('results.storage.unit_flow_out', unit=unr)].sum()
                    )
                col_sel.metric(
                    txt('results.storage.metric.losses_mwh'),
                    format_sep(losses, 1),
                    border=True
                )



# %% MARK: Solver Log
with tab_pro:
    st.markdown(
        txt('results.advanced.description'),
        unsafe_allow_html=True
    )
    if ss.param_opt['Solver'] == 'SCIP':
        st.text(txt('results.advanced.scip_no_solverlogs'))
    else:
        with tab_pro.expander(txt('results.advanced.solver_log.expander')):
            logpath = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__), '..', 'solverlogs',
                    f'{ss.param_opt["Solver"].lower()}_log.txt'
                    )
                )
            with open(logpath, 'r', encoding='utf-8') as file:
                solverlog = file.read()

            st.text(solverlog)

# %% MARK: Footer
icon_path = os.path.join(os.path.dirname(__file__), '..', 'img', 'icons')
icon_base64s = load_icon_base64s(icon_path)

footer(icon_base64s)

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
from helpers import footer, format_sep, load_icon_base64s
from reporting import generate_html_report
from streamlit import session_state as ss


@st.dialog('Ergebnisse lokal speichern')
def save_results():
    """Temporarely save results and zip them, then let user download it."""
    with st.spinner('Daten werden verarbeitet...'):
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

        tspath = os.path.join(zippath, 'Ergebnisse_Zeitreihen.csv')
        ss.energy_system.data_all.to_csv(tspath, sep=';')

        cappath = os.path.join(zippath, 'Ergebnisse_Kapazitäten.csv')
        ss.overview_caps.to_csv(cappath, sep=';', encoding='utf-8-sig')

        kpdf = pd.DataFrame.from_dict(
            {k: [v] for k, v in ss.energy_system.key_params.items()}
        )
        kprename = {
            'op_cost_total': 'Betriebskosten',
            'invest_total': 'Investitionskosten',
            'cost_gas': 'Gaskosten',
            'cost_el_grid': 'Elektrizitätskosten (Netz)',
            'cost_el_internal': 'Elektrizitätskosten (Intern)',
            'cost_el': 'Elektrizitätskosten (Gesamt)',
            'cost_total': 'Gesamtkosten',
            'revenues_spotmarket': 'Stromerlöse',
            'revenues_heat': 'Wärmeerlöse',
            'revenues_total': 'Gesamterlöse',
            'balance_total': 'Gesamtbilanz',
            'LCOH': 'Wärmegestehungskosten',
            'total_heat_demand': 'Gesamtwärmebedarf',
            'Emissions OM (Gas)': 'Emissionen (Gasbezug)',
            'Emissions OM (Electricity)': 'Emissionen (Elektrizitätsbezug)',
            'Emissions OM (Spotmarket)': 'Emissionsgutschriften (Elektrizitätseinspeisung)',
            'Total Emissions OM': 'Gesamtemissionen'
        }
        kpdf.rename(columns=kprename, inplace=True)

        kppath = os.path.join(zippath, 'Ergebnisse_Allgemein.csv')
        kpdf.to_csv(kppath, sep=';', encoding='utf-8-sig', index=False)

        shutil.make_archive(zippath, 'zip', zippath)

    with open(f'{zippath}.zip', 'rb') as file:
        btn = st.download_button(
            label='Speichere deine Ergebnisse',
            data=file,
            file_name='Ergebnisse',
            mime='application/zip'
        )

    shutil.rmtree(tmppath)


@st.dialog('Bericht herunterladen')
def download_report():
    """Generate and download HTML report."""
    with st.spinner('Bericht wird generiert...'):
        try:
            # Get image path
            img_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', 'img')
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
                label='📥 Bericht herunterladen',
                data=html_content.encode('utf-8'),
                file_name=f'Bericht_OWP_{timestamp}.html',
                mime='text/html',
                key='report_download_btn'
            )
            
            st.success('Bericht erfolgreich generiert!')
            
        except Exception as e:
            st.error(f'Fehler bei der Berichtsgenerierung: {str(e)}')


# %% MARK: Parameters
shortnames = {
    'Wärmepumpe': 'hp',
    'Gas- und Dampfkraftwerk': 'ccet',
    'Blockheizkraftwerk': 'ice',
    'Solarthermie': 'sol',
    'Gaskessel': 'gb',
    'Elektrodenheizkessel': 'eb',
    'Externe Wärmequelle': 'exhs',
    'Wärmespeicher': 'tes'
}
longnames = {
    'hp': 'Wärmepumpe',
    'ccet': 'Gas- und Dampfkraftwerk',
    'ice': 'Blockheizkraftwerk',
    'sol': 'Solarthermie',
    'gb': 'Gaskessel',
    'eb': 'Elektrodenheizkessel',
    'exhs': 'Externe Wärmequelle',
    'tes': 'Wärmespeicher'
}

colors = {
    'Wärmepumpe': '#B54036',
    'Gas- und Dampfkraftwerk': '#00395B',
    'Blockheizkraftwerk': '#00395B',
    'Gaskessel': '#EC6707',
    'Solarthermie': '#EC6707',
    'Wärmespeicher Ein': 'slategrey',
    'Wärmespeicher Aus': 'dimgrey',
    'Wärmebedarf': '#31333f',
    'Elektrodenheizkessel': '#EC6707',
    'Externe Wärmequelle': '#74ADC0'
}

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

    st.markdown("""---""")

    st.subheader('Assoziierte Projektpartner')
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
    st.header('Simulationsergebnisse')
    st.error('**Error:** Es sind noch keine Ergebnisse vorhanden. Sie müssen zuerst eine Optimierung auf der dafür vorgesehenen Seite durchführen.')

    with st.container(border=True):
        st.page_link(
            'pages/01_Optimierung.py', label='**Zur Optimierung**',
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
            'Überblick', 'Anlageneinsatz', 'Stromproduktion', 'Speicherstand',
            'Erweitert'
            ]
            )
    else:
        tab_ov, tab_unit, tab_el, tab_pro = st.tabs(
            ['Überblick', 'Anlageneinsatz', 'Stromproduktion', 'Erweitert']
            )
else:
    if tes_used:
        tab_ov, tab_unit, tab_tes, tab_pro = st.tabs(
            ['Überblick', 'Anlageneinsatz', 'Speicherstand', 'Erweitert']
            )
    else:
        tab_ov, tab_unit, tab_pro = st.tabs(
            ['Überblick', 'Anlageneinsatz', 'Erweitert']
            )

# %% MARK: Overview
with tab_ov:
    st.markdown(
        (
            '<small>*Es werden die Ergebnisse der Optimierung übersichtlich '
            'dargestellt. Dazu gehören die (optimalen) Kapazitäten, die '
            'resultierende Wärmeproduktion sowie die wirtschaftlichen und '
            'ökologischen Kennwerte. Nach der Analyse kann entweder ein neues '
            'Energiesystem konfiguriert werden. Sollen die Ergebnisse für '
            'weiterführende Analysen genutzt werden, steht der Download eines '
            'standardisierten Berichts oder alternativ die vollständigen '
            'Ergebnisdaten und -parameter zur Verfügung.*</small>'
        ),
        unsafe_allow_html=True
    )
    with st.expander('Auslegung', expanded=True):
        col_cap, col_sum = st.columns([3, 2], gap='large')

        col_cap.subheader(
            'Optimierte Anlagenkapazitäten', help=ss.tt['results_design']
            )
        col_cap1, col_cap2 = col_cap.columns([2, 3], gap='large')

        topopath = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), '..', 'img', 'es_topology_'
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
        ss.overview_caps.rename(index={0: 'Kapazität'}, inplace=True)
        ss.overview_caps = ss.overview_caps.apply(lambda x: round(x, 1))

        col_cap2.dataframe(ss.overview_caps.T, width='stretch')

        col_sum.subheader(
            'Wärmeproduktion', help=ss.tt['results_heat_production']
            )
        qsum = pd.DataFrame(columns=['unit', 'qsum'])
        idx = 0
        for unit in ss.param_units.keys():
            ucat = unit.rstrip('0123456789')
            unr = unit[len(ucat):]
            if ucat == 'tes':
                tl = {'in': 'Ein', 'out': 'Aus'}
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
                y=alt.Y('unit', title=None),
                x=alt.X('qsum', title='Gesamtwärmebereitstellung in MWh')
                ),
            width='stretch'
            )

    with st.expander('Wirtschaftliche Kennzahlen'):
        st.subheader('Wirtschaftliche Kennzahlen')

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            'LCOH (Erzeugung) in €/MWh',
            format_sep(ss.energy_system.key_params['LCOH']),
            border=True, help=ss.tt['lcoh_heat']
            )
        col1.metric(
            'LCOH (inkl. Wärmenetz) in €/MWh',
            format_sep(ss.energy_system.key_params['LCOH_incl_net']),
            border=True, help=ss.tt['lcoh_incl_net']
            )
        col2.metric(
            'Wärmeerlöse in €',
            format_sep(ss.energy_system.key_params['revenues_heat']),
            border=True, help=ss.tt['rev_heat']
            )
        col2.metric(
            'Stromerlöse in €',
            format_sep(ss.energy_system.key_params['revenues_spotmarket']),
            border=True, help=ss.tt['rev_el']
            )
        col3.metric(
            'Stromkosten in €',
            format_sep(ss.energy_system.key_params['cost_el']),
            border=True, help=ss.tt['cost_el']
            )
        col3.metric(
            'Gaskosten in €',
            format_sep(ss.energy_system.key_params['cost_gas']),
            border=True, help=ss.tt['cost_gas']
            )
        col4.metric(
            'Anlagenkosten (gesamt)',
            format_sep(ss.energy_system.cost_df.loc[[
                'invest', 'op_cost_fix', 'op_cost_var'
            ]].sum().sum()),
            border=True, help=ss.tt['cost_units']
            )
        col4.metric(
            'Wärmenetzkosten (gesamt)',
            format_sep(
                ss.energy_system.key_params['invest_net_total']
                + ss.energy_system.key_params['cost_net_fix_total']
                + ss.energy_system.key_params['cost_net_var_total']
            ),
            border=True, help=ss.tt['cost_units']
            )

        unit_cost = ss.energy_system.cost_df.copy()
        unit_cost.loc['invest', 'Wärmenetz'] = (
            ss.energy_system.key_params['invest_net_total']
        )
        unit_cost.loc['op_cost_fix', 'Wärmenetz'] = (
            ss.energy_system.key_params['cost_net_fix_total']
        )
        unit_cost.loc['op_cost_var', 'Wärmenetz'] = (
            ss.energy_system.key_params['cost_net_var_total']
        )
        unit_cost.loc['op_cost', 'Wärmenetz'] = (
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
                'invest': 'Investitionskosten (€)',
                'op_cost_var': 'Variable Betriebskosten (€)',
                'op_cost_fix': 'Fixe Betriebskosten (€)',
                'op_cost': 'Gesamtbetriebskosten (€)'
                },
            inplace=True
            )

        unit_cost.drop('Gesamtbetriebskosten (€)', axis=0, inplace=True)
        unit_cost = unit_cost.map(format_sep)

        st.dataframe(unit_cost, width='stretch')

    with st.expander('Ökologische Kennzahlen'):
    # st.subheader('Ökologische Kennzahlen', help=ss.tt['results_ecol'])
        met1, met2, met3, met4= st.columns([1, 1, 1, 1])
        met1.metric(
            'Gesamtemissionen in t',
            format_sep(ss.energy_system.key_params['Total Emissions OM']/1e3, 1),
            border=True, help=ss.tt['em_ges']
            )
        met2.metric(
            'Emissionen durch Gasbezug in t',
            format_sep(ss.energy_system.key_params['Emissions OM (Gas)']/1e3, 1),
            border=True, help=ss.tt['em_gas']
            )
        met3.metric(
            'Emissionen durch Strombezug in t',
            format_sep(ss.energy_system.key_params['Emissions OM (Electricity)']/1e3, 1),
            border=True, help=ss.tt['em_el']
            )

        met4.metric(
            'Emissionsgutschriften durch Stromproduktion in t',
            format_sep(ss.energy_system.key_params['Emissions OM (Spotmarket)']/1e3, 1),
            border=True, help=ss.tt['em_spot']
            )

    with st.container(border=True):

        col_left, col_mid, col_right = st.columns([1, 1, 1])
        reset_es = col_left.button(
            label='📝 **Neues Energiesystem konfigurieren**',
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
            label='📊 **Bericht herunterladen**',
            key='report_download_button',
            width='stretch'
            )
        if report_btn:
            download_report()

        save_results_btn = col_right.button(
            label='💾 **Daten exportieren**',
            width='stretch'
            )
        if save_results_btn:
            save_results()

# %% MARK: Unit Commitment
with tab_unit:
    st.markdown(
        (
            '<small>*Die Ergebnisse des Einsatzes werden in Form geordneter '
            'Jahresdauerlinien als auch als zeitlicher Verlauf des '
            'tatsächlichen Anlageneinsatzes über den gesamten '
            'Betrachtungszeitraum dargstellt. Für eine vertiefte Analyse '
            'können einzelne Anlagen nach Bedarf ausgeblendet werden. '
            'Zusätzlich ist es möglich, den Betrachtungszeitraum anzupassen '
            'oder die Ergebnisse auf unterschiedlichen Ebenen zu aggregieren, '
            'um spezifische Fragestellungen gezielt auszuwerten.*</small>'
        ),
        unsafe_allow_html=True
    )
    col_sel, col_unit = st.columns([1, 2], gap='large')

    col_unit.subheader(
        'Geordnete Jahresdauerlinien des Anlageneinsatzes', help=ss.tt['oadl']
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
                collabel = 'Wärmebedarf'
            elif this_unit.rstrip('0123456789') == 'tes':
                if '_in' in col:
                    collabel = f'{longnames[this_unit_cat]} {this_unit_nr} Ein'
                elif '_out' in col:
                    collabel = f'{longnames[this_unit_cat]} {this_unit_nr} Aus'
            else:
                collabel = f'{longnames[this_unit_cat]} {this_unit_nr}'
            heatprod[collabel] = ss.energy_system.data_all[col].copy()

    selection = col_sel.multiselect(
        'Wähle die Wärmeversorgungsanlagen aus:',
        list(heatprod.columns),
        default=list(heatprod.columns),
        placeholder='Wärmeversorgungsanlagen'
        )

    dates = col_sel.date_input(
        'Zeitraum auswählen:',
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
            'Ergebnisse aggregieren', help=ss.tt['toggle_agg_results'],
            key='toggle_agg_results'
        )
    if agg_results:
        agg_periods = {
            'Stündlich': 'h',
            'Täglich': 'd',
            'Wöchentlich': 'W',
            'Monatlich': 'ME',
            'Quartalsweise': 'QE'
        }
        agg_period_name = col_sel.selectbox(
            'Aggregationszeitraum wählen:', options=list(agg_periods.keys()),
                key='select_agg_time_span_dispatch'
        )
        agg_period = agg_periods[agg_period_name]

        agg_method = col_sel.selectbox(
            'Aggregationsmethode wählen:', options=['Mittelwert', 'Summe'],
            help=ss.tt['agg_method'], key='agg_method_dispatch'
        )
    else:
        agg_period_name = 'Stündlich'

    if agg_results:
        if agg_method == 'Mittelwert':
            heatprod = heatprod.resample(agg_period).mean()
        elif agg_method == 'Summe':
            heatprod = heatprod.resample(agg_period).sum()

    heatprod_sorted = pd.DataFrame(
        np.sort(heatprod.values, axis=0)[::-1], columns=heatprod.columns
        )
    heatprod_sorted.index.names = ['Stunde']
    heatprod_sorted.reset_index(inplace=True)

    hprod_sorted_melt = heatprod_sorted[['Stunde'] + selection].melt('Stunde')
    hprod_sorted_melt.rename(
        columns={'variable': 'Versorgungsanlage'}, inplace=True
        )

    ylabel = (
        f'{agg_period_name}e'
        if agg_period_name[-1] != 'e'
        else agg_period_name
    )

    col_unit.altair_chart(
        alt.Chart(hprod_sorted_melt).mark_line().encode(
            y=alt.Y('value', title=f'{ylabel} Wärmeproduktion in MWh'),
            x=alt.X('Stunde', title='Anzahl'),
            color=alt.Color('Versorgungsanlage').scale(
                domain=selection,
                range=[colors[re.sub(r'\s\d', '', s)] for s in selection]
                )
            ),
        width='stretch'
        )

    col_unit.subheader('Tatsächlicher Anlageneinsatz', help=ss.tt['adl'])

    if tes_used:
        for col in heatprod.columns:
            if 'Wärmespeicher' in col and 'Ein' in col:
                heatprod[col] *= -1
    # heatprod.drop('Wärmebedarf', axis=1, inplace=True)
    heatprod.index.names = ['Date']
    heatprod.reset_index(inplace=True)

    if agg_results and 'Wärmebedarf' in selection:
        selection.remove('Wärmebedarf')

    hprod_melt = heatprod[['Date'] + selection].melt('Date')
    hprod_melt.rename(
        columns={'variable': 'Versorgungsanlage'}, inplace=True
        )

    if not agg_results:
        col_unit.altair_chart(
            alt.Chart(hprod_melt).mark_line().encode(
                y=alt.Y('value', title=f'{ylabel} Wärmeproduktion in MWh'),
                x=alt.X('Date', title='Datum'),
                color=alt.Color('Versorgungsanlage').scale(
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
                y=alt.Y('value', title=f'{ylabel} Wärmeproduktion in MWh'),
                x=alt.X(time_units[agg_period], title='Datum'),
                color=alt.Color('Versorgungsanlage').scale(
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
            (
                '<small>*Es wird die Stromproduktion des Systems dargestellt. '
                'Neben zentralen Kennzahlen werden die Netzeinspeisung sowie '
                'die interne Nutzung des erzeugten Stroms ausgewiesen. Zur '
                'besseren Einordnung ist zusätzlich die zugrunde liegende '
                'Strompreiszeitreihe visualisiert. Für weiterführende '
                'Analysen können alle dargestellten Daten flexibel aggregiert '
                'werden.*</small>'
            ),
            unsafe_allow_html=True
        )
        col_sel, col_el = st.columns([1, 2], gap='large')

        dates = col_sel.date_input(
            'Zeitraum auswählen:',
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
                'Ergebnisse aggregieren', help=ss.tt['toggle_agg_results'],
                key='toggle_agg_results_el'
            )
        if agg_results:
            agg_periods = {
                'Stündlich': 'h',
                'Täglich': 'd',
                'Wöchentlich': 'W',
                'Monatlich': 'ME',
                'Quartalsweise': 'QE'
            }
            agg_period_name = col_sel.selectbox(
                'Aggregationszeitraum wählen:',
                options=list(agg_periods.keys()),
                key='select_agg_time_span_el'
            )
            agg_period = agg_periods[agg_period_name]

            agg_method = col_sel.selectbox(
                'Aggregationsmethode wählen:', options=['Mittelwert', 'Summe'],
                help=ss.tt['agg_method'], key='agg_method_el'
            )
        else:
            agg_period_name = 'Stündlich'

        if agg_results:
            elprod.set_index('Date', inplace=True)
            if agg_method == 'Mittelwert':
                elprod = elprod.resample(agg_period).mean().reset_index()
            elif agg_method == 'Summe':
                elprod = elprod.resample(agg_period).sum().reset_index()

        elprod_sorted = pd.DataFrame(
            np.sort(elprod.values, axis=0)[::-1], columns=elprod.columns
            )
        elprod_sorted.index.names = ['Stunde']
        elprod_sorted.reset_index(inplace=True)

        col_sel.subheader('Kennzahlen')
        col_sel.metric(
            'Stromerlöse in €',
            format_sep(ss.energy_system.key_params['revenues_spotmarket'], 2),
            border=True, help=ss.tt['rev_el']
        )
        col_sel.metric(
            'Stromkosten in €',
            format_sep(ss.energy_system.key_params['cost_el'], 2),
            border=True, help=ss.tt['cost_el']
        )
        col_sel.metric(
            'Stromkosten in € (Netz)',
            format_sep(ss.energy_system.key_params['cost_el_grid'], 2),
            border=True, help=ss.tt['cost_el_int']
        )
        col_sel.metric(
            'Stromkosten in € (intern)',
            format_sep(ss.energy_system.key_params['cost_el_internal'], 2),
            border=True, help=ss.tt['cost_el_ext']
        )
        col_sel.metric(
            'Stromproduktion in MWh (Spotmarkt)',
            format_sep(elprod['P_spotmarket'].sum(), 1),
            border=True, help=ss.tt['el_ext']
        )
        col_sel.metric(
            'Stromproduktion in MWh (intern)',
            format_sep(elprod['P_internal'].sum(), 1),
            border=True, help=ss.tt['el_int']
        )

        col_el.subheader('Stromproduktion - Netzeinspeisung')
        col_el.altair_chart(
            alt.Chart(elprod).mark_line(color='#00395B').encode(
                y=alt.Y(
                    'P_spotmarket',
                    title='Ins Netz eingespeiste Elektrizität in MWh'
                    ),
                x=alt.X('Date', title='Datum')
            ),
            width='stretch'
            )

        col_el.subheader('Stromproduktion - interne Nutzung')
        col_el.altair_chart(
            alt.Chart(elprod).mark_line(color='#74ADC0').encode(
                y=alt.Y(
                    'P_internal',
                    title='Intern genutze Elektrizität in MWh'
                    ),
                x=alt.X('Date', title='Datum')
            ),
            width='stretch'
            )

        col_el.subheader('Spotmarktpreise')
        col_el.altair_chart(
            alt.Chart(elprod).mark_line(color='#00395B').encode(
                y=alt.Y('el_spot_price', title='Spotmarkt Strompreis in €/MWh'),
                x=alt.X('Date', title='Datum')
            ),
            width='stretch'
            )

# %% MARK: TES Content
if tes_used:
    with tab_tes:
        st.markdown(
            (
                '<small>*Es werden die Ergebnisse der thermischen Speicher '
                'dargestellt. Neben zentralen Kennzahlen werden der '
                'Speicherfüllstand sowie die Speicherbeladung (negativ) und '
                'Entladung (positiv) im zeitlichen Verlauf visualisiert. Zur '
                'tieferen Analyse können alle Daten flexibel aggregiert '
                'werden.*</small>'
            ),
            unsafe_allow_html=True
        )
        st.subheader('Füllstand des thermischen Energiespeichers')

        col_sel, col_tes = st.columns([1, 2], gap='large')

        dates = col_sel.date_input(
            'Zeitraum auswählen:',
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
                        f'Q_in_{unit}': f'Wärmespeicher {unr} Ein',
                        f'Q_out_{unit}': f'Wärmespeicher {unr} Aus'},
                    inplace=True
                    )
                tesdata.index.names = ['Date']
                tesdata.reset_index(inplace=True)

                col_tes.subheader(f'Wärmespeicher {unr}')

                col_tes.altair_chart(
                    alt.Chart(tesdata).mark_line(color='#EC6707').encode(
                        y=alt.Y(
                            f'storage_content_{unit}',
                            title='Speicherstand in MWh'
                            ),
                        x=alt.X('Date', title='Datum'),
                        ),
                    width='stretch'
                    )

                domain = [
                    f'Wärmespeicher {unr} Aus', f'Wärmespeicher {unr} Ein'
                    ]
                col_tes.altair_chart(
                    alt.Chart(tesdata[['Date', *domain]].melt('Date')).mark_bar(size=0.5).encode(
                        y=alt.Y('value', title='Speicherbe- & -entladung in MWh'),
                        x=alt.X('Date', title='Datum'),
                        color=alt.Color('variable').scale(
                            domain=domain,
                            range=[colors[re.sub(r'\s\d', '', d)] for d in domain]
                            ).legend(None)
                        ),
                    width='stretch'
                    )

                col_sel.markdown(f'##### Speicher {unr}')
                if f'Wärmespeicher {unr} (MWh)' in ss.overview_caps.columns:
                    col_sel.metric(
                        'Kapazität in MWh',
                        format_sep(ss.overview_caps[f'Wärmespeicher {unr} (MWh)'].iloc[0], 1),
                        border=True
                    )
                col_sel.metric(
                    'Summe der Speicherntladung in MWh',
                    format_sep(tesdata[f'Wärmespeicher {unr} Aus'].sum(), 1),
                    border=True
                )
                col_sel.metric(
                    'Summe der Speicherbeladung in MWh',
                    format_sep(abs(tesdata[f'Wärmespeicher {unr} Ein'].sum()), 1),
                    border=True
                )
                losses = (
                    abs(tesdata[f'Wärmespeicher {unr} Ein'].sum())
                    - tesdata[f'Wärmespeicher {unr} Aus'].sum()
                    )
                col_sel.metric(
                    'Speicherverluste in MWh',
                    format_sep(losses, 1),
                    border=True
                )



# %% MARK: Solver Log
with tab_pro:
    st.markdown(
        (
            '<small>*Die erweiterten Ergebnisse enthalten Informationen für '
            'den Solverlog, der vom jeweiligen Solver automatisch generiert '
            'wird, um optimierungsspezifische Informationen für die '
            'Simulation zurückzugeben.*</small>'
        ),
        unsafe_allow_html=True
    )
    if ss.param_opt['Solver'] == 'SCIP':
        st.text('Der SCIP Solver ermöglicht aktuell keine Solverlogs.')
    else:
        with tab_pro.expander('Solver Log'):
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

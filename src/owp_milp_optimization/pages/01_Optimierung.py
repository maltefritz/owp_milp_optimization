import base64
import json
import os
import shutil

import pandas as pd
import streamlit as st
from helpers import footer, load_icon_base64s
from model import EnergySystem
from streamlit import session_state as ss


@st.dialog('Energiesystem lokal speichern')
def download_energy_system():
    """Temporarely save data and zip it, then let user download zip archive."""
    with st.spinner('Daten werden verarbeitet...'):
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
            label='Speichere dein Energiesystem',
            data=file,
            file_name='Energiesystem',
            mime='application/zip'
        )

    shutil.rmtree(tmppath)

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
st.header('Zusammenfassung')

if 'param_units' not in ss:
    st.error('**Error:** Es sind noch keine Parameter vorhanden. Sie müssen zuerst das Energiesystem auf der dafür vorgesehenen Seite konfigurieren.')

    with st.container(border=True):
        st.page_link(
            'pages/00_Energiesystem.py', label='**Energiesystem konfigurieren**',
            icon='📝', width='stretch'
            )

    icon_path = os.path.join(os.path.dirname(__file__), '..', 'img', 'icons')
    icon_base64s = load_icon_base64s(icon_path)

    footer(icon_base64s)
    st.stop()

col_es, col_over = st.columns([1, 4], gap='large')

col_es.subheader('Energiesystem')

topopath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'img', 'es_topology_')
    )

col_es.image(f'{topopath}header.png', width='stretch')
for unit in ss.param_units.keys():
    unit = unit.rstrip('0123456789')
    col_es.image(
        f'{topopath+unit}.png', width='stretch'
        )

col_over.subheader('Zeitreihen im Wärmeversorgungssystem')

data_overview = ss.data.describe()
data_overview.drop(index=['count', 'std', '25%', '75%'], inplace=True)
data_overview.rename(
    index={
        'mean': 'Mittelwert', 'min': 'Minimalwert',
        '50%': 'Median', 'max': 'Maximalwert'
        },
    columns={
        'heat_demand': 'Wärmelast (MWh)',
        'el_spot_price': 'Spotmarkt Strompreis (€/MWh)',
        'ef_om': 'Emissionsfaktor Strommix (kg/MWh)',
        'gas_price': 'Gaspreis (€/MWh)',
        'co2_price': 'CO₂-Preis (€/MWh)'
        }, inplace=True
    )

if 'Solarthermie' in ss.units:
    data_overview['solar_heat_flow'] *= 1e6
    data_overview.rename(columns={
        'solar_heat_flow': 'Spez. solare Einstrahlung (Wh/m²)'
        }, inplace=True
    )

col_over.dataframe(data_overview.T.style.format('{:.2f}'), width='stretch')

col_over.subheader('Parameter im Wärmeversorgungssystem')

param_overview = pd.DataFrame.from_dict(
    ss.param_opt, orient='index', columns=['Wert']
    )
param_overview.drop(
    index=[
        'MIPGap', 'TimeLimit', 'heat_price', 'TEHG_bonus',
        'net_op_cost_fix', 'net_op_cost_var'
        ], inplace=True
    )
param_overview.loc['ef_gas'] *= 1000
param_overview.loc['capital_interest'] *= 100
param_overview.rename(
    index={
        'net_inv_spez': 'Spez. Investitionskosten Wärmenetz (€/MW/m)',
        'ef_gas': 'Emissionsfaktor Gas (kg/MWh)',
        'elec_consumer_charges_grid': 'Strompreisbestandteile (Netz) (€/MWh)',
        'elec_consumer_charges_self': 'Strompreisbestandteile (Eigenbedarf) (€/MWh)',
        'energy_tax': 'Energiesteuer (€/MWh)',
        'vNNE': 'Vermiedene Netznutzungsentgelte (€/MWh)',
        'capital_interest': 'Kapitalzins (%)',
        'lifetime': 'Lebensdauer (a)',
        'net_dist': 'Wärmenetzlänge (km)'
        }, inplace=True
    )
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
    label='💾 Input Daten speichern',
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
    label='📝 Energiesystem speichern',
    key='download_es_button_overview',
    width='stretch'
    )
if download_es_btn:
    download_energy_system()

reset_es = col_reset.button(
    label='📝 Neues Energiesystem konfigurieren',
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
    opt = st.button(label='🖥️**Optimierung starten**', width='stretch')
    if opt:
        with st.spinner('Optimierung wird durchgeführt...'):
            ss.energy_system = EnergySystem(
                ss.data, ss.param_units, ss.param_opt
                )
            st.toast('Energiesystem ist initialisiert', duration=8)

            ss.energy_system.generate_buses()
            ss.energy_system.generate_sources()
            ss.energy_system.generate_sinks()
            ss.energy_system.generate_components()
            st.toast('Modell ist erzeugt', duration=8)

            st.toast('Optimierung ist gestartet', duration=8)
            solver_status = ss.energy_system.solve_model()

            if solver_status == 'ok':
                st.toast('Optimierungsproblem ist gelöst', duration=8)
                ss.energy_system.get_results()
                st.toast('Ergebnisse sind ausgelesen', duration=8)

                ss.energy_system.calc_econ_params()
                ss.energy_system.calc_ecol_params()
                st.toast('Postprocessing ist durchgeführt', duration=8)

if solver_status is not None:
    if solver_status == 'infeasable':
        st.error(
            'Das Optimierungsproblem konnte nicht gelöst werden.\n\n'
            + 'Möglicherweise wurden die Anlagengrößen so gewählt, dass diese '
            + 'nicht in der Lage sind die Wärmelast in jedem Zeitschritt zu'
            + 'decken und/oder einen Wärmespeicher zu beladen.\n\n'
            + 'Mögliche Ansätze zur Lösung des Problems könnten sein:\n\n'
            + '- Passe installierte oder Grenzen der zu installierenden '
            + 'Leistung der Anlagen an\n\n'
            + '- Füge einen Wärmespeicher hinzu\n\n'
            + '- Füge eine flexible externe Wärmequelle hinzu\n\n'
            )
    elif solver_status == 'unknown solver error':
        st.error(
            'Bei der Optimierung ist ein unbekannter Fehler aufgetreten.\n\n'
            + 'Überprüfe die gewählten Parameter und versuche eine neue '
            + 'Optimierung zu starten.'
            )
if opt:
    if solver_status is not None and solver_status == 'ok':
        with st.container(border=True):
            st.page_link(
                'pages/02_Simulationsergebnisse.py',
                label='**Zu den Ergebnissen**',
                icon='📊', width='stretch'
                )

# %% MARK: Footer
icon_path = os.path.join(os.path.dirname(__file__), '..', 'img', 'icons')
icon_base64s = load_icon_base64s(icon_path)

footer(icon_base64s)

import base64
import os

import pandas as pd
import streamlit as st
from helpers import footer, load_icon_base64s, txt
from streamlit import session_state as ss

st.set_page_config(
    layout='wide',
    page_title=txt('app.page_title', _language='de'),
    page_icon=os.path.join(os.path.dirname(__file__), 'img',  'page_icon_ZNES.png')
    )

@st.cache_data
def read_input_data():
    '''Read in input data all at once.'''
    inputpath = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'input'
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

if 'eco_data' not in ss:
    ss.all_heat_load, ss.eco_data = read_input_data()

    ss.all_el_prices = ss.eco_data['el_spot_price'].to_frame()
    ss.all_el_emissions = ss.eco_data['ef_om'].to_frame()
    ss.all_gas_prices = ss.eco_data['gas_price'].to_frame()
    ss.all_co2_prices = ss.eco_data['co2_price'].to_frame()
    ss.all_solar_heat_flow = ss.eco_data[[
        'solar_heat_flow_schleswig',
        'solar_heat_flow_chemnitz',
        'solar_heat_flow_stuttgart'
    ]]

# %% Sidebar
with st.sidebar:
    st.subheader(txt('app.sidebar_title'))

    logo_inno = os.path.join(
        os.path.dirname(__file__), 'img', 'Logo_InnoNord_OWP.png'
        )
    st.image(logo_inno, width='stretch')

    logo = os.path.join(
        os.path.dirname(__file__), 'img', 'Logo_ZNES_mitUnisV2.svg'
        )
    st.image(logo, width='stretch')

# %% Main Window
col_inno, _, col_foerder = st.columns([0.3, 0.4, 0.3])
logo = os.path.join(os.path.dirname(__file__), 'img',  'Logo_InnoNord_OWP.png')
col_inno.image(logo, width='stretch')

logo_foederer = os.path.join(os.path.dirname(__file__), 'img',  'Logos_Förderer_ohnePTJ_BMFTR.png')
col_foerder.image(logo_foederer, width='stretch')

st.write(txt('home.intro'))

with st.container(border=True):
    st.page_link(
        'pages/00_Energiesystem.py',
        label=f"**{txt('home.configure_energy_system')}**",
        icon='📝', width='stretch',
        )

st.write(txt('home.associated_project_partners'))

# _, col_partner, _ = st.columns([0.1 ,0.8, 0.1])
logo_partner = os.path.join(
    os.path.dirname(__file__), 'img',  'Logos_Partner_neu.svg'
    )
# col_partner.image(logo_partner, width='stretch')
st.image(logo_partner, width='stretch')

st.markdown('''---''')

with st.expander(txt('home.expander.used_software')):
    st.info(txt('home.used_software_text'))

with st.expander(txt('home.expander.publications')):
    st.success(txt('home.publications_text'))

with st.expander(txt('home.expander.disclaimer')):
    st.warning(txt('home.disclaimer_text'))

with st.expander(txt('home.expander.copyright')):
    licpath = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..', 'LICENSE'
        ))
    with open(licpath, 'r', encoding='utf-8') as file:
        lictext = file.read()

    st.success(txt('home.software_license_heading') + lictext.replace('(c)', '©'))

# %% MARK: Footer
icon_path = os.path.join(os.path.dirname(__file__), 'img', 'icons')
icon_base64s = load_icon_base64s(icon_path)

footer(icon_base64s)

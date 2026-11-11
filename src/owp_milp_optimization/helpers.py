import base64
import io
import json
import os
import zipfile
from importlib import metadata

import pandas as pd
import streamlit as st


def read_license():
    """Return the license text of the dashboard.

    An installed package (regular or editable) ships its license file in its
    metadata. Without an installation, the license file of the source checkout
    is used. Returns None if no license file is available.
    """
    try:
        dist = metadata.distribution('owp_milp_optimization')
    except metadata.PackageNotFoundError:
        pass
    else:
        for name in dist.metadata.get_all('License-File') or ['LICENSE']:
            text = dist.read_text(f'licenses/{name}') or dist.read_text(name)
            if text:
                return text

    licpath = os.path.join(os.path.dirname(__file__), '..', '..', 'LICENSE')
    if os.path.isfile(licpath):
        with open(licpath, 'r', encoding='utf-8') as file:
            return file.read()
    return None


def zip_files(files):
    """Return a zip archive of the given files as bytes.

    The archive is built in memory, so nothing is written to the package
    directory, which can be read-only in an installation. ``files`` maps the
    file names in the archive to their content (str or bytes).
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def energy_system_to_zip(data, param_opt, param_units):
    """Return the energy system as zip archive (bytes) for the download."""
    return zip_files({
        'data_input.csv': data.to_csv(sep=';'),
        'param_opt.json': json.dumps(param_opt, indent=4, sort_keys=True),
        'param_units.json': json.dumps(param_units, indent=4, sort_keys=True),
    })


def energy_system_from_zip(file):
    """Read an energy system from a zip archive saved by the dashboard.

    Returns the input data, the optimization and the unit parameters.
    """
    with zipfile.ZipFile(file) as archive:
        with archive.open('data_input.csv') as csvfile:
            data = pd.read_csv(csvfile, sep=';', index_col=0, parse_dates=True)
        param_opt = json.loads(archive.read('param_opt.json').decode('utf-8'))
        param_units = json.loads(
            archive.read('param_units.json').decode('utf-8')
        )
    return data, param_opt, param_units


def img_to_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def load_icon_base64s(icon_path):
    return {
        "mail64": img_to_base64(os.path.join(icon_path, 'mail_icon_bw.svg')),
        "orcid64": img_to_base64(os.path.join(icon_path, 'orcid_icon_bw.svg')),
        "github64": img_to_base64(os.path.join(icon_path, 'github_icon_bw.svg')),
        "linkedin64": img_to_base64(os.path.join(icon_path, 'linkedin_icon_bw.svg')),
    }

def show_footer_dialog(icon_base64s):
    @st.dialog("Kontaktdaten")
    def footer_context():
        st.markdown(f"""
        <div style='font-size: 1.0em;'>
            <!-- Personenblock Malte -->
            <div style='margin-bottom: 0.5em;'>
                <strong>Malte Fritz</strong>
                <img src="https://avatars.githubusercontent.com/u/35224977?v=4" width="32" style="margin: 0 10px;"><br>
            </div>
            <p style="margin-bottom: 0.3em;">malte.fritz@hs-flensburg.de</p>
            <a href="mailto:malte.fritz@hs-flensburg.de" style="text-decoration: none;">
                <img src="data:image/svg+xml;base64,{icon_base64s['mail64']}" width="32" style="margin: 10px 10px 10px 0;">
            </a>
            <a href="https://orcid.org/my-orcid?orcid=0009-0001-5843-0973" style="text-decoration: none;">
                <img src="data:image/svg+xml;base64,{icon_base64s['orcid64']}" width="29" style="margin: 0 10px;">
            </a>
            <a href="https://github.com/maltefritz" style="text-decoration: none;">
                <img src="data:image/svg+xml;base64,{icon_base64s['github64']}" width="30" style="margin: 0 10px;">
            </a>
            <a href="https://www.linkedin.com/in/malte-fritz-515259100" style="text-decoration: none;">
                <img src="data:image/svg+xml;base64,{icon_base64s['linkedin64']}" width="35" style="margin: 0 10px;">
            </a>
            <br><br><br>
            <!-- Personenblock Jonas -->
            <div style='margin-bottom: 0.5em;'>
                <strong>Jonas Freißmann</strong>
                <img src="https://avatars.githubusercontent.com/u/57762052?v=4" width="32" style="margin: 0 10px;"><br>
            </div>
            <p style="margin-bottom: 0.3em;">jonas.freissmann@hs-flensburg.de</p>
            <a href="mailto:jonas.freissmann@hs-flensburg.de" style="text-decoration: none;">
                <img src="data:image/svg+xml;base64,{icon_base64s['mail64']}" width="32" style="margin: 10px 10px 10px 0;">
            </a>
            <a href="https://orcid.org/0009-0007-6432-5479" style="text-decoration: none;">
                <img src="data:image/svg+xml;base64,{icon_base64s['orcid64']}" width="29" style="margin: 0 10px;">
            </a>
            <a href="https://github.com/jfreissmann" style="text-decoration: none;">
                <img src="data:image/svg+xml;base64,{icon_base64s['github64']}" width="30" style="margin: 0 10px;">
            </a>
            <a href="https://www.linkedin.com/in/jonas-frei%C3%9Fmann-8a6401368/" style="text-decoration: none;">
                <img src="data:image/svg+xml;base64,{icon_base64s['linkedin64']}" width="35" style="margin: 0 10px;">
            </a>
        </div>
        """, unsafe_allow_html=True)
    return footer_context

def footer(icon_base64s):
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()

    pad_left, col_in, col_nl, col_bot, col_hs, col_help, pad_right = st.columns(7)

    def button_html(text, url, color):
        return f"""
        <div style="text-align: center;">
            <a href="{url}" target="_blank">
                <button style="
                    background-color: {color};
                    border: none;
                    color: white;
                    font-size: 16px;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;">{text}</button>
            </a>
        </div>
        """

    col_in.markdown(button_html("Inno!Nord", "https://inno-nord-projekt.de/", "#00395B"), unsafe_allow_html=True)
    col_nl.markdown(button_html("Newsletter", "https://seu2.cleverreach.com/f/370472-374367/", "#74ADC0"), unsafe_allow_html=True)
    col_hs.markdown(button_html("HS Flensburg", "https://hs-flensburg.de/", "#EC6707"), unsafe_allow_html=True)
    col_help.markdown(button_html("Dokumentation", "https://owp-milp-optimization.readthedocs.io/de/latest/index.html", "#B54036"), unsafe_allow_html=True)

    if col_bot.button(
        '© Malte Fritz & Jonas Freißmann :material/open_in_new:',
        type='tertiary', width='stretch', key='contact_button'
    ):
        show_footer_dialog(icon_base64s)()

def format_sep(value, dec=2):
    return f"{value:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")

"""Report generation module for optimization results."""

import base64
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import altair as alt
import pandas as pd
from jinja2 import Template

from owp_milp_optimization.charts import (create_dispatch_timeseries_chart,
                                          create_el_prod_grid_chart,
                                          create_el_prod_internal_chart,
                                          create_heat_production_chart,
                                          create_ordered_duration_line_chart,
                                          create_tes_content_chart)

from .styling import REPORT_CSS
from .templates import (get_chart_section_template, get_kpi_card_template,
                        get_report_template)

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

# Configure Altair to handle large datasets (up to 8760+ for yearly hourly data)
alt.data_transformers.enable('default', max_rows=None)

def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 data URI."""
    if not os.path.exists(image_path):
        return ""

    with open(image_path, 'rb') as f:
        data = f.read()

    # Determine MIME type
    ext = Path(image_path).suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.svg': 'image/svg+xml',
    }
    mime_type = mime_types.get(ext, 'image/png')

    img_base64 = base64.b64encode(data).decode('utf-8')
    return f'data:{mime_type};base64,{img_base64}'


def format_number(value: float, decimals: int = 1) -> str:
    """Format number with thousand separators."""
    if pd.isna(value):
        return '-'

    formatted = f'{value:,.{decimals}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted


# Capacity fields shown only when the capacity is fixed vs. optimized,
# mirroring the config page (00_Energiesystem.py).
DISP_OPT_PARAMS = ['cap_N', 'Q_N', 'A_N']
COMB_OPT_PARAMS = ['cap_max', 'cap_min', 'Q_max', 'Q_min', 'A_max', 'A_min']


def _param_decimals(fmt: str) -> int:
    """Parse decimal count from a format string like '%0.3f' (default 2)."""
    match = re.search(r'\.(\d+)f', fmt or '')
    return int(match.group(1)) if match else 2


def _format_unit_param(value: Any, uinfo: Dict[str, Any]) -> str:
    """Format a single unit parameter value, mirroring the config page."""
    if uinfo.get('type') == 'bool':
        return 'Ja' if value else 'Nein'

    display = value * 100 if uinfo.get('unit') == '%' else value
    return format_number(display, _param_decimals(uinfo.get('format', '')))


def _unit_param_label(uinput: str, uinfo: Dict[str, Any], unit_cat: str) -> str:
    """Build a parameter label with unit, mirroring the config page logic."""
    name = uinfo['name']
    unit = uinfo.get('unit', '')

    # Economic parameters carry unit-category specific units
    if unit_cat == 'sol':
        if uinput == 'inv_spez':
            return f'{name} in €/m²'
        if uinput == 'op_cost_fix':
            return f'{name} in €/MWh'
    elif unit_cat == 'tes' and uinput in ('inv_spez', 'op_cost_fix') and unit != '%':
        return f'{name} in €/MWh'

    if unit == '':
        return name
    return f'{name} in {unit}'


def _param_rows_html(
    unit_params: Dict[str, Any],
    group_inputs: Dict[str, Any],
    unit_cat: str,
    skip: Optional[list] = None,
) -> str:
    """Build table rows for a group of unit parameters."""
    skip = skip or []
    rows = ''
    for uinput, uinfo in group_inputs.items():
        if uinput not in unit_params or uinput in skip:
            continue
        label = _unit_param_label(uinput, uinfo, unit_cat)
        value = _format_unit_param(unit_params[uinput], uinfo)
        rows += (
            f'<tr><td>{label}</td>'
            f'<td class="text-right">{value}</td></tr>'
        )
    return rows


def create_unit_parameters_section(
    param_units: Dict[str, Any],
    unit_inputs: Dict[str, Any],
) -> str:
    """Create HTML for the per-unit technical/economic parameter tables."""
    tech_inputs = unit_inputs.get('Technische Parameter', {})
    econ_inputs = unit_inputs.get('Ökonomische Parameter', {})

    html = ''
    for unit, unit_params in sorted(param_units.items()):
        unit_cat = unit.rstrip('0123456789')
        unit_nr = unit[len(unit_cat):]
        title = f'{longnames.get(unit_cat, unit_cat)} {unit_nr}'.strip()

        invest_mode = unit_params.get('invest_mode', False)
        skip = DISP_OPT_PARAMS if invest_mode else COMB_OPT_PARAMS

        tech_rows = (
            '<tr><td>Kapazität optimieren</td>'
            f'<td class="text-right">{"Ja" if invest_mode else "Nein"}</td></tr>'
        )
        tech_rows += _param_rows_html(unit_params, tech_inputs, unit_cat, skip)
        econ_rows = _param_rows_html(unit_params, econ_inputs, unit_cat)

        html += f"""<div class="unit-param-block">
    <div class="subsection-title">{title}</div>
    <div class="grid-2">
        <div>
            <table>
                <tr><th>Technische Parameter</th><th class="text-right">Wert</th></tr>
                {tech_rows}
            </table>
        </div>
        <div>
            <table>
                <tr><th>Ökonomische Parameter</th><th class="text-right">Wert</th></tr>
                {econ_rows}
            </table>
        </div>
    </div>
</div>
"""

    return html


def create_kpi_cards(key_params: Dict[str, Any]) -> str:
    """Create HTML for KPI cards."""
    kpi_template = Template(get_kpi_card_template())

    kpi_labels = {
        'LCOH': 'Wärmegestehungskosten (€/MWh)',
        'LCOH_incl_net': 'LCOH inkl. Netz (€/MWh)',
        'cost_total': 'Gesamtkosten (€)',
        'invest_total': 'Investitionskosten (€)',
        'op_cost_total': 'Gesamtbetriebskosten (€)',
        'revenues_total': 'Gesamterlöse (€)',
        'total_heat_demand': 'Gesamtwärmebedarf (MWh)',
        'Total Emissions OM': 'Gesamtemissionen (t)',
    }

    cards_html = []
    for key, label in kpi_labels.items():
        if key in key_params:
            value = key_params[key]

            # Format based on unit
            if 'emission' in label.lower():
                value = format_number(value / 1e3, 0)
            elif '€/MWh' in label:
                value = format_number(value, 2)
            else:
                value = format_number(value, 0)

            card_html = kpi_template.render(label=label, value=value)
            cards_html.append(card_html)

    return '\n'.join(cards_html)


def create_capacities_table(overview_caps: pd.DataFrame) -> str:
    """Create HTML table for capacities."""
    df = overview_caps.T.copy()
    df = df.map(lambda x: format_number(x, 1) if isinstance(x, (int, float)) else x)

    html = '<table>'
    html += '<tr><th>Anlage</th><th class="text-right">Kapazität</th></tr>'

    for idx, row in df.iterrows():
        html += f'<tr><td>{idx}</td><td class="text-right">{row.iloc[0]}</td></tr>'

    html += '</table>'
    return html


def create_costs_table(cost_df: pd.DataFrame, key_params: Dict[str, Any]) -> str:
    """Create HTML table for cost breakdown."""
    unit_cost = cost_df.copy()

    # Add network costs
    unit_cost.loc['invest', 'Wärmenetz'] = key_params.get('invest_net_total', 0)
    unit_cost.loc['op_cost_fix', 'Wärmenetz'] = key_params.get('cost_net_fix_total', 0)
    unit_cost.loc['op_cost_var', 'Wärmenetz'] = key_params.get('cost_net_var_total', 0)
    unit_cost.loc['op_cost', 'Wärmenetz'] = (
        key_params.get('cost_net_fix_total', 0) + key_params.get('cost_net_var_total', 0)
    )

    # Rename index
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

    # Format values
    unit_cost = unit_cost.map(
        lambda x: format_number(int(x), 0)
        if isinstance(x, (int, float))
        else x
    )

    html = '<table>'
    html += '<tr><th></th>'
    for unit in unit_cost.columns:
        ucat = unit.rstrip('0123456789')
        unr = unit[len(ucat):]
        if ucat in longnames.keys():
            unit = f'{longnames[ucat]} {unr}'
        html += f'<th class="text-right">{unit}</th>'
    html += '</tr>'

    for idx, row in unit_cost.iterrows():
        html += f'<tr><td>{idx}</td>'
        for val in row:
            html += f'<td class="text-right">{val}</td>'
        html += '</tr>'

    html += '</table>'
    return html


def create_emission_cards(key_params: Dict[str, Any]) -> str:
    """Create HTML for emission KPI cards."""
    kpi_template = Template(get_kpi_card_template())

    emission_labels = {
        'Total Emissions OM': 'Gesamtemissionen (t)',
        'Emissions OM (Gas)': 'Durch Gasbezug (t)',
        'Emissions OM (Electricity)': 'Durch Strombezug (t)',
        'Emissions OM (Spotmarket)': 'Gutschriften (t)',
    }

    cards_html = []
    for key, label in emission_labels.items():
        if key in key_params:
            value = format_number(key_params[key] / 1e3, 0)
            card_html = kpi_template.render(label=label, value=value)
            cards_html.append(card_html)

    return '\n'.join(cards_html)


def create_parameters_table(param_opt: Dict[str, Any]) -> str:
    """Create HTML table for optimization parameters."""
    param_labels = {
        'Solver': 'Optimierungsalgorithmus',
        'capital_interest': 'Kapitalzinssatz (%)',
        'lifetime': 'Anlagenlebensdauer (Jahre)',
        'ef_gas': 'Emissionsfaktor Gas (kg CO2/MWh)',
    }

    html = '<table>'
    html += '<tr><th>Parameter</th><th class="text-right">Wert</th></tr>'

    for key, label in param_labels.items():
        if key in param_opt:
            value = param_opt[key]
            if key == 'capital_interest':
                value *= 100
                value = format_number(value, 0)
            elif key == 'ef_gas':
                value = format_number(value, 3)
            html += f'<tr><td>{label}</td><td class="text-right">{value}</td></tr>'

    html += '</table>'
    return html


def create_overview_table(energy_system):
    """Create HTML table for input time series overview."""
    data_overview = energy_system.data.describe()
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

    sol_used = any([
        u.rstrip('0123456789') == 'sol'
        for u in energy_system.param_units.keys()
        ])
    if sol_used:
        data_overview['solar_heat_flow'] *= 1e6
        data_overview.rename(columns={
            'solar_heat_flow': 'Spez. solare Einstrahlung (Wh/m²)'
            }, inplace=True
        )

    data_overview = data_overview.map(lambda x: f'{x:.2f}')
    data_overview = data_overview.T.reset_index().rename(columns={'index': ''})

    return data_overview.to_html(index=False, border=False)


def altair_to_vega_spec(chart: alt.Chart) -> Dict[str, Any]:
    """Convert Altair chart to Vega-Lite specification."""
    try:
        spec = chart.to_dict()
        return spec
    except Exception:
        return {}


def create_chart_rendering_script(charts: Dict[str, Dict[str, Any]]) -> str:
    """Create JavaScript to render Vega-Lite charts."""
    embed_calls = ""

    for chart_id, spec in charts.items():
        if spec:
            spec_json = json.dumps(spec)
            embed_calls += f"""
vegaEmbed('#{chart_id}', {spec_json}, {{"actions": false}})
    .then(result => {{}})
    .catch(console.error);
"""

    offline_notice = (
        '<div class="chart-offline-notice">'
        '<p class="chart-offline-title">Diagramme nicht verfügbar</p>'
        '<p>Für die Darstellung der Diagramme ist eine Internetverbindung erforderlich,'
        ' da die Vega-Bibliothek von einem externen Server geladen wird.</p>'
        '</div>'
    )

    return f"""if (typeof vegaEmbed === 'undefined') {{
    document.querySelectorAll('.chart-container').forEach(function(el) {{
        el.innerHTML = '{offline_notice}';
    }});
}} else {{{embed_calls}}}"""


def create_topology_section(
    overview_caps: pd.DataFrame,
    energy_system,
    param_units: Dict[str, Any],
    img_path: str,
) -> str:
    """
    Create topology images section showing installed units.

    Parameters
    ----------
    overview_caps : pd.DataFrame
        Capacity overview dataframe
    energy_system : EnergySystem
        Energy system object
    param_units : Dict
        Unit parameters
    img_path : str
        Path to image directory

    Returns
    -------
    str
        HTML containing topology images
    """
    html = '<div class="image-container">'

    # Header image
    header_path = os.path.join(img_path, 'es_topology_header.png')
    html += f'<img src="{encode_image_to_base64(header_path)}" style="max-width: 100%;">'

    # Unit topology images (only for units with capacity > 0)
    for unit in param_units.keys():
        cap_col = f'cap_{unit}'
        if cap_col in energy_system.data_caps.columns:
            if energy_system.data_caps.loc[0, cap_col] > 0:
                ucat = unit.rstrip('0123456789')
                unit_img_path = os.path.join(img_path, f'es_topology_{ucat}.png')
                if os.path.exists(unit_img_path):
                    html += f'<br><img src="{encode_image_to_base64(unit_img_path)}" style="max-width: 100%; margin-top: 15px;">'

    html += '</div>'
    return html


def generate_html_report(
    energy_system,
    overview_caps: pd.DataFrame,
    param_units: Dict[str, Any],
    param_opt: Dict[str, Any],
    unit_inputs: Dict[str, Any],
    img_path: str,
) -> str:
    """
    Generate complete HTML report.

    Parameters
    ----------
    energy_system : EnergySystem
        The optimized energy system object
    overview_caps : pd.DataFrame
        Capacity overview dataframe
    param_units : Dict
        Unit parameters
    param_opt : Dict
        Optimization parameters
    unit_inputs : Dict
        Unit parameter infos
    img_path : str
        Path to image directory

    Returns
    -------
    str
        Complete HTML report as string
    """
    # Prepare KPI data
    key_params = energy_system.key_params

    # Generate KPI cards
    kpi_cards = create_kpi_cards(key_params)

    # Generate capacities table
    capacities_table = create_capacities_table(overview_caps)

    # Generate costs table
    costs_table = create_costs_table(energy_system.cost_df, key_params)

    # Generate emissions cards
    emission_cards = create_emission_cards(key_params)

    # Generate input time series overview table
    overview_table = create_overview_table(energy_system)

    # Generate parameters table
    parameters_table = create_parameters_table(param_opt)

    # Generate per-unit parameters section
    unit_parameters = create_unit_parameters_section(param_units, unit_inputs)

    # Encode topology image
    topology_path = os.path.join(img_path, 'es_topology_header.png')
    # Encode topology images with installed units
    topology_html = create_topology_section(overview_caps, energy_system, param_units, img_path)

    # Create charts using reusable functions
    heat_prod_chart = create_heat_production_chart(energy_system, param_units)
    duration_chart = create_ordered_duration_line_chart(energy_system, param_units)
    dispatch_chart = create_dispatch_timeseries_chart(energy_system, param_units)

    chart_specs = {
        'heat-production-chart': altair_to_vega_spec(heat_prod_chart),
        'duration-line-chart': altair_to_vega_spec(duration_chart),
        'dispatch-timeseries-chart': altair_to_vega_spec(dispatch_chart)
    }

    if energy_system.chp_used:
        el_prod_grid_chart = create_el_prod_grid_chart(energy_system)
        el_prod_internal_chart = create_el_prod_internal_chart(energy_system)

        chart_specs.update({
            'el-prod-grid-chart': altair_to_vega_spec(el_prod_grid_chart),
            'el-prod-internal-chart': altair_to_vega_spec(el_prod_internal_chart)
        })

    if energy_system.tes_used:
        for unit in param_units.keys():
            if unit.rstrip('01234156789') != 'tes':
                continue

            tes_content_chart = create_tes_content_chart(energy_system, unit)
            chart_specs.update({
                f'{unit}-content-chart': altair_to_vega_spec(tes_content_chart)
            })

    # Create chart rendering script
    chart_rendering_script = create_chart_rendering_script(chart_specs)

    # Prepare timestamp
    timestamp = dt.datetime.now().strftime('%d.%m.%Y %H:%M:%S')

    # Get solver status
    solver_status = 'Optimal' if hasattr(energy_system, 'status') else 'Completed'

    # Prepare chart sections HTML
    chart_sections_html = """
    <div class="section">
        <div class="section-title">Anlageneinsatz</div>

        <div class="subsection-title">Geordnete Jahresdauerlinien</div>
        <div class="chart-container">
            <div id="duration-line-chart"></div>
        </div>

        <div class="subsection-title">Zeitreihe</div>
        <div class="chart-container">
            <div id="dispatch-timeseries-chart"></div>
        </div>
    </div>
    """

    if energy_system.chp_used:
        chart_sections_html += """
            <div class="section">
                <div class="section-title">Stromproduktion</div>

                <div class="subsection-title">Netzeinspeisung</div>
                <div class="chart-container">
                    <div id="el-prod-grid-chart"></div>
                </div>

                <div class="subsection-title">Interne Nutzung</div>
                <div class="chart-container">
                    <div id="el-prod-internal-chart"></div>
                </div>
            </div>
        """

    if energy_system.tes_used:
        chart_sections_html += """
            <div class="section">
                <div class="section-title">Speicherstand</div>

        """

        for unit in param_units.keys():
            unit_cat = unit.rstrip('0123456789')
            unit_nr = unit[len(unit_cat):]
            if unit_cat != 'tes':
                continue

            chart_sections_html += f"""
                    <div class="subsection-title">Wärmespeicher {unit_nr}</div>
                    <div class="chart-container">
                        <div id="{unit}-content-chart"></div>
                    </div>
            """
        chart_sections_html += '</div>'

    # Render main template
    main_template = Template(get_report_template())

    report_content = main_template.render(
        title='Optimierungsbericht Offene Wärmespeicherplanung',
        timestamp=timestamp,
        solver=param_opt.get('Solver', 'Unbekannt'),
        status=solver_status,
        kpi_cards=kpi_cards,
        capacities_table=capacities_table,
        parameters_table=parameters_table,
        unit_parameters=unit_parameters,
        overview_table=overview_table,
        costs_table=costs_table,
        topology_image=topology_html,
        emission_cards=emission_cards,
        chart_sections=chart_sections_html,
        chart_specs=chart_rendering_script,
    )

    # Combine CSS and content
    html = REPORT_CSS + report_content

    return html

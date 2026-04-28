"""Report generation module for optimization results."""

import base64
import datetime as dt
import json
import os
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


def altair_to_vega_spec(chart: alt.Chart) -> Dict[str, Any]:
    """Convert Altair chart to Vega-Lite specification."""
    try:
        spec = chart.to_dict()
        return spec
    except Exception:
        return {}


def create_chart_rendering_script(charts: Dict[str, Dict[str, Any]]) -> str:
    """Create JavaScript to render Vega-Lite charts."""
    script = ""

    for chart_id, spec in charts.items():
        if spec:
            spec_json = json.dumps(spec)
            script += f"""
vegaEmbed('#{chart_id}', {spec_json}, {{"actions": false}})
    .then(result => {{}})
    .catch(console.error);
"""

    return script


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

    # Generate parameters table
    parameters_table = create_parameters_table(param_opt)

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
        costs_table=costs_table,
        topology_image=topology_html,
        emission_cards=emission_cards,
        chart_sections=chart_sections_html,
        chart_specs=chart_rendering_script,
    )

    # Combine CSS and content
    html = REPORT_CSS + report_content

    return html

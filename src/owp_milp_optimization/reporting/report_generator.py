"""Report generation module for optimization results."""

import base64
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict

import altair as alt
import pandas as pd
from jinja2 import Template

from owp_milp_optimization.helpers import get_language, txt

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
unit_name_keys = {
    'hp': 'energy_system.unit.heat_pump',
    'ccet': 'energy_system.unit.combined_cycle',
    'ice': 'energy_system.unit.chp',
    'sol': 'energy_system.unit.solar_thermal',
    'plb': 'report.unit.peak_load_boiler',
    'eb': 'energy_system.unit.electrode_boiler',
    'exhs': 'energy_system.unit.external_heat_source',
    'tes': 'energy_system.unit.thermal_storage'
}


def get_unit_name(unit_cat: str) -> str:
    """Return translated display name for an energy system unit category."""
    return txt(unit_name_keys.get(unit_cat, unit_cat))

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
    """Format number with thousand separators according to the UI language."""
    if pd.isna(value):
        return '-'

    formatted = f'{value:,.{decimals}f}'
    if get_language() == 'de':
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted


def create_kpi_cards(key_params: Dict[str, Any]) -> str:
    """Create HTML for KPI cards."""
    kpi_template = Template(get_kpi_card_template())

    kpi_label_keys = {
        'LCOH': 'report.kpi.lcoh',
        'LCOH_incl_net': 'report.kpi.lcoh_including_network',
        'cost_total': 'report.kpi.total_costs',
        'invest_total': 'results.costs.investment',
        'op_cost_total': 'results.costs.total_operating',
        'revenues_total': 'report.kpi.total_revenues',
        'total_heat_demand': 'report.kpi.total_heat_demand',
        'Total Emissions OM': 'report.kpi.total_emissions',
    }

    cards_html = []
    for key, label_key in kpi_label_keys.items():
        if key in key_params:
            label = txt(label_key)
            value = key_params[key]

            # Format based on result type
            if key == 'Total Emissions OM':
                value = format_number(value / 1e3, 0)
            elif key in {'LCOH', 'LCOH_incl_net'}:
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
    html += (
        f'<tr><th>{txt("report.table.unit")}</th>'
        f'<th class="text-right">{txt("results.overview.capacity.row_label")}</th></tr>'
    )

    for idx, row in df.iterrows():
        html += f'<tr><td>{idx}</td><td class="text-right">{row.iloc[0]}</td></tr>'

    html += '</table>'
    return html


def create_costs_table(cost_df: pd.DataFrame, key_params: Dict[str, Any]) -> str:
    """Create HTML table for cost breakdown."""
    unit_cost = cost_df.copy()

    # Add network costs
    network_label = txt('report.table.network')
    unit_cost.loc['invest', network_label] = key_params.get('invest_net_total', 0)
    unit_cost.loc['op_cost_fix', network_label] = key_params.get('cost_net_fix_total', 0)
    unit_cost.loc['op_cost_var', network_label] = key_params.get('cost_net_var_total', 0)
    unit_cost.loc['op_cost', network_label] = (
        key_params.get('cost_net_fix_total', 0) + key_params.get('cost_net_var_total', 0)
    )

    unit_cost.drop('op_cost', axis=0, inplace=True)

    # Rename index
    unit_cost.rename(
        index={
            'invest': txt('results.costs.investment'),
            'op_cost_var': txt('results.costs.variable_operating'),
            'op_cost_fix': txt('results.costs.fixed_operating'),
        },
        inplace=True
    )

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
        if ucat in unit_name_keys.keys():
            unit = f'{get_unit_name(ucat)} {unr}'
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

    emission_label_keys = {
        'Total Emissions OM': 'report.emissions.total',
        'Emissions OM (Gas)': 'report.emissions.gas_supply',
        'Emissions OM (Electricity)': 'report.emissions.electricity_supply',
        'Emissions OM (Spotmarket)': 'report.emissions.credits',
    }

    cards_html = []
    for key, label_key in emission_label_keys.items():
        if key in key_params:
            value = format_number(key_params[key] / 1e3, 0)
            card_html = kpi_template.render(label=txt(label_key), value=value)
            cards_html.append(card_html)

    return '\n'.join(cards_html)


def create_parameters_table(param_opt: Dict[str, Any]) -> str:
    """Create HTML table for optimization parameters."""
    param_label_keys = {
        'Solver': 'report.parameters.solver',
        'capital_interest': 'report.parameters.capital_interest',
        'lifetime': 'report.parameters.lifetime',
        'ef_gas': 'report.parameters.gas_emission_factor',
    }

    html = '<table>'
    html += (
        f'<tr><th>{txt("common.parameter")}</th>'
        f'<th class="text-right">{txt("common.value")}</th></tr>'
    )

    for key, label_key in param_label_keys.items():
        if key in param_opt:
            value = param_opt[key]
            if key == 'capital_interest':
                value *= 100
                value = format_number(value, 0)
            elif key == 'ef_gas':
                value = format_number(value, 3)
            html += f'<tr><td>{txt(label_key)}</td><td class="text-right">{value}</td></tr>'

    html += '</table>'
    return html


def create_overview_table(energy_system):
    """Create HTML table for input time series overview."""
    data_overview = energy_system.data.describe()
    data_overview.drop(index=['count', 'std', '25%', '75%'], inplace=True)
    data_overview.rename(
        index={
            'mean': txt('common.statistics.mean'),
            'min': txt('common.statistics.minimum'),
            '50%': txt('common.statistics.median'),
            'max': txt('common.statistics.maximum')
            },
        columns={
            'heat_demand': txt('optimization.overview.timeseries.heat_demand'),
            'el_spot_price': txt('optimization.overview.timeseries.electricity_spot_price'),
            'ef_om': txt('optimization.overview.timeseries.electricity_emission_factor'),
            'gas_price': txt('optimization.overview.timeseries.gas_price'),
            'co2_price': txt('optimization.overview.timeseries.co2_price')
            }, inplace=True
        )

    sol_used = any([
        u.rstrip('0123456789') == 'sol'
        for u in energy_system.param_units.keys()
        ])
    if sol_used:
        data_overview['solar_heat_flow'] *= 1e6
        data_overview.rename(columns={
            'solar_heat_flow': txt('optimization.overview.timeseries.solar_heat_flow')
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
        f'<p class="chart-offline-title">{txt("report.charts.offline.title")}</p>'
        f'<p>{txt("report.charts.offline.text")}</p>'
        '</div>'
    )
    offline_notice_json = json.dumps(offline_notice)

    return f"""if (typeof vegaEmbed === 'undefined') {{
    document.querySelectorAll('.chart-container').forEach(function(el) {{
        el.innerHTML = {offline_notice_json};
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

    # Generate input time series overview table
    overview_table = create_overview_table(energy_system)

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
    date_format = '%d.%m.%Y %H:%M:%S' if get_language() == 'de' else '%Y-%m-%d %H:%M:%S'
    timestamp = dt.datetime.now().strftime(date_format)

    # Get solver status
    solver_status = (
        txt('report.status.optimal')
        if hasattr(energy_system, 'status')
        else txt('report.status.completed')
    )

    # Prepare chart sections HTML
    chart_sections_html = f"""
    <div class="section">
        <div class="section-title">{txt('results.tabs.unit_commitment')}</div>

        <div class="subsection-title">{txt('report.charts.duration_lines')}</div>
        <div class="chart-container">
            <div id="duration-line-chart"></div>
        </div>

        <div class="subsection-title">{txt('report.charts.timeseries')}</div>
        <div class="chart-container">
            <div id="dispatch-timeseries-chart"></div>
        </div>
    </div>
    """

    if energy_system.chp_used:
        chart_sections_html += f"""
            <div class="section">
                <div class="section-title">{txt('results.tabs.electricity_production')}</div>

                <div class="subsection-title">{txt('report.charts.grid_feed_in')}</div>
                <div class="chart-container">
                    <div id="el-prod-grid-chart"></div>
                </div>

                <div class="subsection-title">{txt('report.charts.internal_use')}</div>
                <div class="chart-container">
                    <div id="el-prod-internal-chart"></div>
                </div>
            </div>
        """

    if energy_system.tes_used:
        chart_sections_html += f"""
            <div class="section">
                <div class="section-title">{txt('results.tabs.storage_content')}</div>

        """

        for unit in param_units.keys():
            unit_cat = unit.rstrip('0123456789')
            unit_nr = unit[len(unit_cat):]
            if unit_cat != 'tes':
                continue

            chart_sections_html += f"""
                    <div class="subsection-title">{txt('results.storage.unit_label', unit=unit_nr)}</div>
                    <div class="chart-container">
                        <div id="{unit}-content-chart"></div>
                    </div>
            """
        chart_sections_html += '</div>'

    # Render main template
    main_template = Template(get_report_template())

    report_content = main_template.render(
        title=txt('report.title'),
        timestamp=timestamp,
        solver=param_opt.get('Solver', txt('report.status.unknown')),
        status=solver_status,
        kpi_cards=kpi_cards,
        capacities_table=capacities_table,
        parameters_table=parameters_table,
        overview_table=overview_table,
        costs_table=costs_table,
        topology_image=topology_html,
        emission_cards=emission_cards,
        chart_sections=chart_sections_html,
        chart_specs=chart_rendering_script,
    )

    # Combine CSS and content
    css = REPORT_CSS.replace('report.title_html_head', txt('report.title_html_head'))
    html = css + report_content

    return html

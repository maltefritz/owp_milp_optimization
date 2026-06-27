"""Chart generation utilities for both Streamlit and reporting."""

from typing import Dict, Tuple

import altair as alt
import numpy as np
import pandas as pd

from helpers import txt

COLORS_BY_UNIT_CAT = {
    'hp': '#B54036',
    'ccet': '#00395B',
    'ice': '#00395B',
    'plb': '#EC6707',
    'gb': '#EC6707',
    'sol': '#EC6707',
    'eb': '#EC6707',
    'exhs': '#74ADC0',
    'tes_in': 'slategrey',
    'tes_out': 'dimgrey',
    'heat_demand': '#31333f',
}

UNIT_NAME_KEYS = {
    'hp': 'energy_system.unit.heat_pump',
    'ccet': 'energy_system.unit.combined_cycle',
    'ice': 'energy_system.unit.chp',
    'sol': 'energy_system.unit.solar_thermal',
    'gb': 'energy_system.unit.gas_boiler',
    'plb': 'report.unit.peak_load_boiler',
    'eb': 'energy_system.unit.electrode_boiler',
    'exhs': 'energy_system.unit.external_heat_source',
    'tes': 'energy_system.unit.thermal_storage',
}


# Configure Altair to handle large datasets (up to 8760+ for yearly hourly data)
alt.data_transformers.enable('default', max_rows=None)


def get_unit_name(unit_cat: str) -> str:
    """Return translated display name for an energy system unit category."""
    return txt(UNIT_NAME_KEYS.get(unit_cat, unit_cat))


def get_unit_label(unit: str) -> str:
    """Return translated display label for a concrete unit such as hp1."""
    unit_cat = unit.rstrip('0123456789')
    unit_nr = unit[len(unit_cat):]
    return f'{get_unit_name(unit_cat)} {unit_nr}'.strip()


def get_storage_flow_label(unit: str, flow: str) -> str:
    """Return translated display label for thermal storage charge/discharge."""
    unit_cat = unit.rstrip('0123456789')
    unit_nr = unit[len(unit_cat):]
    flow_label_key = (
        'results.storage.charge_label'
        if flow == 'in'
        else 'results.storage.discharge_label'
    )
    return f'{get_unit_name(unit_cat)} {unit_nr} {txt(flow_label_key)}'.strip()


def create_heat_production_dataframe(
    energy_system,
    param_units: Dict,
) -> Tuple[pd.DataFrame, Dict[str, str], set[str], str]:
    """Create translated heat production dataframe and matching color metadata."""
    heatprod = pd.DataFrame()
    label_colors = {}
    storage_charge_labels = set()
    demand_label = txt('results.common.heat_demand')

    for col in energy_system.data_all.columns:
        if 'Q_' not in col or energy_system.data_all[col].sum() <= 0:
            continue

        this_unit = None
        for unit in param_units.keys():
            if unit in col:
                this_unit = unit
                break

        if this_unit is None:
            collabel = demand_label
            label_colors[collabel] = COLORS_BY_UNIT_CAT['heat_demand']
        else:
            this_unit_cat = this_unit.rstrip('0123456789')

            if this_unit_cat == 'tes':
                if '_in' in col:
                    collabel = get_storage_flow_label(this_unit, 'in')
                    label_colors[collabel] = COLORS_BY_UNIT_CAT['tes_in']
                    storage_charge_labels.add(collabel)
                elif '_out' in col:
                    collabel = get_storage_flow_label(this_unit, 'out')
                    label_colors[collabel] = COLORS_BY_UNIT_CAT['tes_out']
                else:
                    collabel = get_unit_label(this_unit)
                    label_colors[collabel] = COLORS_BY_UNIT_CAT.get(
                        this_unit_cat,
                        '#999999',
                    )
            else:
                collabel = get_unit_label(this_unit)
                label_colors[collabel] = COLORS_BY_UNIT_CAT.get(
                    this_unit_cat,
                    '#999999',
                )

        heatprod[collabel] = energy_system.data_all[col].copy()

    return heatprod, label_colors, storage_charge_labels, demand_label


def create_heat_production_chart(
    energy_system,
    param_units: Dict,
) -> alt.Chart:
    """
    Create bar chart of total heat production by unit.

    Parameters
    ----------
    energy_system : EnergySystem
        Energy system with optimization results
    param_units : Dict
        Unit parameters

    Returns
    -------
    alt.Chart
        Altair bar chart
    """
    qsum = pd.DataFrame(columns=['unit', 'qsum'])
    idx = 0

    for unit in param_units.keys():
        ucat = unit.rstrip('0123456789')

        if ucat == 'tes':
            for flow in ['in', 'out']:
                unit_col = f'Q_{flow}_{unit}'
                qsum.loc[idx, 'unit'] = get_storage_flow_label(unit, flow)
                qsum.loc[idx, 'qsum'] = energy_system.data_all[unit_col].sum()
                idx += 1
        else:
            unit_col = f'Q_out_{unit}' if ucat in ['hp', 'tes'] else f'Q_{unit}'
            qsum.loc[idx, 'unit'] = get_unit_label(unit)
            qsum.loc[idx, 'qsum'] = energy_system.data_all[unit_col].sum()
            idx += 1

    return alt.Chart(qsum).mark_bar(color='#B54036').encode(
        y=alt.Y('unit', title=None),
        x=alt.X('qsum', title=txt('results.chart.total_heat_supply_mwh'))
    ).properties(width=800)


def create_ordered_duration_line_chart(
    energy_system,
    param_units: Dict,
) -> alt.Chart:
    """
    Create ordered annual duration line chart.

    Parameters
    ----------
    energy_system : EnergySystem
        Energy system with optimization results
    param_units : Dict
        Unit parameters

    Returns
    -------
    alt.Chart
        Altair line chart
    """
    heatprod, label_colors, _, _ = create_heat_production_dataframe(
        energy_system,
        param_units,
    )

    duration_col = 'duration_rank'
    supply_unit_col = 'supply_unit'
    hourly_label = txt('results.aggregation.period_label.hourly')

    heatprod_sorted = pd.DataFrame(
        np.sort(heatprod.values, axis=0)[::-1], columns=heatprod.columns
    )
    heatprod_sorted.index.names = [duration_col]
    heatprod_sorted.reset_index(inplace=True)

    hprod_sorted_melt = heatprod_sorted.melt(duration_col)
    hprod_sorted_melt.rename(
        columns={'variable': supply_unit_col},
        inplace=True,
    )

    units = list(hprod_sorted_melt[supply_unit_col].unique())
    return alt.Chart(hprod_sorted_melt).mark_line().encode(
        y=alt.Y(
            'value',
            title=txt('results.chart.heat_production_mwh', period=hourly_label),
        ),
        x=alt.X(duration_col, title=txt('results.chart.count_axis')),
        color=alt.Color(supply_unit_col, title=txt('results.common.supply_unit')).scale(
            domain=units,
            range=[label_colors.get(unit, '#999999') for unit in units]
        )
    ).properties(width=600)


def create_dispatch_timeseries_chart(
    energy_system,
    param_units: Dict,
    start_date=None,
    end_date=None,
) -> alt.Chart:
    """
    Create time series dispatch chart (line plot of actual unit dispatch).

    Parameters
    ----------
    energy_system : EnergySystem
        Energy system with optimization results
    param_units : Dict
        Unit parameters
    start_date : datetime, optional
        Start date for time series (defaults to first time step)
    end_date : datetime, optional
        End date for time series (defaults to last time step)

    Returns
    -------
    alt.Chart
        Altair line chart
    """
    heatprod, label_colors, storage_charge_labels, demand_label = (
        create_heat_production_dataframe(energy_system, param_units)
    )

    if start_date is None:
        start_date = heatprod.index[0]
    if end_date is None:
        end_date = heatprod.index[-1]

    heatprod = heatprod.loc[start_date:end_date, :]

    for col in heatprod.columns:
        if col in storage_charge_labels:
            heatprod[col] *= -1

    if demand_label in heatprod.columns:
        heatprod = heatprod.drop(columns=[demand_label])

    heatprod = heatprod.resample('ME').sum()

    heatprod.index.names = ['Date']
    heatprod.reset_index(inplace=True)

    supply_unit_col = 'supply_unit'
    monthly_label = txt('results.aggregation.period_label.monthly')

    hprod_melt = heatprod.melt('Date')
    hprod_melt.rename(columns={'variable': supply_unit_col}, inplace=True)

    units = list(hprod_melt[supply_unit_col].unique())
    return alt.Chart(hprod_melt).mark_bar().encode(
        y=alt.Y(
            'value',
            title=txt('results.chart.heat_production_mwh', period=monthly_label)
        ),
        x=alt.X('yearmonth(Date):O', title=txt('common.date')),
        color=alt.Color(supply_unit_col, title=txt('results.common.supply_unit')).scale(
            domain=units,
            range=[label_colors.get(unit, '#999999') for unit in units]
        )
    ).properties(width=600)


def create_el_prod_grid_chart(
    energy_system,
    start_date=None,
    end_date=None,
) -> alt.Chart:
    """
    Create time series el. grid production chart.

    Parameters
    ----------
    energy_system : EnergySystem
        Energy system with optimization results
    start_date : datetime, optional
        Start date for time series (defaults to first time step)
    end_date : datetime, optional
        End date for time series (defaults to last time step)

    Returns
    -------
    alt.Chart
        Altair line chart
    """
    if start_date is None:
        start_date = energy_system.data_all.index[0]
    if end_date is None:
        end_date = energy_system.data_all.index[-1]

    elprod = pd.DataFrame(
        columns=['P_spotmarket']
    )

    elprod['P_spotmarket'] = energy_system.data_all.loc[
        start_date:end_date, 'P_spotmarket'
    ]

    elprod = elprod.resample('W').sum()

    ymax = energy_system.data_all.loc[
        start_date:end_date, ['P_spotmarket', 'P_internal']
        ].resample('W').sum().max().max()
    ymax *= 1.05

    elprod.index.names = ['Date']
    elprod.reset_index(inplace=True)

    return alt.Chart(elprod).mark_bar(color='#00395B').encode(
        y=alt.Y(
            'P_spotmarket',
            title=txt('charts.axis.weekly_grid_feed_in_mwh'),
            scale=alt.Scale(domain=[0, ymax])
        ),
        x=alt.X('yearweek(Date):O', title=txt('common.date'))
    ).properties(width=600)


def create_el_prod_internal_chart(
    energy_system,
    start_date=None,
    end_date=None,
) -> alt.Chart:
    """
    Create time series el. internal usage chart.

    Parameters
    ----------
    energy_system : EnergySystem
        Energy system with optimization results
    start_date : datetime, optional
        Start date for time series (defaults to first time step)
    end_date : datetime, optional
        End date for time series (defaults to last time step)

    Returns
    -------
    alt.Chart
        Altair line chart
    """
    if start_date is None:
        start_date = energy_system.data_all.index[0]
    if end_date is None:
        end_date = energy_system.data_all.index[-1]

    elprod = pd.DataFrame(
        columns=['P_internal']
    )

    elprod['P_internal'] = energy_system.data_all.loc[
        start_date:end_date, 'P_internal'
    ]

    elprod = elprod.resample('W').sum()

    ymax = energy_system.data_all.loc[
        start_date:end_date, ['P_spotmarket', 'P_internal']
        ].resample('W').sum().max().max()
    ymax *= 1.05

    elprod.index.names = ['Date']
    elprod.reset_index(inplace=True)

    return alt.Chart(elprod).mark_bar(color='#74ADC0').encode(
        y=alt.Y(
            'P_internal',
            title=txt('charts.axis.weekly_internal_electricity_mwh'),
            scale=alt.Scale(domain=[0, ymax])
        ),
        x=alt.X('yearweek(Date):O', title=txt('common.date'))
    ).properties(width=600)


def create_tes_content_chart(
    energy_system,
    unit,
    start_date=None,
    end_date=None,
) -> alt.Chart:
    """
    Create time series TES storage content chart.

    Parameters
    ----------
    energy_system : EnergySystem
        Energy system with optimization results
    unit : str
        Unit shortname including its number (e.g. 'tes1').
    start_date : datetime, optional
        Start date for time series (defaults to first time step)
    end_date : datetime, optional
        End date for time series (defaults to last time step)

    Returns
    -------
    alt.Chart
        Altair line chart
    """
    if start_date is None:
        start_date = energy_system.data_all.index[0]
    if end_date is None:
        end_date = energy_system.data_all.index[-1]

    tesdata = energy_system.data_all.loc[
        start_date:end_date,
        f'storage_content_{unit}'
        ].copy().to_frame()

    tesdata.index.names = ['Date']
    tesdata.reset_index(inplace=True)

    return alt.Chart(tesdata).mark_line(color='#EC6707').encode(
        y=alt.Y(
            f'storage_content_{unit}',
            title=txt('results.storage.chart.content_mwh')
        ),
        x=alt.X('Date', title=txt('common.date'))
    ).properties(width=600)

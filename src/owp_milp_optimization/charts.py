"""Chart generation utilities for both Streamlit and reporting."""

import re
from typing import Dict

import altair as alt
import numpy as np
import pandas as pd

COLORS = {
    'Wärmepumpe': '#B54036',
    'Gas- und Dampfkraftwerk': '#00395B',
    'Blockheizkraftwerk': '#00395B',
    'Spitzenlastkessel': '#EC6707',
    'Solarthermie': '#EC6707',
    'Wärmespeicher Ein': 'slategrey',
    'Wärmespeicher Aus': 'dimgrey',
    'Wärmebedarf': '#31333f',
    'Elektrodenheizkessel': '#EC6707',
    'Externe Wärmequelle': '#74ADC0'
}

LONGNAMES = {
    'hp': 'Wärmepumpe',
    'ccet': 'Gas- und Dampfkraftwerk',
    'ice': 'Blockheizkraftwerk',
    'sol': 'Solarthermie',
    'plb': 'Spitzenlastkessel',
    'eb': 'Elektrodenheizkessel',
    'exhs': 'Externe Wärmequelle',
    'tes': 'Wärmespeicher'
}


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
        unr = unit[len(ucat):]
        
        if ucat == 'tes':
            tl = {'in': 'Ein', 'out': 'Aus'}
            for var in ['in', 'out']:
                unit_col = f'Q_{var}_{unit}'
                qsum.loc[idx, 'unit'] = f'{LONGNAMES[ucat]} {unr} {tl[var]}'
                qsum.loc[idx, 'qsum'] = energy_system.data_all[unit_col].sum()
                idx += 1
        else:
            unit_col = f'Q_out_{unit}' if ucat in ['hp', 'tes'] else f'Q_{unit}'
            qsum.loc[idx, 'unit'] = f'{LONGNAMES[ucat]} {unr}'
            qsum.loc[idx, 'qsum'] = energy_system.data_all[unit_col].sum()
            idx += 1
    
    return alt.Chart(qsum).mark_bar(color='#B54036').encode(
        y=alt.Y('unit', title=None),
        x=alt.X('qsum', title='Gesamtwärmebereitstellung in MWh')
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
    heatprod = pd.DataFrame()
    for col in energy_system.data_all.columns:
        if 'Q_' in col and energy_system.data_all[col].sum() > 0:
            this_unit = None
            for unit in param_units.keys():
                if unit in col:
                    this_unit = unit
                    this_unit_cat = this_unit.rstrip('0123456789')
                    this_unit_nr = this_unit[len(this_unit_cat):]
            
            if this_unit is None:
                collabel = 'Wärmebedarf'
            elif this_unit.rstrip('0123456789') == 'tes':
                if '_in' in col:
                    collabel = f'{LONGNAMES[this_unit_cat]} {this_unit_nr} Ein'
                elif '_out' in col:
                    collabel = f'{LONGNAMES[this_unit_cat]} {this_unit_nr} Aus'
                else:
                    collabel = f'{LONGNAMES[this_unit_cat]} {this_unit_nr}'
            else:
                collabel = f'{LONGNAMES[this_unit_cat]} {this_unit_nr}'
            
            heatprod[collabel] = energy_system.data_all[col].copy()
    
    heatprod_sorted = pd.DataFrame(
        np.sort(heatprod.values, axis=0)[::-1], columns=heatprod.columns
    )
    heatprod_sorted.index.names = ['Stunde']
    heatprod_sorted.reset_index(inplace=True)
    
    hprod_sorted_melt = heatprod_sorted.melt('Stunde')
    hprod_sorted_melt.rename(columns={'variable': 'Versorgungsanlage'}, inplace=True)
    
    units = list(hprod_sorted_melt['Versorgungsanlage'].unique())
    return alt.Chart(hprod_sorted_melt).mark_line().encode(
        y=alt.Y('value', title='Stündliche Wärmeproduktion in MWh'),
        x=alt.X('Stunde', title='Anzahl'),
        color=alt.Color('Versorgungsanlage').scale(
            domain=units,
            range=[COLORS.get(re.sub(r'\s\d', '', s), '#999999') for s in units]
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
    heatprod = pd.DataFrame()
    for col in energy_system.data_all.columns:
        if 'Q_' in col and energy_system.data_all[col].sum() > 0:
            this_unit = None
            for unit in param_units.keys():
                if unit in col:
                    this_unit = unit
                    this_unit_cat = this_unit.rstrip('0123456789')
                    this_unit_nr = this_unit[len(this_unit_cat):]
            
            if this_unit is None:
                collabel = 'Wärmebedarf'
            elif this_unit.rstrip('0123456789') == 'tes':
                if '_in' in col:
                    collabel = f'{LONGNAMES[this_unit_cat]} {this_unit_nr} Ein'
                elif '_out' in col:
                    collabel = f'{LONGNAMES[this_unit_cat]} {this_unit_nr} Aus'
                else:
                    collabel = f'{LONGNAMES[this_unit_cat]} {this_unit_nr}'
            else:
                collabel = f'{LONGNAMES[this_unit_cat]} {this_unit_nr}'
            
            heatprod[collabel] = energy_system.data_all[col].copy()
    
    if start_date is None:
        start_date = heatprod.index[0]
    if end_date is None:
        end_date = heatprod.index[-1]
    
    heatprod = heatprod.loc[start_date:end_date, :]
    
    tes_used = any([u.rstrip('0123456789') == 'tes' for u in param_units.keys()])
    if tes_used:
        for col in heatprod.columns:
            if 'Wärmespeicher' in col and 'Ein' in col:
                heatprod[col] *= -1
    
    heatprod.index.names = ['Date']
    heatprod.reset_index(inplace=True)
    
    hprod_melt = heatprod.melt('Date')
    hprod_melt.rename(columns={'variable': 'Versorgungsanlage'}, inplace=True)
    
    units = list(hprod_melt['Versorgungsanlage'].unique())
    return alt.Chart(hprod_melt).mark_line().encode(
        y=alt.Y('value', title='Wärmeproduktion in MWh'),
        x=alt.X('Date', title='Datum'),
        color=alt.Color('Versorgungsanlage').scale(
            domain=units,
            range=[COLORS.get(re.sub(r'\s\d', '', s), '#999999') for s in units]
        )
    ).properties(width=600)

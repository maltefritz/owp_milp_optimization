"""Tests for building the oemof.solph energy system (no solver involved).

These tests check that ``EnergySystem`` translates the parameter dicts into
the intended oemof.solph nodes, flows and parameters.
"""
import copy

import numpy as np
import oemof.solph as solph
import pandas as pd
import pytest

from owp_milp_optimization.model import EnergySystem, calc_bwsf

ALL_CATS = ['hp', 'ccet', 'ice', 'gb', 'eb', 'sol', 'exhs', 'tes']


def seq(values, n):
    """Materialize an oemof sequence (or scalar sequence) of length n."""
    return np.array([values[t] for t in range(n)], dtype=float)


def build(data, param_units, param_opt):
    es = EnergySystem(data, param_units, param_opt)
    es.generate_buses()
    es.generate_sources()
    es.generate_sinks()
    es.generate_components()
    return es


@pytest.fixture
def data(make_data):
    return make_data()


@pytest.fixture
def opt(make_opt):
    return make_opt()


@pytest.fixture
def all_units(make_unit):
    return {f'{cat}1': make_unit(cat) for cat in ALL_CATS}


@pytest.fixture
def es_all(data, all_units, opt):
    """Energy system with one unit of every type, built but not solved."""
    return build(data, all_units, opt)


def out_flow(es, unit, bus='hnw'):
    return es.comps[unit].outputs[es.buses[bus]]


def in_flow(es, unit, bus):
    return es.comps[unit].inputs[es.buses[bus]]


# %% Constructor

@pytest.mark.parametrize('units, tes, chp, gas, el', [
    (['gb1'], False, False, True, False),
    (['hp1'], False, False, False, True),
    (['eb1'], False, False, False, True),
    (['ccet1'], False, True, True, True),
    (['ice2'], False, True, True, True),
    (['tes1', 'sol1'], True, False, False, False),
    (['exhs1'], False, False, False, False),
    (['hp12', 'gb3'], False, False, True, True),
    (['sol1', 'tes1', 'tes2', 'ice1'], True, True, True, True),
])
def test_usage_flags(units, tes, chp, gas, el, data, opt, make_unit):
    """Test wether xxx_used attributes are correctly infered from units."""
    param_units = {u: make_unit(u.rstrip('0123456789')) for u in units}
    es = EnergySystem(data, param_units, opt)
    assert (es.tes_used, es.chp_used, es.gas_used, es.el_used) == (
        tes, chp, gas, el
    )


def test_time_index_starts_at_data_and_is_hourly(data, opt, make_unit):
    es = EnergySystem(data, {'gb1': make_unit('gb')}, opt)
    assert es.periods == len(data)
    # infer_last_interval adds the end of the last time step
    assert len(es.es.timeindex) == len(data) + 1
    assert es.es.timeindex[0] == data.index[0]
    assert (np.diff(es.es.timeindex) == pd.Timedelta('1h')).all()


def test_bwsf_uses_capital_interest_and_lifetime(data, make_opt, make_unit):
    opt = make_opt(capital_interest=0.07, lifetime=15)
    es = EnergySystem(data, {'gb1': make_unit('gb')}, opt)
    assert es.bwsf == pytest.approx(calc_bwsf(0.07, 15))


def test_constructor_does_not_build_nodes(data, opt, make_unit):
    es = EnergySystem(data, {'gb1': make_unit('gb')}, opt)
    assert es.buses == {}
    assert es.comps == {}
    assert len(es.es.nodes) == 0

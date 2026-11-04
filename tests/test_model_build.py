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


# %% Topology

@pytest.mark.parametrize('units, buses, comps', [
    (
        ['gb1'],
        {'gnw', 'hnw'},
        {'gas_source', 'heat_sink', 'gb1'},
    ),
    (
        ['hp1', 'eb1'],
        {'enw', 'hnw'},
        {'elec_source', 'heat_sink', 'hp1', 'eb1'},
    ),
    (
        ['ccet1'],
        {'gnw', 'enw', 'hnw', 'chp_node'},
        {'gas_source', 'elec_source', 'heat_sink', 'elec_sink', 'ccet1',
         'chp_internal'},
    ),
    (
        ['sol1', 'exhs1', 'tes1'],
        {'hnw'},
        {'heat_sink', 'sol1', 'exhs1', 'tes1'},
    ),
    (
        ['gb1', 'gb2', 'hp1', 'hp2'],
        {'gnw', 'enw', 'hnw'},
        {'gas_source', 'elec_source', 'heat_sink', 'gb1', 'gb2', 'hp1', 'hp2'},
    ),
])
def test_topology(units, buses, comps, data, opt, make_unit):
    param_units = {u: make_unit(u.rstrip('0123456789')) for u in units}
    es = build(data, param_units, opt)
    assert set(es.buses) == buses
    assert set(es.comps) == comps


def test_all_nodes_are_added_to_solph_energy_system(es_all):
    expected = (
        {str(b.label) for b in es_all.buses.values()}
        | {str(c.label) for c in es_all.comps.values()}
    )
    assert {str(n.label) for n in es_all.es.nodes} == expected


def test_node_labels(es_all):
    assert {k: str(b.label) for k, b in es_all.buses.items()} == {
        'gnw': 'gas network',
        'enw': 'electricity network',
        'hnw': 'heat network',
        'chp_node': 'chp node',
    }
    labels = {k: str(c.label) for k, c in es_all.comps.items()}
    assert labels['gas_source'] == 'gas source'
    assert labels['elec_source'] == 'electricity source'
    assert labels['heat_sink'] == 'heat demand'
    assert labels['elec_sink'] == 'spotmarket'
    assert labels['chp_internal'] == 'chp internal'
    for cat in ALL_CATS:
        assert labels[f'{cat}1'] == f'{cat}1'


@pytest.mark.parametrize('unit, cls, inputs, outputs', [
    ('hp1', solph.components.Converter, {'enw'}, {'hnw'}),
    ('eb1', solph.components.Converter, {'enw'}, {'hnw'}),
    ('gb1', solph.components.Converter, {'gnw'}, {'hnw'}),
    ('ccet1', solph.components.Converter, {'gnw'}, {'hnw', 'chp_node'}),
    ('ice1', solph.components.Converter, {'gnw'}, {'hnw', 'chp_node'}),
    ('sol1', solph.components.Source, set(), {'hnw'}),
    ('exhs1', solph.components.Source, set(), {'hnw'}),
    ('tes1', solph.components.GenericStorage, {'hnw'}, {'hnw'}),
    ('gas_source', solph.components.Source, set(), {'gnw'}),
    ('elec_source', solph.components.Source, set(), {'enw'}),
    ('heat_sink', solph.components.Sink, {'hnw'}, set()),
    ('elec_sink', solph.components.Sink, {'chp_node'}, set()),
    ('chp_internal', solph.components.Converter, {'chp_node'}, {'enw'}),
])
def test_component_connections(es_all, unit, cls, inputs, outputs):
    comp = es_all.comps[unit]
    bus_key = {b: k for k, b in es_all.buses.items()}
    assert isinstance(comp, cls)
    assert {bus_key[b] for b in comp.inputs} == inputs
    assert {bus_key[b] for b in comp.outputs} == outputs

"""Unit tests for the module-level helper functions of ``model.py``."""
import pandas as pd
import pytest

from owp_milp_optimization.model import (
    LCOH, calc_bwsf, calc_cost, check_column, result_labeling
)


# %% calc_bwsf (Barwert-Summenfaktor / present value annuity factor)

def test_calc_bwsf_reference_value():
    """Matches the textbook value for 5 % interest over 20 years."""
    assert calc_bwsf(0.05, 20) == pytest.approx(12.462210, abs=1e-6)


@pytest.mark.parametrize('i', [0.01, 0.05, 0.08, 0.2])
@pytest.mark.parametrize('n', [1, 5, 20, 40])
def test_calc_bwsf_equals_sum_of_discount_factors(i, n):
    """Equals the definition: the sum of 1 / (1 + i)^t for t = 1..n."""
    expected = sum((1 + i) ** -t for t in range(1, n + 1))
    assert calc_bwsf(i, n) == pytest.approx(expected)


def test_calc_bwsf_single_year():
    """For a single year, it is just the discount factor of that year."""
    assert calc_bwsf(0.1, 1) == pytest.approx(1 / 1.1)


def test_calc_bwsf_decreases_with_interest():
    """A higher interest rate gives a smaller present value factor."""
    assert calc_bwsf(0.02, 20) > calc_bwsf(0.05, 20) > calc_bwsf(0.1, 20)


@pytest.mark.xfail(
    raises=ZeroDivisionError, strict=True,
    reason=(
        'BUG: calc_bwsf divides by (q - 1), so a capital interest of 0 % '
        'raises ZeroDivisionError. The limit for i -> 0 is n. The dashboard '
        'does not restrict the interest rate input to values > 0.'
    )
)
def test_calc_bwsf_zero_interest_equals_lifetime():
    """At 0 % interest, every year counts fully, so the factor is n."""
    assert calc_bwsf(0.0, 20) == pytest.approx(20)


# %% LCOH (levelized cost of heat)

def test_lcoh_matches_formula():
    """Equals (invest + bwsf * (cost - revenue)) / (bwsf * Q)."""
    invest, cost, Q, revenue, i, n = 1e6, 2e5, 1e4, 5e4, 0.04, 25
    bwsf = calc_bwsf(i, n)
    expected = (invest + bwsf * (cost - revenue)) / (bwsf * Q)
    assert LCOH(invest, cost, Q, revenue=revenue, i=i, n=n) == pytest.approx(
        expected
    )


def test_lcoh_defaults_are_five_percent_and_twenty_years():
    """Without explicit values: no revenue, 5 % interest and 20 years."""
    assert LCOH(1e6, 2e5, 1e4) == pytest.approx(
        LCOH(1e6, 2e5, 1e4, revenue=0, i=0.05, n=20)
    )


def test_lcoh_without_invest_is_specific_running_cost():
    """Without invest, LCOH is simply the annual cost per MWh of heat."""
    assert LCOH(0, 5000, 100) == pytest.approx(50)


def test_lcoh_annualizes_invest_with_bwsf():
    """The invest is spread over the lifetime using the bwsf."""
    # Pure investment: invest / (bwsf * Q) is the annuity per MWh
    assert LCOH(12.462210 * 100, 0, 100) == pytest.approx(1.0, abs=1e-6)


def test_lcoh_decreases_with_revenue():
    """Revenues (e.g. from selling electricity) lower the heat cost."""
    assert LCOH(1e6, 2e5, 1e4, revenue=1e5) < LCOH(1e6, 2e5, 1e4)


# %% calc_cost

@pytest.fixture
def cost_params():
    """Cost parameters of one heat pump, with bonuses on invest (25 %) and
    operating cost (50 %) so that their effect is visible."""
    return {
        'hp1': {
            'inv_spez': 1000.0, 'inv_bonus_rel': 0.25, 'op_cost_fix': 10.0,
            'op_cost_var': 2.0, 'op_cost_bonus_rel': 0.5,
        }
    }


def test_calc_cost_computes_all_cost_rows(cost_params):
    """Every cost row follows from capacity (20), dispatch and the bonuses.

    The dispatch series ``uc`` sums up to 6 MWh.
    """
    uc = pd.Series([1.0, 2.0, 3.0])
    cost_df = calc_cost('hp1', 20.0, cost_params, uc, pd.DataFrame())

    assert cost_df.loc['invest', 'hp1'] == pytest.approx(1000 * 20 * 0.75)
    assert cost_df.loc['op_cost_fix', 'hp1'] == pytest.approx(10 * 20 * 0.5)
    assert cost_df.loc['op_cost_var', 'hp1'] == pytest.approx(2 * 6 * 0.5)
    assert cost_df.loc['op_cost', 'hp1'] == pytest.approx(100 + 6)


def test_calc_cost_adds_additional_variable_cost_without_bonus(cost_params):
    """``add_var_cost`` is charged per MWh on top of the variable cost."""
    uc = pd.Series([1.0, 2.0, 3.0])
    cost_df = calc_cost(
        'hp1', 20.0, cost_params, uc, pd.DataFrame(), add_var_cost=4.0
    )
    # The additional cost (e.g. energy tax) is not reduced by the bonus
    assert cost_df.loc['op_cost_var', 'hp1'] == pytest.approx(6 + 4 * 6)
    assert cost_df.loc['op_cost', 'hp1'] == pytest.approx(100 + 6 + 24)


@pytest.mark.parametrize('add_var_cost', [None, 0, 0.0])
def test_calc_cost_ignores_empty_additional_cost(cost_params, add_var_cost):
    """``None`` and 0 as ``add_var_cost`` leave the variable cost unchanged."""
    uc = pd.Series([1.0, 2.0, 3.0])
    cost_df = calc_cost(
        'hp1', 20.0, cost_params, uc, pd.DataFrame(),
        add_var_cost=add_var_cost
    )
    assert cost_df.loc['op_cost_var', 'hp1'] == pytest.approx(6)


def test_calc_cost_keeps_existing_columns(cost_params):
    """Adding a second unit leaves the column of the first one untouched."""
    cost_params['gb1'] = dict(cost_params['hp1'])
    uc = pd.Series([1.0])
    cost_df = calc_cost('hp1', 1.0, cost_params, uc, pd.DataFrame())
    before = cost_df['hp1'].copy()
    cost_df = calc_cost('gb1', 2.0, cost_params, uc, cost_df)

    assert list(cost_df.columns) == ['hp1', 'gb1']
    assert list(cost_df.index) == ['invest', 'op_cost_fix', 'op_cost_var',
                                   'op_cost']
    pd.testing.assert_series_equal(cost_df['hp1'], before)


def test_calc_cost_zero_dispatch_has_only_fixed_cost(cost_params):
    """A unit that never runs only causes fixed operating cost."""
    cost_df = calc_cost(
        'hp1', 20.0, cost_params, pd.Series([0.0, 0.0]), pd.DataFrame()
    )
    assert cost_df.loc['op_cost_var', 'hp1'] == 0
    assert cost_df.loc['op_cost', 'hp1'] == cost_df.loc['op_cost_fix', 'hp1']


# %% check_column (oemof result key -> readable label)

HNW = 'heat network'

LABEL_CASES = [
    # heat producers that feed the heat network: heat pump
    ((('hp1', HNW), 'flow'), 'Q_out_hp1'),
    ((('hp1', HNW), 'invest'), 'cap_hp1'),
    ((('hp1', HNW), 'status'), 'state_hp1'),
    ((('hp1', HNW), 'status_nominal'), 'state_nom_hp1'),
    ((('hp1', HNW), 'total'), 'total_hp1'),
    # thermal energy storage discharging into the heat network
    ((('tes1', HNW), 'flow'), 'Q_out_tes1'),
    ((('tes1', HNW), 'invest'), 'cap_out_tes1'),
    ((('tes1', HNW), 'status'), 'state_out_tes1'),
    ((('tes1', HNW), 'status_nominal'), 'state_nom_out_tes1'),
    ((('tes1', HNW), 'total'), 'total_out_tes1'),
    # every other heat producer
    ((('gb1', HNW), 'flow'), 'Q_gb1'),
    ((('ccet2', HNW), 'invest'), 'cap_ccet2'),
    ((('sol1', HNW), 'status'), 'state_sol1'),
    ((('eb1', HNW), 'status_nominal'), 'state_nom_eb1'),
    ((('exhs3', HNW), 'total'), 'total_exhs3'),
    # flows out of the heat network
    (((HNW, 'tes1'), 'flow'), 'Q_in_tes1'),
    (((HNW, 'tes1'), 'invest'), 'cap_in_tes1'),
    (((HNW, 'tes1'), 'status'), 'state_in_tes1'),
    (((HNW, 'tes1'), 'status_nominal'), 'state_nom_in_tes1'),
    (((HNW, 'tes1'), 'total'), 'total_in_tes1'),
    (((HNW, 'heat demand'), 'flow'), 'Q_demand'),
    # CHP electricity
    ((('ccet1', 'chp node'), 'flow'), 'P_ccet1'),
    ((('ice1', 'chp node'), 'flow'), 'P_ice1'),
    ((('chp node', 'spotmarket'), 'flow'), 'P_spotmarket'),
    ((('chp node', 'chp internal'), 'flow'), 'P_internal'),
    ((('chp internal', 'electricity network'), 'flow'), 'P_internal'),
    # electricity consumers
    ((('electricity network', 'hp1'), 'flow'), 'P_in_hp1'),
    ((('electricity network', 'hp1'), 'status'), 'state_hp1'),
    ((('electricity network', 'eb1'), 'flow'), 'P_eb1'),
    # gas consumers
    ((('gas network', 'gb1'), 'flow'), 'H_gb1'),
    ((('gas network', 'ccet1'), 'flow'), 'H_ccet1'),
    # sources
    ((('gas source', 'gas network'), 'flow'), 'H_source'),
    ((('electricity source', 'electricity network'), 'flow'), 'P_source'),
    # storage internals
    ((('tes1', 'None'), 'storage_content'), 'storage_content_tes1'),
    ((('tes1', 'None'), 'invest'), 'cap_tes1'),
    ((('tes1', 'None'), 'total'), 'total_tes1'),
    ((('tes1', 'None'), 'storage_losses'), 'storage_losses_tes1'),
    ((('tes1', 'None'), 'other'), "(('tes1', 'None'), 'other')"),
]


@pytest.mark.parametrize('col, expected', LABEL_CASES)
def test_check_column_labels(col, expected):
    """Each oemof result key gets its readable label.

    oemof names results ``((from_node, to_node), variable)``. ``check_column``
    turns that into labels like ``Q_gb1`` (heat from gas boiler 1).
    """
    assert check_column(col, debug=False) == expected


@pytest.mark.parametrize('col', [
    (('foo', 'bar'), 'flow'),
    (('hp1', HNW), 'unknown_variable'),
    (('chp node', 'somewhere'), 'flow'),
])
def test_check_column_unknown_returns_none(col):
    """Keys that match no labeling rule return None instead of raising."""
    assert check_column(col, debug=False) is None


def test_check_column_reports_unknown_edge_in_debug_mode(capsys):
    """With ``debug=True``, an unknown key is printed."""
    check_column((('foo', 'bar'), 'flow'), debug=True)
    assert 'could not be labeled' in capsys.readouterr().out


def test_check_column_is_silent_without_debug(capsys):
    """With ``debug=False``, nothing is printed."""
    check_column((('foo', 'bar'), 'flow'), debug=False)
    assert capsys.readouterr().out == ''


# %% result_labeling

def test_result_labeling_renames_dataframe_columns_in_place():
    """DataFrame columns are renamed in place, nothing is returned."""
    df = pd.DataFrame(
        [[1.0, 2.0]],
        columns=[(('gb1', HNW), 'flow'), (('gas source', 'gas network'),
                                          'flow')]
    )
    assert result_labeling(df, debug=False) is None
    assert list(df.columns) == ['Q_gb1', 'H_source']


def test_result_labeling_renames_series_index_in_place():
    """For a Series, the index is renamed and the values are kept."""
    s = pd.Series(
        [10.0, 20.0],
        index=[(('hp1', HNW), 'invest'), (('tes1', 'None'), 'invest')]
    )
    result_labeling(s, debug=False)
    assert list(s.index) == ['cap_hp1', 'cap_tes1']
    assert list(s.values) == [10.0, 20.0]


def test_result_labeling_skips_non_tuple_columns(capsys):
    """Columns that are not oemof keys stay as they are (and are reported
    in debug mode)."""
    df = pd.DataFrame([[1.0, 2.0]], columns=['already_labeled',
                                             (('gb1', HNW), 'flow')])
    result_labeling(df, debug=True)
    assert list(df.columns) == ['already_labeled', 'Q_gb1']
    assert 'already_labeled' in capsys.readouterr().out


def test_result_labeling_maps_unknown_edges_to_none():
    """Unknown keys become a column named None (see ``check_column``)."""
    df = pd.DataFrame([[1.0]], columns=[(('foo', 'bar'), 'flow')])
    result_labeling(df, debug=False)
    assert list(df.columns) == [None]


def test_result_labeling_handles_empty_series():
    """An empty Series does not raise."""
    s = pd.Series(dtype=float)
    result_labeling(s, debug=False)
    assert s.empty

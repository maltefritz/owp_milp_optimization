"""Unit tests for the module-level helper functions of ``model.py``."""
import pandas as pd
import pytest

from owp_milp_optimization.model import (
    LCOH, calc_bwsf, calc_cost, check_column, result_labeling
)


# %% calc_bwsf (Barwert-Summenfaktor / present value annuity factor)

def test_calc_bwsf_reference_value():
    # 5 % interest over 20 years, standard textbook value
    assert calc_bwsf(0.05, 20) == pytest.approx(12.462210, abs=1e-6)


@pytest.mark.parametrize('i', [0.01, 0.05, 0.08, 0.2])
@pytest.mark.parametrize('n', [1, 5, 20, 40])
def test_calc_bwsf_equals_sum_of_discount_factors(i, n):
    expected = sum((1 + i) ** -t for t in range(1, n + 1))
    assert calc_bwsf(i, n) == pytest.approx(expected)


def test_calc_bwsf_single_year():
    assert calc_bwsf(0.1, 1) == pytest.approx(1 / 1.1)


def test_calc_bwsf_decreases_with_interest():
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
    assert calc_bwsf(0.0, 20) == pytest.approx(20)


# %% LCOH (levelized cost of heat)

def test_lcoh_matches_formula():
    invest, cost, Q, revenue, i, n = 1e6, 2e5, 1e4, 5e4, 0.04, 25
    bwsf = calc_bwsf(i, n)
    expected = (invest + bwsf * (cost - revenue)) / (bwsf * Q)
    assert LCOH(invest, cost, Q, revenue=revenue, i=i, n=n) == pytest.approx(
        expected
    )


def test_lcoh_defaults_are_five_percent_and_twenty_years():
    assert LCOH(1e6, 2e5, 1e4) == pytest.approx(
        LCOH(1e6, 2e5, 1e4, revenue=0, i=0.05, n=20)
    )


def test_lcoh_without_invest_is_specific_running_cost():
    assert LCOH(0, 5000, 100) == pytest.approx(50)


def test_lcoh_annualizes_invest_with_bwsf():
    # Pure investment: invest / (bwsf * Q) is the annuity per MWh
    assert LCOH(12.462210 * 100, 0, 100) == pytest.approx(1.0, abs=1e-6)


def test_lcoh_decreases_with_revenue():
    assert LCOH(1e6, 2e5, 1e4, revenue=1e5) < LCOH(1e6, 2e5, 1e4)


# %% calc_cost

@pytest.fixture
def cost_params():
    return {
        'hp1': {
            'inv_spez': 1000.0, 'inv_bonus_rel': 0.25, 'op_cost_fix': 10.0,
            'op_cost_var': 2.0, 'op_cost_bonus_rel': 0.5,
        }
    }


def test_calc_cost_computes_all_cost_rows(cost_params):
    uc = pd.Series([1.0, 2.0, 3.0])
    cost_df = calc_cost('hp1', 20.0, cost_params, uc, pd.DataFrame())

    assert cost_df.loc['invest', 'hp1'] == pytest.approx(1000 * 20 * 0.75)
    assert cost_df.loc['op_cost_fix', 'hp1'] == pytest.approx(10 * 20 * 0.5)
    assert cost_df.loc['op_cost_var', 'hp1'] == pytest.approx(2 * 6 * 0.5)
    assert cost_df.loc['op_cost', 'hp1'] == pytest.approx(100 + 6)


def test_calc_cost_adds_additional_variable_cost_without_bonus(cost_params):
    uc = pd.Series([1.0, 2.0, 3.0])
    cost_df = calc_cost(
        'hp1', 20.0, cost_params, uc, pd.DataFrame(), add_var_cost=4.0
    )
    # The additional cost (e.g. energy tax) is not reduced by the bonus
    assert cost_df.loc['op_cost_var', 'hp1'] == pytest.approx(6 + 4 * 6)
    assert cost_df.loc['op_cost', 'hp1'] == pytest.approx(100 + 6 + 24)


@pytest.mark.parametrize('add_var_cost', [None, 0, 0.0])
def test_calc_cost_ignores_empty_additional_cost(cost_params, add_var_cost):
    uc = pd.Series([1.0, 2.0, 3.0])
    cost_df = calc_cost(
        'hp1', 20.0, cost_params, uc, pd.DataFrame(),
        add_var_cost=add_var_cost
    )
    assert cost_df.loc['op_cost_var', 'hp1'] == pytest.approx(6)


def test_calc_cost_keeps_existing_columns(cost_params):
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
    cost_df = calc_cost(
        'hp1', 20.0, cost_params, pd.Series([0.0, 0.0]), pd.DataFrame()
    )
    assert cost_df.loc['op_cost_var', 'hp1'] == 0
    assert cost_df.loc['op_cost', 'hp1'] == cost_df.loc['op_cost_fix', 'hp1']

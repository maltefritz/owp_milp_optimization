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

import os

import oemof.solph as solph
import pandas as pd
from oemof.solph import views
from pyomo.contrib import appsi
from pyomo.contrib.appsi.base import TerminationCondition


class EnergySystem():
    """Model class that builds the energy system from parameters."""

    def __init__(self, data, param_units, param_opt):
        self.data = data
        self.param_units = param_units
        self.param_opt = param_opt

        self.tes_used = any(
            [u.rstrip('0123456789') == 'tes' for u in self.param_units.keys()]
            )
        self.chp_used = (
            any([
                u.rstrip('0123456789') == 'ice'
                for u in self.param_units.keys()
                ])
            or any([
                u.rstrip('0123456789') == 'ccet'
                for u in self.param_units.keys()
                ])
            )
        self.gas_used = (
            self.chp_used or any([
                u.rstrip('0123456789') == 'plb'
                for u in self.param_units.keys()
                ])
            )
        self.el_used = (
            self.chp_used
            or any([
                u.rstrip('0123456789') == 'hp'
                for u in self.param_units.keys()
                ])
            or any([
                u.rstrip('0123456789') == 'eb'
                for u in self.param_units.keys()
                ])
            )

        self.periods = len(data.index)
        self.es = solph.EnergySystem(
            timeindex=pd.date_range(
                data.index[0], periods=self.periods, freq='h'
                ),
            infer_last_interval=True
            )

        self.bwsf = calc_bwsf(
            self.param_opt['capital_interest'],
            self.param_opt['lifetime']
            )

        self.buses = {}
        self.comps = {}

    def generate_buses(self):
        if self.gas_used:
            self.buses['gnw'] = solph.Bus(label='gas network')
        if self.el_used:
            self.buses['enw'] = solph.Bus(label='electricity network')
        self.buses['hnw'] = solph.Bus(label='heat network')
        if self.chp_used:
            self.buses['chp_node'] = solph.Bus(label='chp node')

        self.es.add(*list(self.buses.values()))

    def generate_sources(self):
        if self.gas_used:
            self.comps['gas_source'] = solph.components.Source(
                label='gas source',
                outputs={
                    self.buses['gnw']: solph.flows.Flow(
                        variable_costs=(
                            self.data['gas_price']
                            + (self.data['co2_price']
                               * self.param_opt['ef_gas'])
                            )
                        )
                    }
                )

            self.es.add(self.comps['gas_source'])

        if self.el_used:
            self.comps['elec_source'] = solph.components.Source(
                label='electricity source',
                outputs={
                    self.buses['enw']: solph.flows.Flow(
                        variable_costs=(
                            self.param_opt['elec_consumer_charges_grid']
                            - self.param_opt['elec_consumer_charges_self']
                            + self.data['el_spot_price']
                            )
                        )
                    }
                )

            self.es.add(self.comps['elec_source'])

        for unit, unit_params in self.param_units.items():
            unit_cat = unit.rstrip('0123456789')
            if unit_cat == 'sol':
                if unit_params['invest_mode']:
                    nominal_capacity = solph.Investment(
                        ep_costs=unit_params['inv_spez'] / self.bwsf,
                        maximum=unit_params['A_max'],
                        minimum=unit_params['A_min']
                        )
                else:
                    nominal_capacity = unit_params['A_N']

                self.comps[unit] = solph.components.Source(
                    label=unit,
                    outputs={
                        self.buses['hnw']: solph.flows.Flow(
                            variable_costs=unit_params['op_cost_var'],
                            nominal_capacity=nominal_capacity,
                            fix=self.data['solar_heat_flow']
                            )
                        }
                    )

                self.es.add(self.comps[unit])

            if unit_cat == 'exhs':
                if unit_params['fix']:
                    fix = 1
                else:
                    fix = None

                if unit_params['invest_mode']:
                    nominal_capacity = solph.Investment(
                        ep_costs=unit_params['inv_spez'] / self.bwsf,
                        maximum=unit_params['cap_max'],
                        minimum=unit_params['cap_min']
                        )
                else:
                    nominal_capacity = unit_params['cap_N']

                self.comps[unit] = solph.components.Source(
                    label=unit,
                    outputs={
                        self.buses['hnw']: solph.flows.Flow(
                            variable_costs=unit_params['op_cost_var'],
                            nominal_capacity=nominal_capacity,
                            fix=fix
                            )
                        }
                    )

                self.es.add(self.comps[unit])

    def generate_sinks(self):
        self.comps['heat_sink'] = solph.components.Sink(
            label='heat demand',
            inputs={
                self.buses['hnw']: solph.flows.Flow(
                    variable_costs=-self.param_opt['heat_price'],
                    nominal_capacity=self.data['heat_demand'].max(),
                    fix=self.data['heat_demand']/self.data['heat_demand'].max()
                    )
                }
            )

        self.es.add(self.comps['heat_sink'])

        if self.chp_used:
            self.comps['elec_sink'] = solph.components.Sink(
                label='spotmarket',
                inputs={
                    self.buses['chp_node']: solph.flows.Flow(
                        variable_costs=(
                            -self.data['el_spot_price'] - self.param_opt['vNNE']
                            )
                        )
                    }
                )

            self.es.add(self.comps['elec_sink'])

    def generate_components(self):
        internal_el = False
        for unit, unit_params in self.param_units.items():
            unit_cat = unit.rstrip('0123456789')
            if unit_cat in ['ccet', 'ice']:

                if unit_params['invest_mode']:
                    nominal_capacity = solph.Investment(
                        ep_costs=unit_params['inv_spez'] / self.bwsf,
                        maximum=unit_params['cap_max'],
                        minimum=unit_params['cap_min']
                        )
                else:
                    nominal_capacity = unit_params['cap_N']

                self.comps[unit] = solph.components.Converter(
                    label=unit,
                    inputs={self.buses['gnw']: solph.flows.Flow()},
                    outputs={
                        self.buses['chp_node']: solph.flows.Flow(
                            variable_costs=unit_params['op_cost_var']
                            ),
                        self.buses['hnw']: solph.flows.Flow(
                            nominal_capacity=nominal_capacity,
                            max=unit_params['Q_rel_max'],
                            min=unit_params['Q_rel_min'],
                            nonconvex=solph.NonConvex()
                            )
                        },
                    conversion_factors={
                        self.buses['chp_node']: unit_params['eta_el'],
                        self.buses['hnw']: unit_params['eta_th']
                        }
                    )

                self.es.add(self.comps[unit])
                internal_el = True

            if unit_cat in ['hp', 'plb', 'eb']:
                if unit_cat == 'hp':
                    eff = 'cop'
                    input_nw = 'enw'
                    var_cost = (
                        unit_params['op_cost_var']
                        + self.param_opt['elec_consumer_charges_self']
                        )
                elif unit_cat == 'plb':
                    eff = 'eta'
                    input_nw = 'gnw'
                    var_cost = (
                        unit_params['op_cost_var']
                        + self.param_opt['energy_tax']
                        )
                elif unit_cat == 'eb':
                    eff = 'eta'
                    input_nw = 'enw'
                    var_cost = (
                        unit_params['op_cost_var']
                        + self.param_opt['elec_consumer_charges_self']
                        )

                if unit_params['invest_mode']:
                    nominal_capacity = solph.Investment(
                        ep_costs=unit_params['inv_spez'] / self.bwsf,
                        maximum=unit_params['cap_max'],
                        minimum=unit_params['cap_min']
                        )
                else:
                    nominal_capacity = unit_params['cap_N']

                self.comps[unit] = solph.components.Converter(
                    label=unit,
                    inputs={self.buses[input_nw]: solph.flows.Flow()},
                    outputs={
                        self.buses['hnw']: solph.flows.Flow(
                            nominal_capacity=nominal_capacity,
                            max=unit_params['Q_rel_max'],
                            min=unit_params['Q_rel_min'],
                            nonconvex=solph.NonConvex(),
                            variable_costs=var_cost
                            )
                        },
                    conversion_factors={
                        self.buses[input_nw]: unit_params[eff]
                        }
                    )

                self.es.add(self.comps[unit])

            if unit_cat == 'tes':
                if unit_params['invest_mode']:
                    nominal_storage_capacity = solph.Investment(
                        ep_costs=unit_params['inv_spez'] / self.bwsf,
                        maximum=unit_params['Q_max'],
                        minimum=unit_params['Q_min']
                        )
                else:
                    nominal_storage_capacity = unit_params['Q_N']

                self.comps[unit] = solph.components.GenericStorage(
                    label=unit,
                    nominal_storage_capacity=nominal_storage_capacity,
                    inputs={
                        self.buses['hnw']: solph.flows.Flow(
                            variable_costs=unit_params['op_cost_var']
                            )
                        },
                    outputs={
                        self.buses['hnw']: solph.flows.Flow(
                            variable_costs=unit_params['op_cost_var']
                            )
                        },
                    invest_relation_input_capacity=(
                        unit_params['Q_in_to_cap']
                        ),
                    invest_relation_output_capacity=(
                        unit_params['Q_out_to_cap']
                        ),
                    initial_storage_level=unit_params['init_storage'],
                    loss_rate=unit_params['Q_rel_loss'],
                    balanced=unit_params['balanced']
                    )

                self.es.add(self.comps[unit])

        if internal_el:
            self.comps['chp_internal'] = solph.components.Converter(
                label='chp internal',
                inputs={self.buses['chp_node']: solph.flows.Flow()},
                outputs={self.buses['enw']: solph.flows.Flow(
                    nominal_capacity=9999,
                    max=1.0,
                    min=0.0
                    )},
                conversion_factors={self.buses['enw']: 1}
                )

            self.es.add(self.comps['chp_internal'])

    def solve_model(self):
        self.model = solph.Model(self.es)

        solverlogspath = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'solverlogs')
            )
        if not os.path.exists(solverlogspath):
            os.mkdir(solverlogspath)

        logpath = os.path.abspath(
            os.path.join(
                solverlogspath, f'{self.param_opt["Solver"].lower()}_log.txt'
                )
            )
        if os.path.exists(logpath):
            os.remove(logpath)

        tc = None
        if self.param_opt['Solver'] == 'Gurobi':
            options = {
                    'MIPGap': self.param_opt['MIPGap'],
                    'LogFile': logpath
                    }
            if self.param_opt['TimeLimit'] is not None:
                options.update({'TimeLimit': self.param_opt['TimeLimit']})
            results = self.model.solve(
                solver='gurobi', solve_kwargs={'tee': True},
                cmdline_options=options, allow_nonoptimal=True
                )
            tc = results.Solver.Termination_condition
        elif self.param_opt['Solver'] == 'SCIP':
            options = {
                    'limits/gap': self.param_opt['MIPGap'],
                    'logfile': logpath
                    }
            if self.param_opt['TimeLimit'] is not None:
                options.update({'limits/time': self.param_opt['TimeLimit']})
            results = self.model.solve(
                solver='scip', solve_kwargs={'tee': True},
                cmdline_options=options, allow_nonoptimal=True
                )
            tc = results.Solver.Termination_condition
        elif self.param_opt['Solver'] == 'HiGHS':
            opt = appsi.solvers.Highs()
            opt.config.mip_gap = self.param_opt['MIPGap']
            opt.config.logfile = logpath
            if self.param_opt['TimeLimit'] is not None:
                opt.config.time_limit = self.param_opt['TimeLimit']
            # opt.config.stream_solver = True
            # opt.highs_options['output_flag'] = True
            # opt.highs_options['log_to_console'] = True
            try:
                results = opt.solve(self.model)
            except RuntimeError:
                results = appsi.solvers.highs.HighsResults(opt)
            tc = results.termination_condition

        feasable_sols = [
            TerminationCondition.optimal,
            'optimal',
            TerminationCondition.objectiveLimit,
            'objectiveLimit',
            TerminationCondition.maxTimeLimit,
            'maxTimeLimit',
        ]
        infeasable_sols = [
            TerminationCondition.infeasible,
            'infeasible',
            TerminationCondition.unbounded,
            'unbounded',
            TerminationCondition.infeasibleOrUnbounded,
            'infeasibleOrUnbounded',
        ]

        if tc in feasable_sols:
            return 'ok'
        elif tc in infeasable_sols:
            return 'infeasable'
        else:
            print(f'UNKOWN SOVLER ERROR:: Termination Condition: {tc}')
            return 'unknown solver error'

    def get_results(self):
        self.results = solph.processing.results(self.model)
        # breakpoint()
        # self.meta_results = solph.processing.meta_results(self.model)

        concat_data = []
        if self.gas_used:
            data_gnw = views.node(self.results, 'gas network')['sequences']
            concat_data += [data_gnw]
        if self.el_used:
            data_enw = views.node(
                self.results, 'electricity network'
                )['sequences']
            concat_data += [data_enw]
        data_hnw = views.node(self.results, 'heat network')['sequences']
        concat_data += [data_hnw]

        if self.chp_used:
            data_chpnode = views.node(self.results, 'chp node')['sequences']
            concat_data += [data_chpnode]

        try:
            self.data_caps = (
                views.node(self.results, 'heat network')['scalars']
                )
        except KeyError:
            self.data_caps = pd.Series()

        if self.tes_used:
            data_tes = None
            for unit, unit_params in self.param_units.items():
                if unit.rstrip('0123456789') == 'tes':
                    next_data_tes = views.node(self.results, unit)['sequences']
                    if unit_params['invest_mode']:
                        next_cap_tes = (
                            views.node(
                                self.results, unit
                                )['scalars'][((unit, 'None'), 'invest')]
                            )
                    else:
                        next_cap_tes = unit_params['Q_N']
                    if data_tes is None:
                        data_tes = next_data_tes
                    else:
                        data_tes = pd.concat([data_tes, next_data_tes], axis=1)
                    self.data_caps = pd.concat([
                        self.data_caps,
                        pd.Series(
                            next_cap_tes, index=[((unit, 'None'), 'invest')]
                            )
                        ])
            concat_data += [data_tes]

        # Combine all data and relabel the column names
        self.data_all = pd.concat(concat_data, axis=1)
        if self.data_all.iloc[-1, :].isna().values.all():
            self.data_all.drop(self.data_all.tail(1).index, inplace=True)

        result_labeling(self.data_all)
        self.data_all = self.data_all.loc[
            :, ~self.data_all.columns.duplicated()
            ].copy()

        result_labeling(self.data_caps)

        for unit, unit_params in self.param_units.items():
            if f'cap_{unit}' not in self.data_caps.index:
                unit_cat = unit.rstrip('0123456789')
                if unit_cat == 'tes':
                    param_var = 'Q_N'
                elif unit_cat == 'sol':
                    param_var = 'A_N'
                else:
                    param_var = 'cap_N'
                self.data_caps[f'cap_{unit}'] = unit_params[param_var]

        if None in self.data_all.columns:
            self.data_all.drop(columns=[None], inplace=True)
        for col in self.data_all.columns:
            if ('status' in col[-1]) or ('state' in col):
                self.data_all.drop(columns=col, inplace=True)

        self.data_caps = self.data_caps.to_frame().transpose()
        self.data_caps.reset_index(inplace=True, drop=True)
        if None in self.data_caps.columns:
            self.data_caps.drop(columns=[None], inplace=True)
        for col in self.data_caps.columns:
            if ('total' in str(col)) or ('0' in str(col)):
                self.data_caps.drop(columns=col, inplace=True)

        try:
            self.data_all = self.data_all.reindex(
                sorted(self.data_all.columns), axis=1
                )
        except TypeError as e:
            print(f'TypeError in sorting data_all: {e}')

        try:
            self.data_caps = self.data_caps.reindex(
                sorted(self.data_caps.columns), axis=1
                )
        except TypeError as e:
            print(f'TypeError in sorting data_caps: {e}')

        # Prepare economic and ecologic data containers
        self.cost_df = pd.DataFrame()
        self.key_params = {}

    def calc_econ_params(self):
        for unit, unit_params in self.param_units.items():
            unit_cat = unit.rstrip('0123456789')

            unit_E_N = self.data_caps.loc[0, f'cap_{unit}']
            add_cost = 0

            if unit_cat == 'plb':
                add_cost = self.param_opt['energy_tax']
                E_N_label = f'Q_{unit}'
            elif unit_cat == 'hp':
                E_N_label = f'Q_out_{unit}'
            elif unit_cat == 'tes':
                E_N_label = f'Q_in_{unit}'
            elif unit_cat in ['ccet', 'ice']:
                E_N_label = f'P_{unit}'
                unit_E_N = (
                    unit_E_N / unit_params['eta_th']
                    * unit_params['eta_el']
                    )
            else:
                E_N_label = f'Q_{unit}'

            self.cost_df = calc_cost(
                unit, unit_E_N, self.param_units, self.data_all[E_N_label],
                self.cost_df, add_var_cost=add_cost
                )

        # %% Primary energy and total cost calculation
        # total unit costs
        self.key_params['op_cost_total'] = self.cost_df.loc['op_cost'].sum()
        self.key_params['invest_total'] = self.cost_df.loc['invest'].sum()

        # total gas costs
        if 'H_source' in self.data_all.columns:
            self.key_params['cost_gas'] = (
                self.data_all['H_source'] * (
                    self.data['gas_price']
                    + self.data['co2_price'] * self.param_opt['ef_gas']
                    )
                ).sum()
        else:
            self.key_params['cost_gas'] = 0

        # total electricity costs
        if 'P_source' in self.data_all.columns:
            self.key_params['cost_el_grid'] = (
                self.data_all['P_source'] * (
                    self.data['el_spot_price']
                    + self.param_opt['elec_consumer_charges_grid']
                    )
                ).sum()
        else:
            self.key_params['cost_el_grid'] = 0


        if 'P_internal' in self.data_all.columns:
            self.key_params['cost_el_internal'] = (
                self.data_all['P_internal']
                * self.param_opt['elec_consumer_charges_self']
                ).sum()
        else:
            self.key_params['cost_el_internal'] = 0

        self.key_params['cost_el'] = (
            self.key_params['cost_el_grid']
            + self.key_params['cost_el_internal']
            )

        self.key_params['cost_total'] = (
            self.key_params['op_cost_total'] + self.key_params['cost_gas']
            + self.key_params['cost_el']
            )

        # %% Revenue calculation
        if 'P_internal' in self.data_all.columns:
            self.key_params['revenues_spotmarket'] = (
                self.data_all['P_spotmarket'] * (
                    self.data['el_spot_price'] + self.param_opt['vNNE']
                    )
                ).sum()
        else:
            self.key_params['revenues_spotmarket'] = 0

        self.key_params['revenues_heat'] = (
            self.data_all['Q_demand'].sum() * self.param_opt['heat_price']
            )

        self.key_params['revenues_total'] = (
            self.key_params['revenues_spotmarket']
            + self.key_params['revenues_heat']
            )

        # %% Total balance
        self.key_params['balance_total'] = (
            self.key_params['revenues_total'] - self.key_params['cost_total']
            )

        # %% Meta results
        # self.key_params['objective'] = self.meta_results['objective']
        # self.key_params['gap'] = (
        #     (self.meta_results['problem']['Lower bound']
        #     - self.meta_results['objective'])
        #     / self.meta_results['problem']['Lower bound'] * 100
        #     )

        # %% Main economic results
        self.key_params['LCOH'] = LCOH(
            self.key_params['invest_total'], self.key_params['cost_total'],
            self.data_all['Q_demand'].sum(),
            revenue=(
                self.key_params['revenues_total']
                - self.key_params['revenues_heat']
                ),
            i=self.param_opt['capital_interest'], n=self.param_opt['lifetime']
            )

        self.key_params['total_heat_demand'] = self.data_all['Q_demand'].sum()

    def calc_ecol_params(self):
        self.data_all['Emissions OM'] = 0

        if 'H_source' in self.data_all.columns:
            self.data_all['Emissions OM'] += (
                self.data_all['H_source'] * self.param_opt['ef_gas']
                )
            self.key_params['Emissions OM (Gas)'] = (
                self.data_all['H_source'] * self.param_opt['ef_gas']
                ).sum()
        else:
            self.key_params['Emissions OM (Gas)'] = 0

        if 'P_source' in self.data_all.columns:
            self.data_all['Emissions OM'] += (
                self.data_all['P_source'] * self.data['ef_om']
                )
            self.key_params['Emissions OM (Electricity)'] = (
                self.data_all['P_source'] * self.data['ef_om']
                ).sum()
        else:
            self.key_params['Emissions OM (Electricity)'] = 0

        if 'P_spotmarket' in self.data_all.columns:
            self.data_all['Emissions OM'] -= (
                self.data_all['P_spotmarket'] * self.data['ef_om']
                )
            self.key_params['Emissions OM (Spotmarket)'] = (
                self.data_all['P_spotmarket'] * self.data['ef_om'] * -1
                ).sum()
        else:
            self.key_params['Emissions OM (Spotmarket)'] = 0

        self.key_params['Total Emissions OM'] = (
            self.data_all['Emissions OM'].sum()
            )

    def run_model(self):
        self.generate_buses()
        self.generate_sources()
        self.generate_sinks()
        self.generate_components()
        self.solve_model()

    def run_postprocessing(self):
        self.get_results()
        self.calc_econ_params()
        self.calc_ecol_params()

def calc_bwsf(i, n):
    """Berechne Barwert Summenfaktor.
    
    Parameters:
    -----------
    i : float
        Kapitalzins als rationale Zahl (nicht Prozent)

    n : int
        Lebensdauer des Investments in Jahren
    """
    q = 1+i
    return (q**n - 1)/(q**n * (q - 1))

def LCOH(invest, cost, Q, revenue=0, i=0.05, n=20):
    """Konstantin 2013, Markus [29].

    LCOH        Wärmegestehungskosten
    invest:     Investitionsausgaben zum Zeitpunkt t=0
    bwsf:       Barwert Summenfaktor
    cashflow:   Differenz aller Einnahmen und Ausgaben (Zahlungsströme)
                innerhalb des betrachteten Jahres
    Q:          Gesamte bereitgestellte Wärmemenge pro Jahr
    i:          Kalkulationszinssatz
    n:          Betrachtungsdauer
    """
    q = 1 + i
    bwsf = (q**n - 1)/(q**n * (q - 1))

    LCOH = (invest + bwsf * (cost - revenue))/(bwsf * Q)
    return LCOH

def calc_cost(label, E_N, param, uc, cost_df, add_var_cost=None):
    """
    Calculate invest and operational cost for a unit.

    Parameters
    ----------

    label : str
        Label of unit to be used as column name in cost DataFrame.

    E_N : float
        Nominal rated energy that the specific cost relate to.

    param : dict
        JSON parameter file of user defined constants.

    uc : pandas.DataFrame
        DataFrame containing the units results of the unit commitment
        optimization.

    cost_df : pandas.DataFrame
        DataFrame in which the calculated cost should be inserted.
    """
    cost_df.loc['invest', label] =  param[label]['inv_spez'] * E_N
    cost_df.loc['op_cost_fix', label] = param[label]['op_cost_fix'] * E_N
    cost_df.loc['op_cost_var', label] = (
        param[label]['op_cost_var'] * uc.sum()
        )
    if add_var_cost:
        cost_df.loc['op_cost_var', label] += add_var_cost * uc.sum()
    cost_df.loc['op_cost', label] = (
        cost_df.loc['op_cost_fix', label] + cost_df.loc['op_cost_var', label]
        )

    return cost_df

def result_labeling(df, debug=True, **kwargs):
    """
    Relabel the column names of oemof.solve result dataframes.

    Parameters
    ----------

    df : pandas.DataFrame
        DataFrame containing the results whose column names should be relabeled.
    """
    labeldict = {}
    if isinstance(df, pd.DataFrame):
        for col in df.columns:
            if not isinstance(col, tuple):
                if debug:
                    print(f'Edge "{col}" was skipped while labeling.')
                continue
            labeldict[col] = check_column(col, debug)
        df.rename(columns=labeldict, inplace=True)

    elif isinstance(df, pd.Series):
        for col in df.index:
            if not isinstance(col, tuple):
                if debug:
                    print(f'Edge "{col}" was skipped while labeling.')
                continue
            labeldict[col] = check_column(col, debug)
        df.rename(index=labeldict, inplace=True)

def check_column(col, debug):
    if col[0][1] == 'heat network':
        if col[0][0].rstrip('0123456789') == 'hp':
            if col[1] == 'flow':
                return f'Q_out_{col[0][0]}'
            elif col[1] == 'invest':
                return f'cap_{col[0][0]}'
            elif col[1] == 'status':
                return f'state_{col[0][0]}'
            elif col[1] == 'status_nominal':
                return f'state_nom_{col[0][0]}'
        elif col[0][0].rstrip('0123456789') == 'tes':
            if col[1] == 'flow':
                return f'Q_out_{col[0][0]}'
            elif col[1] == 'invest':
                return f'cap_out_{col[0][0]}'
            elif col[1] == 'status':
                return f'state_out_{col[0][0]}'
            elif col[1] == 'status_nominal':
                return f'state_nom_out_{col[0][0]}'
            elif col[1] == 'total':
                return f'total_out_{col[0][0]}'
        else:
            if col[1] == 'flow':
                return f'Q_{col[0][0]}'
            elif col[1] == 'invest':
                return f'cap_{col[0][0]}'
            elif col[1] == 'status':
                return f'state_{col[0][0]}'
            elif col[1] == 'status_nominal':
                return f'state_nom_{col[0][0]}'

    elif col[0][0] == 'heat network':
        if col[0][1].rstrip('0123456789') == 'tes':
            if col[1] == 'flow':
                return f'Q_in_{col[0][1]}'
            elif col[1] == 'invest':
                return f'cap_in_{col[0][1]}'
            elif col[1] == 'status':
                return f'state_in_{col[0][1]}'
            elif col[1] == 'status_nominal':
                return f'state_nom_in_{col[0][1]}'
            elif col[1] == 'total':
                return f'total_in_{col[0][1]}'
        elif col[0][1] == 'heat demand':
            return 'Q_demand'

    elif col[0][1] == 'chp node':
        if col[1] == 'flow':
            return f'P_{col[0][0]}'

    elif col[0][0] == 'electricity network':
        if col[0][1].rstrip('0123456789') == 'hp':
            if col[1] == 'flow':
                return f'P_in_{col[0][1]}'
            elif col[1] == 'status':
                return f'state_{col[0][1]}'
        else:
            return f'P_{col[0][1]}'

    elif col[0][0] == 'gas network':
        return f'H_{col[0][1]}'

    elif col[0][0] == 'chp node':
        if col[0][1] == 'spotmarket':
            return 'P_spotmarket'
        elif col[0][1] == 'chp internal':
            return 'P_internal'

    elif col[0][0] == 'chp internal':
        if col[0][1] == 'electricity network':
            return 'P_internal'

    elif col[0][0] == 'gas source':
        return 'H_source'

    elif col[0][0] == 'electricity source':
        return 'P_source'

    elif col[0][0].rstrip('0123456789') == 'tes' and col[0][1] == 'None':
        if col[1] == 'storage_content':
            return f'storage_content_{col[0][0]}'
        elif col[1] == 'invest':
            return f'cap_{col[0][0]}'

    else:
        if debug:
            print(f'Edge "{col}" could not be labeled.')

# def result_labeling(df, labeldictpath='labeldict.csv'):
#     """
#     Relabel the column names of oemof.solve result dataframes.

#     Parameters
#     ----------

#     df : pandas.DataFrame
#         DataFrame containing the results whose column names should be relabeled.
    
#     labeldictpath : str
#         Relative path to the labeldict csv file. Defaults to a path in the same
#         directory.
#     """
#     labeldict_csv = pd.read_csv(labeldictpath, sep=';', na_filter=False)

#     labeldict = dict()
#     for idx in labeldict_csv.index:
#         labeldict[
#             ((labeldict_csv.loc[idx, 'name_out'],
#               labeldict_csv.loc[idx, 'name_in']),
#               labeldict_csv.loc[idx, 'type'])
#             ] = labeldict_csv.loc[idx, 'label']

#     if isinstance(df, pd.DataFrame):
#         for col in df.columns:
#             if col in labeldict.keys():
#                 df.rename(columns={col: labeldict[col]}, inplace=True)
#             else:
#                 print(f'Column name "{col}" not in "{labeldictpath}".')
#     elif isinstance(df, pd.Series):
#         for idx in df.index:
#             if idx in labeldict.keys():
#                 df.rename(index={idx: labeldict[idx]}, inplace=True)
#             else:
#                 print(f'Column name "{idx}" not in "{labeldictpath}".')

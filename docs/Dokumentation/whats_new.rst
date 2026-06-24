~~~~~~~~~~
What's New
~~~~~~~~~~

v0.0.6 (Jun 24, 2026)
=====================

New Features
------------

- Add more locations for solar thermal heat flow data
- Add datepicker and scale method for solar thermal heat flow
- Add short instructions for energy system and results
- Separate data in electricity supply expander
- Separate data in gas supply expander

Improvements
------------

- Extend statefulness to the entire tool
- Improve robustness of result processing
- Add further information about the user selected heat load
- Rename peak load boiler to gas boiler
- Adjust subheader and title labeling of constant and own electricty price data
- Add new and improve old tooltips
- Remove user survey qr code and link in the sidebar
- Remove unused TEHG Bonus

Fixes
-----

- Fix postprocessing calculation bug of net costs
- Fix typos

Contributors
------------

- `@maltefritz <https://github.com/maltefritz>`__
- `@jfreissmann <https://github.com/jfreissmann>`__
- `@Coelopsychis <https://github.com/Coelopsychis>`__


v0.0.5 (Apr 29, 2026)
=====================

New Features
------------

- Add automated result report
- Add net costs methods 'total' and 'exclude net'
- Configure color theme

Improvements
------------

- Improve tool statefulnes
- Update README installation reference to current package structure
- Improve result visualization
- Add new and improve old tooltips


Fixes
-----

- Add graceful error handling for early move into results or conclusion
- Fix solar data to not already include collector efficiency
- Fix co2 price bug where emission factor for gas is multiplied twice
- Fix critical bug when defining conversion factors
- Fix pandas dataframe error
- Fix error with large data set plots in altair
- Fix typos

Contributors
------------

- `@maltefritz <https://github.com/maltefritz>`__
- `@jfreissmann <https://github.com/jfreissmann>`__


v0.0.4 (Nov 03, 2025)
=====================

New Features
------------

- Allow constant electricity and gas prices
- Allow user changes for additional el. price fees and taxes
- Allow relative investment and operational cost subsidies
- Add basic network cost calculation

Improvements
------------

- Add newer heat load data from the district heating system of Flensburg (2024)
- Add newer heat price time series (2024)
- Update streamlit version

Fixes
-----

- Fix typos
- Fix links

Contributors
------------

- `@maltefritz <https://github.com/maltefritz>`__
- `@jfreissmann <https://github.com/jfreissmann>`__


v0.0.3 (May 14, 2025)
=====================

New Features
------------

- Add support for SCIP solver
- Add tooltips
- Add check if units are able to supply the necessary heat load
- Add warnings for infeasable optimization problems
- Add solver availability check
- Improve formatting of numbers
- Add basic documentation structure
- Add helpful links

Improvements
------------

- Update energy system model to work with new oemof.solph version

Fixes
-----

- Fix multiple typos

Contributors
------------

- `@maltefritz <https://github.com/maltefritz>`__
- `@jfreissmann <https://github.com/jfreissmann>`__


v0.0.2 (Dec 03, 2024)
=====================

New Features
------------

- Add scaling methods for time series data
- Add external heat source unit
- Enable partial design optimization of units
- Allow download of results
- Add ability to use multiple instances of a heating unit
- Add ability to aggregate unit dispatch results
- Experimental: Allow users to upload saved energy systems

Improvements
------------

- Update streamlit version

Fixes
-----

- Fix multiple typos
- Fix bugs in result calculation and visualization
- Fix session state management of unit selection

Contributors
------------

- `@maltefritz <https://github.com/maltefritz>`__
- `@jfreissmann <https://github.com/jfreissmann>`__
- `@p-snft <https://github.com/p-snft>`__


v0.0.1 (May 17, 2024)
=====================

New Features
------------

- Basic tool structure
- Combined design and dispatch optimization
- Heat load, energy carrier prices and emission factor time series as well as
  other data until 2023
- Result plots for total heat production, unit commitment and storage content
- Add support for Gurobi and HiGHS

Contributors
------------

- `@jfreissmann <https://github.com/jfreissmann>`__
- `@maltefritz <https://github.com/maltefritz>`__

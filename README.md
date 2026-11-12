[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://owp-inno-nord.streamlit.app/)

# OWP Optimization Dashboard

Energy system optimization dashboard using mixed integer linear programming.
Developed as part of the project "Offene Wärmespeicherplanung (OWP)" as part of
*Inno!Nord* of the *T!Raum* initiative funded by the German Federal Ministry of
Research, Technology and Space.

## Key Features

- Combined invest and dispatch optimization based on [oemof.solph](https://github.com/oemof/oemof-solph)
- Parametrization and result visualization with a [Streamlit](https://github.com/streamlit/streamlit) dashboard
- Wide range of typical heating plants
- Comprehensive data base of heat load data, energy prices and emission factors

## Documentation

Detailed installation instructions, usage guides, troubleshooting and further information are available in the [OWP Optimization Dashboard documentation](https://owp-milp-optimization.readthedocs.io/de/latest/).

The documentation is currently available in German only. An English version will be added in the future.

## Funding

[<img src="https://raw.githubusercontent.com/maltefritz/owp_milp_optimization/main/src/owp_milp_optimization/img/Logos_F%C3%B6rderer_ohnePTJ_BMFTR.png">](https://www.innovation-strukturwandel.de/strukturwandel/shareddocs/entries/de/InnovationUndStrukturwandel/TRaum/innonord)

## Installation

Python 3.10 to 3.14 is supported, Python 3.11 is recommended. Create and activate a virtual environment.

### Windows

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
```

### macOS and Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install the dashboard and its dependencies from PyPI:

```bash
python -m pip install --upgrade pip
python -m pip install owp-milp-optimization
```

The open-source HiGHS solver is installed as a dependency and is used by default. No separate solver installation is required for the standard setup.

### Installation from source

To work on the code, clone the repository and install it in editable mode in the activated virtual environment:

```bash
git clone https://github.com/maltefritz/owp_milp_optimization.git
cd owp_milp_optimization
python -m pip install -e .
```

## Run the dashboard

Start the dashboard in the activated virtual environment:

```bash
owp-milp-optimization
```

If the command is not found, `python -m owp_milp_optimization` starts the dashboard as well.

Streamlit will normally open the dashboard automatically. Otherwise, open the displayed local address, usually:

```text
http://localhost:8501
```

Further options are passed on to Streamlit, e.g. to use another port:

```bash
owp-milp-optimization --server.port 8502
```

Stop the application by pressing `Ctrl+C`.

## License

The dashboard is licensed under the MIT License. See the [LICENSE](https://github.com/maltefritz/owp_milp_optimization/blob/main/LICENSE) file for further information.

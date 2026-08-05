[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://owp-inno-nord.streamlit.app/)

# OWP Optimization Dashboard

Energy system optimization dashboard using mixed integer linear programming.
Developed as part of the project "Offene Wärmespeicherplanung (OWP)" as part of
*Inno!Nord* of the *T!Raum* initiative funded by the German Federal Ministry of
Research, Technology and Space.

## Key Features

- Combined invest and dispatch optimization based on [oemof.solph](https://github.com/oemof/oemof-solph)
- Parametrization and result visualizaiton with a [Streamlit](https://github.com/streamlit/streamlit) dashboard
- Wide range of typical heating plants
- Comprehensive data base of heat load data, energy prices and emission factors

## Documentation

Detailed installation instructions, usage guides, troubleshooting and further information are available in the [OWP Optimization Dashboard documentation](https://owp-milp-optimization.readthedocs.io/de/latest/).

The documentation is currently available in German only. An English version will be added in the future.

## Funding

[<img src="src\owp_milp_optimization\img\Logos_Förderer_ohnePTJ_BMFTR.png">](https://www.innovation-strukturwandel.de/strukturwandel/de/innovation-strukturwandel/t_raum/t_raum_node.html)

## Installation

Python 3.11 is recommended. Clone the repository and navigate to its root directory:

```bash
git clone https://github.com/maltefritz/owp_milp_optimization.git
cd owp_milp_optimization
```

Create and activate a virtual environment.

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

Install the application and its dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install .
```

The open-source HiGHS solver is installed as a dependency and is used by default. No separate solver installation is required for the standard setup.

## Run the dashboard

The virtual environment must be active before starting the application.

### Windows

```bash
cd src\owp_milp_optimization
python -m streamlit run Home.py
```

### macOS and Linux

```bash
cd src/owp_milp_optimization
python -m streamlit run Home.py
```

Streamlit will normally open the dashboard automatically. Otherwise, open the displayed local address, usually:

```text
http://localhost:8501
```

Stop the application by pressing `Ctrl+C`/`Cmd+C`.

## License

See the `LICENSE` file for further information.

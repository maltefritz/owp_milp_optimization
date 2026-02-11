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

## Funding

[<img src="src\owp_milp_optimization\img\Logos_Förderer_ohnePTJ_BMFTR.png">](https://www.innovation-strukturwandel.de/strukturwandel/de/innovation-strukturwandel/t_raum/t_raum_node.html)

## Installation

For now, only direct download from the [GitHub Repository](https://github.com/jfreissmann/owp_milp_optimization) is supported, so just clone it locally or download a ZIP file of the code. If you are using [Miniforge](https://github.com/conda-forge/miniforge) or another environment management tool using [conda](https://docs.conda.io/en/latest/), you can create and activate a clean environment like this:

```
conda create -n my_new_env python=3.11
```

```
conda activate my_new_env
```

To use the optimization dashboard, the necessary dependencies have to be installed. In a clean environment from the root directory the installation from this file could look like this:

```
python -m pip install "c:\path\to\the\package"
```

If you have already navigated your terminal (e.g. cmd) to the package directory, the path string in the command above simplifies to a single period character ("."), which means the current working directory.

## Run the dashboard

Running the optimization dashboard is as easy as running the following command from the root directory in your virtual environment with dependencies installed:

```
streamlit run src\owp_milp_optimization\Home.py
```

## License

See the `LICENSE` file for further information.

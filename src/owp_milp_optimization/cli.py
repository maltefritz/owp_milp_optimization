"""Command line entry point of the dashboard.

After the installation, ``owp-milp-optimization`` starts the dashboard. It
does the same as ``streamlit run Home.py`` in the package directory.
"""
import sys
from pathlib import Path

from streamlit.web import cli as stcli

HOME = Path(__file__).parent / 'Home.py'


def main():
    """Start the dashboard with ``streamlit run``.

    Further arguments are passed on to ``streamlit run``, e.g.
    ``owp-milp-optimization --server.port 8502``. Streamlit reads the theme
    from ``.streamlit/config.toml`` next to ``Home.py``, so the dashboard can
    be started from any working directory.
    """
    sys.argv = ['streamlit', 'run', str(HOME), *sys.argv[1:]]
    stcli.main()

~~~~~~~~~~~~~~~
Start des Tools
~~~~~~~~~~~~~~~

Anwendung starten
=================

Die Anwendung sollte aus dem Verzeichnis gestartet werden, in dem sich
``Home.py`` und die Streamlit-Konfiguration befinden.

.. important::
   Die Anwendung muss aus derselben virtuellen Umgebung gestartet werden, in der das Tool installiert wurde.
   Andernfalls kann es zu Problemen bei der Nutzung kommen.


Windows
-------

.. code-block:: batch

   cd C:\Pfad\zum\owp_milp_optimization
   .venv\Scripts\activate
   cd src\owp_milp_optimization
   python -m streamlit run Home.py

macOS und Linux
---------------

.. code-block:: batch

   cd /pfad/zum/owp_milp_optimization
   source .venv/bin/activate
   cd src/owp_milp_optimization
   python -m streamlit run Home.py


Aufrufen des Tools
==================
Streamlit zeigt anschließend im Terminal eine lokale Adresse an. In der Regel
lautet sie:

.. code-block:: text

   http://localhost:8501

Die Anwendung wird normalerweise automatisch im Standardbrowser geöffnet.
Andernfalls kann die angezeigte Adresse manuell im Browser aufgerufen werden.

Der Streamlit-Prozess wird mit :kbd:`Strg+C` beziehungsweise auf macOS mit
:kbd:`Control+C` beendet.

Die virtuelle Umgebung kann nach der Nutzung mit folgendem Befehl verlassen
werden:

.. code-block:: batch

   deactivate

Alternativ genügt es auch, das Terminal zu schließen. Die Umgebung wird dann automatisch deaktiviert.

Fehlerbehebung
==============

Die virtuelle Umgebung ist nicht aktiv
---------------------------------------

Nach der Aktivierung sollte ``(.venv)`` am Anfang der Kommandozeile stehen. Der
verwendete Python-Interpreter kann geprüft werden.

Unter Windows:

.. code-block:: batch

   where python
   python -m pip --version

Unter macOS und Linux:

.. code-block:: batch

   which python
   python -m pip --version

Die ausgegebenen Pfade sollten auf den Ordner ``.venv`` im Repository
verweisen.

Streamlit wird nicht gefunden
-----------------------------

Wird die Meldung ``No module named streamlit`` angezeigt, ist Streamlit nicht
installiert. Dies kann daran liegen, dass die virtuelle Umgebung nicht
aktiviert ist (siehe oben) oder die Installation noch nicht durchgeführt wurde. Die Umgebung muss
aktiviert und das Projekt aus dem Hauptverzeichnis installiert werden:

.. code-block:: batch

   python -m pip install .

Port 8501 ist bereits belegt
----------------------------

Falls bereits eine andere Streamlit-Anwendung läuft, kann ein anderer Port
verwendet werden:

.. code-block:: batch

   python -m streamlit run Home.py --server.port 8502

Die Anwendung ist anschließend unter ``http://localhost:8502`` erreichbar.

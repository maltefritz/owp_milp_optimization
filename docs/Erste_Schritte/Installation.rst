~~~~~~~~~~~~
Installation
~~~~~~~~~~~~

Das Tool kann lokal unter Windows, macOS und Linux ausgeführt werden. Es wird als Python-Paket aus dem Python Package Index (PyPI) installiert. Für die Python-Abhängigkeiten wird eine virtuelle Umgebung mit :mod:`venv` verwendet. Für die Weiterentwicklung kann das Tool alternativ aus dem Quellcode installiert werden (siehe :ref:`installation-quellcode`).

.. note::

   Das Tool unterstützt Python 3.10 bis 3.14. Für diese Anleitung wird **Python 3.11** empfohlen. Diese Version wird auch für den Build der Online-Dokumentation eingesetzt.

Voraussetzungen
===============

Für die lokale Installation werden benötigt:

* Python 3.11,
* eine Internetverbindung zur Installation der Python-Pakete und
* ein aktueller Webbrowser.

Python sollte von der offiziellen `Python-Webseite <https://www.python.org/downloads/release/python-3119/>`__ oder über die Paketverwaltung des jeweiligen Betriebssystems installiert werden.

Installation unter Windows
==========================

Die folgenden Befehle sind für das Standard-Terminal vorgesehen.

Python-Version prüfen
---------------------

Zunächst wird geprüft, ob Python 3.11 über den Python Launcher verfügbar ist:

.. code-block:: batch

   py -3.11 --version

Die Ausgabe sollte beispielsweise ``Python 3.11.9`` lauten. Die genaue Patch-Version kann abweichen.

Virtuelle Umgebung erstellen
-----------------------------

In einem beliebigen Arbeitsordner, beispielsweise einem neuen Projektordner, wird eine virtuelle Umgebung namens ``.venv`` erstellt:

.. code-block:: batch

   py -3.11 -m venv .venv

Anschließend wird sie aktiviert:

.. code-block:: batch

   .venv\Scripts\activate

Nach der Aktivierung steht ``(.venv)`` am Anfang der Terminal-Eingabezeile.

Python-Pakete installieren
--------------------------

Innerhalb der aktivierten Umgebung wird zunächst ``pip`` aktualisiert:

.. code-block:: batch

   python -m pip install --upgrade pip

Danach werden das OWP-Tool und alle benötigten Abhängigkeiten installiert:

.. code-block:: batch

   python -m pip install owp-milp-optimization

Installation unter macOS
========================

Python-Version prüfen
---------------------

Im Terminal wird geprüft, ob Python 3.11 verfügbar ist:

.. code-block:: batch

   python3.11 --version

Die Ausgabe sollte eine Python-Version aus der Reihe 3.11 anzeigen.

Virtuelle Umgebung erstellen
-----------------------------

In einem beliebigen Arbeitsordner, beispielsweise einem neuen Projektordner, wird die virtuelle Umgebung erstellt:

.. code-block:: batch

   python3.11 -m venv .venv

Anschließend wird sie aktiviert:

.. code-block:: batch

   source .venv/bin/activate

Nach der Aktivierung sollte ``(.venv)`` am Anfang der Terminalzeile stehen.

Python-Pakete installieren
--------------------------

Innerhalb der aktivierten Umgebung werden ``pip`` und anschließend das OWP-Tool installiert:

.. code-block:: batch

   python -m pip install --upgrade pip
   python -m pip install owp-milp-optimization

Installation unter Linux
========================

Python-Version prüfen
---------------------

Im Terminal wird geprüft, ob Python 3.11 verfügbar ist:

.. code-block:: batch

   python3.11 --version

Zusätzlich muss das Python-Modul ``venv`` installiert sein. Bei einigen Linux-Distributionen wird es als separates Paket bereitgestellt, beispielsweise unter dem Namen ``python3.11-venv``. Der genaue Paketname und der Installationsbefehl hängen von der verwendeten Distribution ab.

Virtuelle Umgebung erstellen
-----------------------------

In einem beliebigen Arbeitsordner, beispielsweise einem neuen Projektordner, wird die virtuelle Umgebung erstellt:

.. code-block:: batch

   python3.11 -m venv .venv

Anschließend wird sie aktiviert:

.. code-block:: batch

   source .venv/bin/activate

Nach der Aktivierung sollte ``(.venv)`` am Anfang der Terminalzeile stehen.

Python-Pakete installieren
--------------------------

Innerhalb der aktivierten Umgebung werden ``pip`` und anschließend das OWP-Tool installiert:

.. code-block:: batch

   python -m pip install --upgrade pip
   python -m pip install owp-milp-optimization

Installation überprüfen
=======================

Nach der Installation kann geprüft werden, ob das OWP-Tool installiert ist:

.. code-block:: batch

   python -m pip show owp-milp-optimization

Es sollten unter anderem der Name und die installierte Version des Tools angezeigt werden.

.. note::
   Der Solver HiGHS wird zusammen mit den Python-Abhängigkeiten installiert. Für die Standardnutzung des OWP-Tools ist daher keine separate Solver-Installation notwendig. Weitere Informationen zu Solvern und deren Installation befinden sich in der Dokumentation unter :doc:`../Dokumentation/Solver`.

Anwendung starten
=================

Nach der Installation kann die Anwendung gestartet werden. Eine detaillierte Anleitung befindet sich in :doc:`Start`.

.. note::
   Die virtuelle Umgebung muss nur einmal erstellt und das Projekt nur einmal installiert werden. Bei einer späteren Nutzung genügen die Aktivierung der Umgebung und der erneute Start der Anwendung.

.. _installation-quellcode:

Installation aus dem Quellcode
==============================

Für die Weiterentwicklung oder um einen noch nicht veröffentlichten Stand zu nutzen, kann das Tool direkt aus dem GitHub-Repository installiert werden. Zusätzlich zu den oben genannten Voraussetzungen wird dafür Git oder ein als ZIP-Datei heruntergeladenes Repository benötigt.

Mit Git
-------

Das Repository wird mit folgendem Befehl heruntergeladen:

.. code-block:: batch

   git clone https://github.com/maltefritz/owp_milp_optimization.git
   cd owp_milp_optimization

Alle weiteren Befehle werden im Hauptverzeichnis des Repositorys ausgeführt (in diesem Verzeichnis befindet sich unter anderem die Datei ``pyproject.toml``).

Ohne Git
--------

Alternativ kann das Repository auf GitHub über **Code → Download ZIP** als ZIP-Datei heruntergeladen werden. Das Archiv muss anschließend entpackt und das Terminal im entpackten Hauptverzeichnis geöffnet werden.

Tool installieren
-----------------

Die virtuelle Umgebung wird wie oben für das jeweilige Betriebssystem beschrieben im Hauptverzeichnis des Repositorys erstellt und aktiviert. Anschließend wird das Tool aus dem Quellcode installiert:

.. code-block:: batch

   python -m pip install --upgrade pip
   python -m pip install .

.. tip::

   Für die Weiterentwicklung des Tools kann anstelle der normalen Installation eine editierbare Installation verwendet werden:

   .. code-block:: batch

      python -m pip install -e .

   Änderungen am lokalen Python-Quellcode werden dann ohne erneute Installation wirksam.

Projekt aktualisieren
=====================

Eine neue Version des Tools wird in der aktivierten virtuellen Umgebung installiert mit:

.. code-block:: batch

   python -m pip install --upgrade owp-milp-optimization

Bei einer Installation aus dem Quellcode mit Git wird der aktuelle Stand im Hauptverzeichnis des Repositorys abgerufen:

.. code-block:: batch

   git pull

Wenn sich die Abhängigkeiten in ``pyproject.toml`` geändert haben, sollte das Projekt anschließend in der aktivierten virtuellen Umgebung erneut installiert werden:

.. code-block:: batch

   python -m pip install .

Fehlerbehebung
==============

Python wird nicht gefunden
------------------------------------------

Python ist entweder nicht installiert oder nicht über die Kommandozeile erreichbar. Unter Windows sollte bei der Python-Installation der Python Launcher mitinstalliert werden. Unter macOS und Linux muss gegebenenfalls der vollständige Befehl ``python3.11`` verwendet werden.

Die virtuelle Umgebung ist nicht aktiv
---------------------------------------

Nach der Aktivierung sollte ``(.venv)`` am Anfang der Kommandozeile stehen. Der verwendete Python-Interpreter kann geprüft werden.

Unter Windows:

.. code-block:: batch

   where python
   python -m pip --version

Unter macOS und Linux:

.. code-block:: batch

   which python
   python -m pip --version

Die ausgegebenen Pfade sollten auf den Ordner ``.venv`` verweisen.

Das Tool ist nicht installiert
------------------------------

Meldet ``python -m pip show owp-milp-optimization`` das Paket als nicht gefunden, ist das Tool in der aktiven Umgebung nicht installiert. Dies kann daran liegen, dass die virtuelle Umgebung nicht aktiviert ist (siehe oben) oder die Installation noch nicht durchgeführt wurde. Die Umgebung muss aktiviert und das Tool installiert werden:

.. code-block:: batch

   python -m pip install owp-milp-optimization

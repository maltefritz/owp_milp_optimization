~~~~~~
Solver
~~~~~~

Das Tool formuliert die Auslegung und den Betrieb des betrachteten Wärmeversorgungssystems als gemischt-ganzzahliges lineares Optimierungsproblem (Mixed-Integer Linear Program, MILP). Zur Lösung dieses Problems stehen drei Solver zur Auswahl:

* :ref:`solver-highs`,
* :ref:`solver-gurobi` und
* :ref:`solver-scip`.

Das mathematische Modell wird mit ``oemof.solph`` und ``Pyomo`` erstellt. Der ausgewählte Solver übernimmt anschließend die numerische Lösung des Modells.

.. note::

   **HiGHS ist der voreingestellte Solver.** Er wird zusammen mit dem Tool installiert und benötigt weder eine zusätzliche Installation noch eine Lizenz. Für einen unkomplizierten Einstieg sollte daher zunächst HiGHS verwendet werden.

Überblick
=========

.. list-table:: Vergleich der verfügbaren Solver
   :header-rows: 1
   :widths: 16 23 22 39

   * - Solver
     - Lizenz
     - Zusätzliche Installation
     - Einordnung
   * - HiGHS
     - MIT-Lizenz, Open Source
     - Nein
     - Standardempfehlung für eine unkomplizierte und frei verfügbare
       Installation
   * - Gurobi
     - Proprietär; kostenlose akademische Lizenzen verfügbar
     - Ja
     - Leistungsfähige Alternative, insbesondere für umfangreiche oder
       anspruchsvolle Modelle; für größere Modelle ist eine passende Lizenz
       erforderlich
   * - SCIP
     - Apache-2.0-Lizenz, Open Source
     - Ja
     - Frei verfügbare Alternative zu HiGHS; das ausführbare
       Kommandozeilenprogramm muss separat installiert werden

Die Solver können für dasselbe Modell unterschiedliche Rechenzeiten benötigen. Auch die interne Suche nach einer Lösung unterscheidet sich. Bei gleichen Modell- und Toleranzeinstellungen sollten die Zielfunktionswerte innerhalb der vorgegebenen Toleranzen übereinstimmen. Bei mehreren gleichwertigen Lösungen können sich einzelne Anlagenentscheidungen oder Dimensionierungen dennoch unterscheiden.

Solver im Tool auswählen
============================

Die Solver-Einstellungen befinden sich auf der Seite zur Konfiguration des Energiesystems im Reiter **Sonstiges** im Abschnitt **Optimierung**. Dort können folgende Einstellungen vorgenommen werden:

Solver
   Auswahl zwischen **HiGHS**, **Gurobi** und **SCIP**. Das Tool prüft bei der Auswahl, ob der Solver in der aktuellen Python-Umgebung beziehungsweise auf dem System verfügbar ist.

MIP Gap
   Zulässige relative Optimalitätslücke (Mixed-Integer Programming Gap) in Prozent. Der MIP Gap beschreibt den Abstand zwischen der besten gefundenen ganzzahligen Lösung und der besten bekannten Schranke für das globale Optimum.

   Ein MIP Gap von beispielsweise ``2`` bedeutet, dass der Solver die Suche beenden darf, sobald die relative Abweichung höchstens 2 % beträgt. Dies bedeutet nicht, dass alle ausgegebenen Größen einen Fehler von 2 % besitzen.

   Ein kleinerer MIP Gap erhöht den Anspruch an den Optimalitätsnachweis und kann die Rechenzeit deutlich verlängern. Ein Wert von ``0`` verlangt einen vollständigen Optimalitätsnachweis innerhalb der numerischen Toleranzen des Solvers und ist für große Modelle i.d.R. nicht zweckmäßig.

Zeitlimit
   Optionales Zeitlimit für die Optimierung in Minuten. Wird das Zeitlimit erreicht, kann der Solver eine bereits gefundene zulässige Lösung zurückgeben, obwohl die gewünschte Optimalitätslücke noch nicht erreicht wurde. Für die Bewertung der Ergebnisqualität sollten in diesem Fall die :ref:`solverprotokolle` geprüft werden.

.. _solver-highs:

HiGHS
=====

`HiGHS <https://highs.dev/>`__ ist ein frei verfügbarer Open-Source-Solver für lineare Optimierungsprobleme, gemischt-ganzzahlige Optimierungsprobleme und quadratische Optimierungsprobleme. HiGHS steht unter der MIT-Lizenz.

Einbindung in das Tool
--------------------------

HiGHS wird über das Python-Paket ``highspy`` und die APPSI-Schnittstelle von Pyomo eingebunden. ``highspy`` ist eine reguläre Abhängigkeit des Tools und wird bei der im Kapitel :doc:`../Erste_Schritte/Installation` beschriebenen Installation automatisch installiert:

.. code-block:: batch

   python -m pip install .

Für die Weiterentwicklung des Tools kann stattdessen die editierbare Installation verwendet werden:

.. code-block:: batch

   python -m pip install -e .

Eine separate ausführbare HiGHS-Datei und eine zusätzliche Lizenz sind für die Verwendung im Tool nicht erforderlich.

Installation prüfen
--------------------

Innerhalb der aktivierten virtuellen Umgebung kann die Verfügbarkeit mit folgendem Befehl geprüft werden:

.. code-block:: batch

   python -c "from pyomo.contrib.appsi.solvers import Highs; print('HiGHS verfügbar:', bool(Highs().available()))"

Bei erfolgreicher Installation wird ausgegeben:

.. code-block:: text

   HiGHS verfügbar: True

Weitere Informationen zur Python-Schnittstelle enthält die `HiGHS-Dokumentation <https://ergo-code.github.io/HiGHS/stable/interfaces/python/>`__.

.. _solver-gurobi:

Gurobi
======

`Gurobi Optimizer <https://www.gurobi.com/>`__ ist ein proprietärer kommerzieller Optimierungssolver. Für Angehörige anerkannter akademischer Einrichtungen bietet Gurobi kostenlose akademische Lizenzen für Forschung, Lehre und Studium an. Für eine kommerzielle oder operative Nutzung ist eine entsprechende Lizenz erforderlich.

Installation
------------

Gurobi ist nicht Bestandteil der Standardinstallation dieses Tools. Das Python-Paket wird innerhalb der aktivierten virtuellen Umgebung installiert.

Windows mit CMD:

.. code-block:: batch

   .venv\Scripts\activate.bat
   python -m pip install gurobipy

macOS und Linux:

.. code-block:: batch

   source .venv/bin/activate
   python -m pip install gurobipy

Das über ``pip`` installierte Paket enthält eine größenbeschränkte Lizenz für kleine Modelle. Reale OWP-Optimierungen können diese Größenbeschränkung überschreiten. In diesem Fall muss eine geeignete Gurobi-Lizenz eingerichtet werden.

Informationen zur Installation befinden sich in der `Gurobi-Installationsanleitung für Python <https://support.gurobi.com/hc/en-us/articles/360044290292-How-do-I-install-Gurobi-for-Python>`__. Die verfügbaren akademischen Lizenzmodelle werden in der `Anleitung für akademische Lizenzen <https://support.gurobi.com/hc/en-us/articles/360040541251-How-do-I-obtain-a-free-academic-license>`__ beschrieben.

Installation und Lizenz prüfen
-------------------------------

Zunächst kann geprüft werden, ob das Python-Paket importiert werden kann:

.. code-block:: batch

   python -c "import gurobipy as gp; print('Gurobi-Version:', gp.gurobi.version())"

Anschließend kann die Erkennung durch Pyomo geprüft werden:

.. code-block:: batch

   python -c "from pyomo.opt import check_available_solvers; print('Gurobi verfügbar:', 'gurobi' in check_available_solvers('gurobi'))"

Bei einer funktionierenden Installation wird ausgegeben:

.. code-block:: text

   Gurobi verfügbar: True

.. warning::

   Eine erfolgreiche Erkennung des Solvers garantiert nicht, dass die vorhandene Lizenz für die Größe des gewählten Modells ausreicht. Die Meldung ``Model too large for size-limited Gurobi license`` weist darauf hin, dass eine uneingeschränkte beziehungsweise ausreichend große Lizenz eingerichtet werden muss.

.. _solver-scip:

SCIP
====

`SCIP <https://www.scipopt.org/>`__ ist ein Open-Source-Solver für gemischt-ganzzahlige und weitere Optimierungsprobleme. Aktuelle SCIP-Versionen stehen unter der Apache-2.0-Lizenz. Abhängig von den beim Buildprozess eingebundenen optionalen Komponenten können zusätzliche Lizenzbedingungen gelten.

Besonderheit der Einbindung
---------------------------

Das OWP-Tool verwendet für SCIP die Kommandozeilenschnittstelle von Pyomo. Dafür muss das ausführbare Programm ``scip`` beziehungsweise unter Windows ``scip.exe`` installiert und über die Umgebungsvariable ``PATH`` auffindbar sein.

.. important::

   Die alleinige Installation von ``pyscipopt`` mit ``pip`` genügt für die derzeitige SCIP-Einbindung des OWP-Tools **nicht**. ``pyscipopt`` stellt eine eigene Python-Schnittstelle bereit, während das OWP-Tool das externe Kommandozeilenprogramm ``scip`` aufruft.

Installation unter Windows
--------------------------

1. Die aktuelle SCIP Optimization Suite von der `offiziellen Downloadseite <https://www.scipopt.org/index.php#download>`__ herunterladen.
2. Den Installer ausführen oder das ZIP-Archiv entpacken.
3. Das Verzeichnis, das ``scip.exe`` enthält, zur Windows-Umgebungsvariable ``PATH`` hinzufügen.
4. Den PC neu starten, damit der aktualisierte ``PATH`` übernommen wird.

Danach wird die Installation im Terminal geprüft:

.. code-block:: batch

   scip --version

Installation unter macOS
------------------------

SCIP kann unter macOS beispielsweise mit Homebrew installiert werden:

.. code-block:: batch

   brew install scip

Alternativ können die auf der `SCIP-Downloadseite <https://www.scipopt.org/index.php#download>`__ angebotenen Pakete verwendet oder SCIP aus dem Quellcode erstellt werden. Die Verfügbarkeit vorkompilierter Pakete hängt von der Prozessorarchitektur und der SCIP-Version ab.

Die Installation wird anschließend geprüft:

.. code-block:: batch

   scip --version

Installation unter Linux
------------------------

Für Linux stellt das SCIP-Projekt je nach Distribution und Architektur vorkompilierte Pakete und Archive bereit. Diese können über die `SCIP-Downloadseite <https://www.scipopt.org/index.php#download>`__ heruntergeladen und entsprechend der dortigen Anleitung installiert werden. Alternativ kann SCIP mit CMake aus dem Quellcode gebaut werden.

Nach der Installation muss das Verzeichnis mit dem Programm ``scip`` im ``PATH`` enthalten sein. Die Installation wird mit folgendem Befehl geprüft:

.. code-block:: batch

   scip --version

Erkennung durch Pyomo prüfen
----------------------------

Unabhängig vom Betriebssystem kann anschließend in der aktivierten virtuellen Umgebung geprüft werden, ob Pyomo SCIP findet:

.. code-block:: batch

   python -c "from pyomo.opt import check_available_solvers; print('SCIP verfügbar:', 'scip' in check_available_solvers('scip'))"

Bei einer funktionierenden Installation wird ausgegeben:

.. code-block:: text

   SCIP verfügbar: True

Weitere Installationsinformationen enthält die `offizielle SCIP-Installationsdokumentation <https://www.scipopt.org/doc/html/INSTALL.php>`__.

Welcher Solver sollte verwendet werden?
=======================================

Für die meisten Anwenderinnen und Anwender ist folgende Reihenfolge sinnvoll:

1. **HiGHS** verwenden, wenn keine besonderen Anforderungen bestehen. Der Solver ist bereits installiert, frei verfügbar und ohne Lizenz nutzbar.
2. **Gurobi** testen, wenn für große oder schwierige Modelle kürzere Rechenzeiten benötigt werden und eine geeignete Lizenz verfügbar ist.
3. **SCIP** als weitere frei verfügbare Alternative einsetzen, wenn die zusätzliche Systeminstallation möglich ist oder Solverergebnisse verglichen werden sollen.

.. tip::

   Gurobi ist in der Regel deutlich leistungsfähiger als HiGHS und SCIP. Für große oder schwierige Modelle kann die Rechenzeit deutlich kürzer sein. Sofern ein Einsatz im akademischen Kontext geplant ist bzw. den entsprechenden Lizenzbedingungen entsprochen wird, sollte eine `kostenlose akademische Lizenz <https://www.gurobi.com/academics>`__ heruntergeladen und Gurobi als Solver genutzt werden.

.. _solverprotokolle:

Solverprotokolle
================

Bei jeder Optimierung erzeugt das Tool ein Solverprotokoll. Die Dateien werden im Quellverzeichnis unter folgendem Pfad gespeichert:

.. code-block:: text

   src/owp_milp_optimization/solverlogs/

Der Dateiname richtet sich nach dem ausgewählten Solver:

.. code-block:: text

   highs_log.txt
   gurobi_log.txt
   scip_log.txt

Ein vorhandenes Protokoll desselben Solvers wird beim nächsten Lauf ersetzt. Das Protokoll enthält je nach Solver unter anderem Angaben zum Modell, Lösungsfortschritt, Zielfunktionswert, MIP Gap, Zeitlimit und Abbruchgrund. Bei unerwarteten Ergebnissen oder vorzeitig beendeten Optimierungen sollte diese Datei zuerst geprüft werden.

Fehlerbehebung
==============

Der Solver wird im Tool als nicht verfügbar angezeigt
----------------------------------------------------------

Die Streamlit-Anwendung muss aus derselben virtuellen Umgebung gestartet werden, in der das Tool und gegebenenfalls der zusätzliche Solver installiert wurden. Nach der Installation eines Solvers sollte Streamlit beendet und neu gestartet werden.

Unter Windows kann der verwendete Python-Interpreter im Terminal geprüft werden:

.. code-block:: batch

   where python
   python -m pip --version

Unter macOS und Linux:

.. code-block:: batch

   which python
   python -m pip --version

Die ausgegebenen Pfade sollten auf die virtuelle Umgebung ``.venv`` im Repository verweisen.

HiGHS ist nicht verfügbar
-------------------------

Das Projekt wurde möglicherweise nicht vollständig in der aktiven virtuellen Umgebung installiert. Aus dem Hauptverzeichnis des Repositorys kann die Installation wiederholt werden:

.. code-block:: batch

   python -m pip install .

Für eine editierbare Installation:

.. code-block:: batch

   python -m pip install -e .

Gurobi meldet einen Lizenzfehler
--------------------------------

Prüfen Sie, ob eine gültige und für den Anwendungsfall geeignete Lizenz eingerichtet ist. Eine über ``pip`` mitgelieferte größenbeschränkte Lizenz reicht möglicherweise nicht aus. Hinweise zur Einrichtung enthält die `Gurobi-Lizenzdokumentation <https://support.gurobi.com/hc/en-us/articles/12872879801105-How-do-I-retrieve-and-set-up-a-Gurobi-license>`__.

SCIP wird trotz Installation nicht gefunden
--------------------------------------------

Prüfen Sie zunächst, ob der folgende Befehl in einem neu geöffneten Terminal funktioniert:

.. code-block:: batch

   scip --version

Wird der Befehl nicht gefunden, liegt das Verzeichnis mit ``scip`` oder ``scip.exe`` nicht im ``PATH``. Nach einer Änderung des ``PATH`` müssen das Terminal bzw. der PC neu gestartet werden.

~~~~~~~~~~~~~~~
Start des Tools
~~~~~~~~~~~~~~~

Anwendung starten
=================

Die Anwendung wird mit dem Befehl ``owp-milp-optimization`` gestartet. Das Verzeichnis, aus dem der Befehl aufgerufen wird, spielt dabei keine Rolle. In den folgenden Beispielen ist der Pfad der Ordner, in dem die virtuelle Umgebung ``.venv`` erstellt wurde.

.. important::
   Die Anwendung muss aus derselben virtuellen Umgebung gestartet werden, in der das Tool installiert wurde. Andernfalls kann es zu Problemen bei der Nutzung kommen.


Windows
-------

.. code-block:: batch

   cd C:\Pfad\zum\Projektordner
   .venv\Scripts\activate
   owp-milp-optimization

macOS und Linux
---------------

.. code-block:: batch

   cd /pfad/zum/projektordner
   source .venv/bin/activate
   owp-milp-optimization


Aufrufen des Tools
==================

Streamlit zeigt anschließend im Terminal eine lokale Adresse an. In der Regel lautet sie:

.. code-block:: text

   http://localhost:8501

Die Anwendung wird normalerweise automatisch im Standardbrowser geöffnet. Andernfalls kann die angezeigte Adresse manuell im Browser aufgerufen werden.

Der Streamlit-Prozess wird mit :kbd:`Strg+C` beziehungsweise auf macOS mit :kbd:`Control+C` beendet.

Die virtuelle Umgebung kann nach der Nutzung mit folgendem Befehl verlassen werden:

.. code-block:: batch

   deactivate

Alternativ genügt es auch, das Terminal zu schließen. Die Umgebung wird dann automatisch deaktiviert.

Fehlerbehebung
==============

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

Der Befehl wird nicht gefunden
------------------------------

Wird ``owp-milp-optimization`` nicht als Befehl erkannt, ist meist die virtuelle Umgebung nicht aktiviert (siehe oben) oder das Tool noch nicht installiert. Die Umgebung muss aktiviert und das Tool installiert werden:

.. code-block:: batch

   python -m pip install owp-milp-optimization

Ist das Tool installiert und wird der Befehl trotzdem nicht gefunden, kann die Anwendung auch über Python gestartet werden:

.. code-block:: batch

   python -m owp_milp_optimization

Port 8501 ist bereits belegt
----------------------------

Falls bereits eine andere Streamlit-Anwendung läuft, kann ein anderer Port verwendet werden:

.. code-block:: batch

   owp-milp-optimization --server.port 8502

Die Anwendung ist anschließend unter ``http://localhost:8502`` erreichbar.

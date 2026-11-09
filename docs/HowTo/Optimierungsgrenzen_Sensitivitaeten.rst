~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Optimierungsgrenzen und Sensitivitätsanalysen
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bei einer Auslegungsoptimierung kann das OWP-Tool die installierte Größe einer Anlage innerhalb vorgegebener Grenzen bestimmen. Diese Grenzen gehören zum mathematischen Modell und beeinflussen damit unmittelbar den zulässigen Lösungsraum. Liegt eine optimierte Kapazität an oder nahe an einer vorgegebenen Grenze, sollte deshalb geprüft werden, ob die Grenze das Ergebnis beeinflusst.

Dieses How-To zeigt, wie Kapazitätsgrenzen im OWP-Tool festgelegt und interpretiert werden und wie darauf aufbauend einfache Sensitivitätsanalysen durchgeführt werden können. Als Beispiel wird die Wärmepumpe aus dem Tutorial :doc:`/Erste_Schritte/Erstes_Energiesystem` verwendet.

Wann ist eine Sensitivitätsanalyse sinnvoll?
============================================

Eine Optimierung liefert die kostenminimale Lösung für die gewählten Eingangsdaten, Modellannahmen und Randbedingungen. Ändern sich diese Annahmen, kann sich auch die optimale Anlagenkonfiguration ändern. Eine Sensitivitätsanalyse ist daher insbesondere sinnvoll,

* wenn eine optimierte Kapazität an oder nahe an ihrer minimalen oder maximalen Grenze liegt
* wenn unsichere Annahmen wie Energiepreise, Investitionskosten, Förderungen oder Wirkungsgrade einen großen Einfluss auf das Ergebnis haben könnten (in der Regel der Fall)
* wenn verschiedenartige Entwicklungen der Rahmenbedingungen untersucht werden sollen
* wenn geprüft werden soll, ob eine gefundene Lösung auch bei veränderten Annahmen ähnlich bleibt.

Für einen gut nachvollziehbaren Vergleich sollte zunächst jeweils nur eine Annahme verändert werden. Sollen mehrere gemeinsam auftretende Entwicklungen untersucht werden, können anschließend zusätzliche Szenarien mit mehreren gleichzeitig veränderten Parametern gebildet werden.

Kapazitätsoptimierung im OWP-Tool
=================================

Die Kapazitätsoptimierung wird auf der Seite **Energiesystem** im Reiter **Anlagen** für jede ausgewählte Versorgungsanlage separat eingestellt. Wird der Schalter **Kapazität optimieren** aktiviert, wird die feste installierte Kapazität ausgeblendet und durch eine minimale und eine maximale installierbare Kapazität ersetzt.

Welche Größe optimiert wird, hängt vom Anlagentyp ab:

.. list-table:: Kapazitätsgrenzen im OWP-Tool
   :header-rows: 1
   :widths: 36 32 32

   * - Anlagentyp
     - Untere Grenze
     - Obere Grenze
   * - Leistungsbasierte Anlagen, beispielsweise Wärmepumpe, BHKW oder Gaskessel
     - Minimal installierbare Leistung in MW
     - Maximal installierbare Leistung in MW
   * - Solarthermie
     - Minimal installierbare Kollektorfläche in m²
     - Maximal installierbare Kollektorfläche in m²
   * - Wärmespeicher
     - Minimal installierbare Speicherkapazität in MWh
     - Maximal installierbare Speicherkapazität in MWh

.. important::

   Die Felder **Minimal installierbare Leistung** und **Maximal installierbare Leistung** begrenzen die installierte Anlagengröße. Sie beschreiben nicht die minimale oder maximale stündliche Betriebsleistung der Anlage.

Wird als untere Grenze ``0`` eingetragen, kann die Optimierung vollständig auf die Installation der Anlage verzichten. Eine untere Grenze größer als 0 erzwingt dagegen mindestens die angegebene Kapazität. Dies sollte also nur verwendet werden, wenn eine entsprechende Mindestgröße tatsächlich Teil der untersuchten Randbedingungen ist.

Wird **Kapazität optimieren** deaktiviert, wird keine Anlagengröße bestimmt. Stattdessen wird je nach Anlagentyp direkt die **Installierte Leistung**, **Installierte Kollektorfläche** oder **Installierte Speicherkapazität** vorgegeben und ausschließlich der Anlageneinsatz optimiert.

.. note::

   Die Kapazitätsoptimierung erfolgt kontinuierlich innerhalb der angegebenen Grenzen. Eine optimierte Leistung von beispielsweise 9,6 MW bedeutet natürlich nicht, dass eine reale Anlage genau in dieser Größe verfügbar sein muss. Falls nur bestimmte Anlagengrößen oder konkrete Produktvarianten zulässig sind, sollten diese im Anschluss an die erste Optimierung als eigene Szenarien (mit vorgegebener fester Kapazität) untersucht werden.

Ergebnisse an Kapazitätsgrenzen interpretieren
==============================================

Die ermittelten Anlagenkapazitäten werden nach einer erfolgreichen Berechnung auf der Seite **Simulationsergebnisse** im Reiter **Überblick** ganz oben angezeigt.

Für die Interpretation können folgende Fälle unterschieden werden:

.. list-table:: Interpretation optimierter Kapazitäten
   :header-rows: 1
   :widths: 28 72

   * - Beobachtung
     - Interpretation
   * - Kapazität liegt klar innerhalb der Grenzen
     - Innerhalb des vorgegebenen Suchbereichs wurde eine Kapazität gefunden, die nicht unmittelbar durch eine Grenze bestimmt wird.
   * - Kapazität liegt nahe an der oberen Grenze
     - Eine größere Anlage könnte wirtschaftlich sein. Die obere Grenze sollte testweise erhöht werden.
   * - Kapazität entspricht der oberen Grenze
     - Das Optimum liegt vermutlich außerhalb des zugelassenen Bereichs. Es sollte definitiv eine Simulation mit einer höheren Obergrenze durchgeführt werden.
   * - Kapazität liegt nahe an oder auf der unteren Grenze
     - Eine kleinere Anlage könnte günstiger sein, oder die optimale Lösung sieht die Anlage überhaupt nicht vor. Bei einer Untergrenze größer als 0 sollte geprüft werden, ob diese Mindestgröße tatsächlich sinnvoll ist.
   * - Kapazität beträgt 0 bei einer Untergrenze von 0
     - Die Anlage wird unter den gewählten Annahmen nicht benötigt beziehungsweise ist gegenüber den verfügbaren Alternativen nicht wirtschaftlich genug, um installiert zu werden.

Wie nah ein Ergebnis an einer Grenze liegen muss, damit eine weitere Untersuchung erforderlich ist, lässt sich nicht allgemeingültig festlegen. Entscheidend ist, ob eine plausible Veränderung der Grenze die Fragestellung oder die wirtschaftliche Bewertung beeinflussen könnte.

.. note::

   Zu enge Kapazitätsgrenzen können auch dazu führen, dass der Wärmebedarf mit den ausgewählten Anlagen nicht gedeckt werden kann. Das OWP-Tool prüft die maximal verfügbare Wärmeleistung bereits bei der Konfiguration und weist darauf hin, wenn die gewählten Anlagen nach dieser Prüfung nicht ausreichen, um den maximalen Wärmebedarf zu decken.

Sensitivitätsanalyse einer Kapazitätsgrenze durchführen
=======================================================

Für eine einfache Sensitivitätsanalyse wird zunächst ein Basisszenario berechnet und anschließend die zu untersuchende Grenze verändert.

Basisszenario sichern
---------------------

Zunächst wird das ursprüngliche Szenario vollständig optimiert. Auf der Seite **Simulationsergebnisse** können die Ergebnisse über **Bericht herunterladen** bzw. **Daten exportieren** gespeichert werden. Dadurch stehen die Kennzahlen und Zeitreihen für den späteren Vergleich weiterhin zur Verfügung.

Kapazitätsgrenze verändern
--------------------------

Anschließend wird über die Navigation zur Seite **Energiesystem** zurückgekehrt. Im Reiter **Anlagen** wird die betreffende Anlage geöffnet und die zu untersuchende minimale oder maximale Kapazität angepasst. Alle anderen Eingaben sollten für diesen Vergleich unverändert bleiben.

Optimierung erneut durchführen
------------------------------

Über **Zur Optimierung** wird erneut auf die Seite **Optimierung** gewechselt. Anschließend wird die Berechnung mit **Optimierung starten** erneut ausgeführt.

Ergebnisse vergleichen
----------------------

Nach der Berechnung werden zunächst die optimierten Kapazitäten im Reiter **Überblick** verglichen. Zusätzlich sollten mindestens die wirtschaftlichen Kennzahlen und der Anlageneinsatz betrachtet werden. Je nach untersuchter Fragestellung können auch Gas- und Strombezug, Stromerlöse, Emissionen oder der Speicherbetrieb relevant sein.

Beispiel: Obergrenze der Wärmepumpe prüfen
==========================================

Im Tutorial :doc:`/Erste_Schritte/Erstes_Energiesystem` wird die Kapazität einer neuen Wärmepumpe zwischen 0 und 10 MW optimiert. Die Optimierung ergibt eine Wärmepumpenleistung von rund 9,6 MW. Da dieser Wert nahe an der maximal installierbaren Leistung von 10 MW liegt, sollte geprüft werden, ob die gewählte Obergrenze das Ergebnis beeinflusst.

Dazu kann folgende kleine Sensitivitätsreihe durchgeführt werden:

.. list-table:: Beispielhafte Varianten
   :header-rows: 1
   :widths: 30 35 35

   * - Variante
     - Minimale Leistung
     - Maximale Leistung
   * - Basisszenario
     - 0 MW
     - 10 MW
   * - Sensitivität 1
     - 0 MW
     - 15 MW
   * - Sensitivität 2
     - 0 MW
     - 20 MW

Für die zweite Variante wird auf der Seite **Energiesystem** im Reiter **Anlagen** der Bereich **Wärmepumpe 1** geöffnet. **Kapazität optimieren** bleibt aktiviert und im Feld **Maximal installierbare Leistung in MW** wird ``15`` eingetragen. Für die dritte Variante wird derselbe Vorgang mit ``20`` MW wiederholt. Die übrigen Anlagenparameter und Randbedingungen bleiben unverändert.

Bleibt die optimierte Wärmepumpenleistung nach der Erhöhung der Obergrenze ungefähr auf dem bisherigen Niveau, spricht dies dafür, dass die ursprüngliche Grenze das Ergebnis nicht wesentlich eingeschränkt hat. Steigt die ermittelte Leistung dagegen deutlich an oder liegt sie erneut nahe an der neuen Obergrenze, war der ursprüngliche Suchbereich für die Auslegungsentscheidung eine Einschränkung und sollte weiter untersucht werden.

Nicht nur die Anlagenkapazität sollte verglichen werden. Eine veränderte Wärmepumpengröße kann beispielsweise den Einsatz von BHKW und Gaskessel, den Gasverbrauch, den Strombezug, die Stromerlöse und die Wärmegestehungskosten beeinflussen. Erst die gemeinsame Betrachtung dieser Größen zeigt, welche Folgen die veränderte Auslegung für das Gesamtsystem hat.

Weitere Parameter untersuchen
=============================

Sensitivitätsanalysen können auch für unsichere technische und wirtschaftliche Annahmen durchgeführt werden. Welche Parameter sinnvoll sind, hängt von der jeweiligen Fragestellung ab. Hier einige Beispiele:

* Wie wirkt ein anderer COP der Wärmepumpe?
* Wie wirken höhere Investitionskosten?
* Wie wirkt eine andere Förderung?
* Wie wirken höhere Gaspreise?
* Wie wirken andere Strompreise?
* Wie wirkt eine andere Wärmenachfrage?

Für die im Tool hinterlegten variablen Strom-, Gas- und CO₂-Preiszeitreihen steht im jeweiligen Bereich die Option **Daten skalieren** zur Verfügung. Bei der Methode **Faktor** wird die gesamte Zeitreihe mit einem Skalierungsfaktor multipliziert. Mit der Methode **Erweitert** können die Schwankungen um den Median über den **Stauchungsfaktor** verändert und die gesamte Zeitreihe zusätzlich über einen **Offset** verschoben werden.

Soll beispielsweise untersucht werden, wie das System auf allgemein höhere Gaspreise reagiert, kann im Reiter **Versorgung** unter **Gasversorgungsdaten** die vorhandene Gaspreiszeitreihe über **Daten skalieren** mit einem größeren Faktor versehen werden. Alternativ kann über die Preisvariante ``Konstant`` ein fester Gaspreis oder über ``Eigene Daten`` eine eigene Preiszeitreihe vorgegeben werden.

.. note::

   Für vergleichbare Ergebnisse sollten Solver und MIP Gap zwischen den Varianten unverändert bleiben. Die MIP Gap beschreibt die zulässige Optimalitätslücke der Zielfunktion und nicht eine prozentuale Unsicherheit einzelner Anlagenkapazitäten. Weitere Hinweise befinden sich unter :doc:`/Dokumentation/Solver`.

Typische Fehlinterpretationen
=============================

**„Die Optimierung hat die maximale Kapazität gewählt, also ist genau diese Größe optimal.“**
   Die Aussage gilt nur innerhalb der vorgegebenen Grenzen. Wird die Obergrenze erreicht, sollte ein größerer Suchbereich geprüft werden.

**„Eine Kapazität von 0 bedeutet, dass die Technologie grundsätzlich ungeeignet ist.“**
   Die Aussage gilt nur für die gewählten Eingangsdaten und die im Modell verfügbaren Alternativen. Bei anderen Energiepreisen, Kosten, Förderungen oder technischen Annahmen kann dieselbe Technologie wirtschaftlich werden.

**„Die beste Variante ist diejenige mit den niedrigsten Investitionskosten.“**
   Die Optimierung berücksichtigt neben Investitionskosten auch Betriebskosten und weitere im Modell enthaltene Erlöse und Kosten. Eine höhere Anfangsinvestition kann durch geringere laufende Kosten ausgeglichen werden.

**„Wenn sich eine Kennzahl verbessert, ist das Szenario insgesamt besser.“**
   Änderungen können gegenläufige Wirkungen haben. Beispielsweise können geringere Gaskosten mit höheren Stromkosten oder veränderten Stromerlösen einhergehen. Für eine belastbare Interpretation sollte deshalb das Gesamtsystem betrachtet werden.

.. note::

   Generell ist es empfehlenswert, die Ergebnisse einer Simulation einer Sensitivitätsanalyse zu unterziehen. Dies gilt umso mehr, je unsicherer die zugrunde liegenden Annahmen sind.

Kurzcheck für Sensitivitätsanalysen
===================================

Vor der Interpretation einer Sensitivitätsanalyse sollte geprüft werden:

* Wurde zwischen den Varianten nur die beabsichtigte Annahme verändert?
* Liegt eine optimierte Kapazität an oder nahe an einer Minimal- oder Maximalgrenze?
* Sind Einstellungen wie Solver und MIP Gap zwischen den Varianten einheitlich?
* Werden neben den optimierten Kapazitäten auch Kosten, Energiebezüge und Anlageneinsatz betrachtet?
* Lassen sich die beobachteten Änderungen technisch und wirtschaftlich erklären?

Eine Sensitivitätsanalyse liefert damit nicht nur zusätzliche Optimierungsergebnisse. Sie hilft vor allem dabei zu erkennen, welche Annahmen für die gefundene Systemauslegung entscheidend sind und wie belastbar die daraus abgeleiteten Schlussfolgerungen sind.

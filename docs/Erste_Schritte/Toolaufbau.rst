~~~~~~~~~~~~~~~~~~~~~~~~~
Wie benutze ich das Tool?
~~~~~~~~~~~~~~~~~~~~~~~~~

Das OWP-Tool führt schrittweise von der Beschreibung eines Wärmeversorgungssystems über die Optimierung bis zur Auswertung der Simulationsergebnisse. Die Bedienung erfolgt über vier Seiten:

#. die **Startseite** (Home) zur Einführung,
#. die Seite **Energiesystem** zur Eingabe aller Randbedingungen,
#. die Seite **Optimierung** zur Kontrolle und Berechnung des Modells und
#. die Seite **Simulationsergebnisse** zur Auswertung der Lösung.

Die Seiten können über die Navigation am linken Rand der Benutzeroberfläche aufgerufen werden.

.. important::

   Die Qualität der Ergebnisse hängt unmittelbar von den eingegebenen Daten und Annahmen ab. Eine mathematisch optimale Lösung ist nicht automatisch technisch, wirtschaftlich oder organisatorisch umsetzbar. Die Ergebnisse sollten daher stets auf Plausibilität geprüft werden.

Empfohlener Arbeitsablauf
=========================

Für eine neue Untersuchung empfiehlt sich folgender Ablauf:

#. Auf der Seite **Energiesystem** die Wärmelast, Wärmenetzdaten, die Systemgrenzen, die verfügbaren Anlagen und die Versorgungsdaten festlegen.
#. Auf der Seite **Optimierung** die Zusammenfassung kontrollieren und die Berechnung starten.
#. Auf der Seite **Simulationsergebnisse** die ermittelten Kapazitäten, Anlagenfahrpläne, Kennzahlen und Speicherverläufe auswerten.
#. Eingaben oder Annahmen gezielt verändern und die Ergebnisse verschiedener Szenarien miteinander vergleichen.

Für einen ersten Testlauf sollte zunächst ein überschaubares System mit wenigen Anlagen verwendet werden. So lassen sich Eingabefehler und unplausible Annahmen leichter erkennen, bevor umfangreichere Szenarien berechnet werden.

Startseite
==========

Die Startseite gibt eine kurze Einführung in die Energiesystemoptimierung und stellt die wesentlichen Möglichkeiten des OWP-Tools vor.

Was ist eine Optimierung?
-------------------------

Bei einer Optimierung wird aus einer großen Zahl möglicher Lösungen diejenige Lösung gesucht, welche die vorgegebene Zielfunktion unter Einhaltung aller Randbedingungen bestmöglich erfüllt. Das OWP-Tool ermittelt unter den getroffenen Annahmen eine kostenminimale Auslegung und/oder einen kostenminimalen Betrieb des betrachteten Wärmeversorgungssystems.

Zu den Randbedingungen gehören beispielsweise:

* die zu deckende Wärmelast,
* die verfügbaren Wärmeversorgungsanlagen,
* technische Grenzen der Anlagen und Speicher,
* Preise und Emissionsfaktoren der eingesetzten Energieträger sowie
* weitere systemweite Vorgaben.

Die Optimierung entscheidet damit nicht frei über alle denkbaren Wärmeversorgungssysteme, sondern ausschließlich innerhalb des durch die Eingaben beschriebenen Lösungsraums.

Auslegungs- und Einsatzoptimierung
----------------------------------

Mit dem OWP-Tool können unterschiedliche Fragestellungen untersucht werden:

Reine Einsatzoptimierung
   Die installierten Leistungen beziehungsweise Kapazitäten der Anlagen sind vorgegeben. Die Optimierung bestimmt, wann und mit welcher Leistung die Anlagen eingesetzt werden.

Kombinierte Auslegungs- und Einsatzoptimierung
   Neben dem optimalen Betrieb werden auch geeignete Anlagenleistungen oder Speicherkapazitäten ermittelt. Die Dimensionierung wird dabei gemeinsam mit dem späteren Einsatz betrachtet.

Gemischte Optimierung
   Innerhalb eines Systems können fest vorgegebene und frei zu dimensionierende Anlagen miteinander kombiniert werden. Beispielsweise kann eine bereits vorhandene Anlage mit fester Leistung berücksichtigt werden, während die Leistung einer neu zu errichtenden Anlage durch die Optimierung bestimmt wird.

Gerade die gemischte Betrachtung ist für Transformationsszenarien hilfreich, in denen bestehende Anlagen weitergenutzt und durch neue Technologien ergänzt werden sollen.

Energiesystem
=============

Auf der Seite **Energiesystem** werden die Eingangsdaten und Randbedingungen des Modells festgelegt. Die Eingaben sind auf die Reiter **Wärme**, **Netz**, **System**, **Anlagen**, **Versorgung** und **Sonstiges** verteilt.

Welche Eingabefelder angezeigt werden, kann teilweise von den zuvor ausgewählten Optionen und Anlagen abhängen.

Wärme
-----

Im Reiter **Wärme** wird der zu deckende Wärmebedarf beschrieben. Dazu wird eine Wärmelast-Zeitreihe aus den im Tool enthaltenen Daten ausgewählt oder durch eigene Daten ersetzt. Je nach Datengrundlage kann die Zeitreihe zusätzlich an den betrachteten Anwendungsfall angepasst oder skaliert werden.

Die Wärmelast ist eine zentrale Randbedingung des Modells: In jedem Zeitschritt muss die benötigte Wärme durch die ausgewählten Anlagen und Speicher bereitgestellt werden.

Netz
----

Im Reiter **Netz** werden die wärmenetzbezogenen Eigenschaften des betrachteten Wärmeversorgungssystems zusammengefasst (Trassenlänge und spezifische Kosten oder alternativ Gesamtkosten).

.. note::

   Die Netzverluste werden dadurch berücksichtigt, dass die im Reiter **Wärme** angegebene Wärmelast bereits die Verluste des Netzes enthält und somit der real zu erzeugenden Wärmemenge entspricht. Die Netzverluste werden also nicht zusätzlich im Modell berechnet. Die Vor- und Rücklauftemperaturen im Wärmenetz werden in dieser Modellierung nicht explizit berücksichtigt.

System
------

Im Reiter **System** können alle Anlagen ausgewählt werden, aus denen das zu optimierende Energiesystem bestehen soll. Dazu gehören sowohl Wärmeerzeuger als auch thermische Energiespeicher.

Anlagen
-------

Im Reiter **Anlagen** werden für die ausgewählten Anlagen die benötigten technischen und wirtschaftlichen Parameter angegeben. Dazu können unter anderem gehören:

* minimale und maximale Leistungen,
* Wirkungsgrade und Leistungszahlen,
* Investitions- und Betriebskosten,
* eventuelle Subventionen,
* Speicherleistung, Speicherkapazität und weitere technische Parameter.

Von besonderer Bedeutung ist die Festlegung, ob eine Anlagenkapazität bereits vorgegeben ist oder durch die Optimierung dimensioniert werden soll (Schalter **Kapazität optimieren**). Dadurch wird bestimmt, ob für die jeweilige Anlage eine reine Einsatzoptimierung oder eine kombinierte Auslegungs- und Einsatzoptimierung durchgeführt wird.

Versorgung
----------

Im Reiter **Versorgung** werden die von außen bezogenen oder abgegebenen Energieströme beschrieben. Dazu gehören die Preise und Emissionsfaktoren der verwendeten Energieträger sowie gegebenenfalls zeitabhängige Strommarkt- oder Brennstoffdaten.

Es besteht die Möglichkeit, vordefinierte Zeitreihen auszuwählen, eigene Zeitreihen hochzuladen oder feste Werte vorzugeben. Für die Elektrizitätsversorgung können die Strompreisbestandteile im Detail vorgegeben werden. Für die Gasversorgung können außerdem CO2-Preisdaten vorgegeben werden.

Diese Eingaben haben einen wesentlichen Einfluss auf den optimalen Anlageneinsatz. Beispielsweise können schwankende Strompreise dazu führen, dass elektrische Wärmeerzeuger und Speicher zu unterschiedlichen Zeiten eingesetzt werden.

Sonstiges
---------

Im Reiter **Sonstiges** befinden sich ergänzende Einstellungen für die Optimierung. Hier können der Kapitalzinssatz, die Betrachtungsdauer, eine Energiesteuer und vermiedene Netznutzungsentgelte konfiguriert werden. Außerdem können der zu verwendende Solver, die zulässige Optimalitätslücke (MIP Gap) und ein Zeitlimit festgelegt werden.

HiGHS ist voreingestellt und für die meisten Anwendungsfälle ein geeigneter Ausgangspunkt. Weitere Informationen zu den verfügbaren Solvern und ihren Einstellungen befinden sich auf der Seite :doc:`/Dokumentation/Solver`.

Eine kleinere Optimalitätslücke kann die Genauigkeit erhöhen, zugleich aber die Rechenzeit deutlich verlängern. Auch ein längerer Betrachtungszeitraum und viele frei dimensionierbare Anlagen vergrößern das Optimierungsproblem.

Optimierung
===========

Die Seite **Optimierung** dient als Kontroll- und Startpunkt der Berechnung. Sie fasst die wesentlichen Informationen des zuvor konfigurierten Energiesystems zusammen.

Vor dem Start sollte geprüft werden:

* ob die gewünschte Wärmelast ausgewählt wurde,
* ob alle benötigten Anlagen eingebunden wurden,
* ob die Versorgungsdaten plausibel sind und
* ob Solver und Lebensdauer sinnvoll gewählt sind.

Die Seite bietet außerdem die Möglichkeit, die Eingaben beziehungsweise das konfigurierte Energiesystem für eine spätere Verwendung zu sichern. Dies ist insbesondere sinnvoll, wenn mehrere Varianten desselben Grundsystems untersucht werden sollen.

Mit dem Button **Optimierung starten** wird aus den Eingaben das mathematische Modell erzeugt und anschließend an den ausgewählten Solver übergeben. Die Berechnungsdauer hängt stark von der Größe und Komplexität des Modells ab.

.. note::

   Während einer laufenden Optimierung sollte die Browserseite nicht neu geladen oder geschlossen werden. Bei einer lokalen Ausführung muss außerdem das Terminal geöffnet bleiben, in dem Streamlit gestartet wurde. Solange die Simulation läuft, zeigt Streamlit oben rechts eine Animation an.

Nach einer erfolgreichen Berechnung können die Ergebnisse auf der Seite **Simulationsergebnisse** ausgewertet werden. Kann keine Lösung gefunden werden, sollten zunächst die Eingaben auf widersprüchliche Randbedingungen, fehlende Daten oder zu enge technische Grenzen geprüft werden.

Simulationsergebnisse
=====================

Die Seite **Simulationsergebnisse** bereitet die Lösung der Optimierung in Kennzahlen, Tabellen und Zeitreihendiagrammen auf. Die Darstellung ist auf die Reiter **Überblick**, **Anlageneinsatz**, **Stromproduktion** und **Speicherstand** verteilt.

.. note::
  Welche Diagramme und Kennzahlen verfügbar sind, hängt vom konfigurierten Energiesystem ab.

Überblick
---------

Der Reiter **Überblick** fasst die wichtigsten Ergebnisse des Szenarios zusammen. Dazu zählen insbesondere:

* die vorgegebenen oder durch die Optimierung ermittelten Anlagenkapazitäten,
* die von den einzelnen Anlagen erzeugten Wärmemengen,
* wirtschaftliche Kennzahlen,
* die Wärmegestehungskosten und
* die verursachten Emissionen.

Dieser Reiter eignet sich besonders für den ersten Plausibilitätscheck und für den Vergleich mehrerer Szenarien. Auffällige Ergebnisse sollten anschließend mithilfe der zeitlich aufgelösten Darstellungen in den weiteren Reitern untersucht werden.

Anlageneinsatz
--------------

Der Reiter **Anlageneinsatz** zeigt den zeitlichen Verlauf der Wärmebereitstellung. Die Produktion der einzelnen Anlagen kann der Wärmelast gegenübergestellt werden.

Dadurch lässt sich unter anderem erkennen:

* welche Anlagen die Grundlast decken,
* welche Anlagen nur bei hohen Lasten eingesetzt werden,
* wann Anlagen ihre Leistungsgrenzen erreichen,
* wie sich Preise und andere Zeitreihen auf den Betrieb auswirken und
* ob das Einsatzverhalten technisch plausibel erscheint.

Für die Interpretation ist nicht nur die gesamte erzeugte Wärmemenge, sondern auch der zeitliche Verlauf entscheidend.

Stromproduktion
---------------

Der Reiter **Stromproduktion** stellt die elektrischen Energieströme des Systems dar. Er ist insbesondere relevant, wenn stromerzeugende oder stromverbrauchende Anlagen wie Kraft-Wärme-Kopplungsanlagen, Wärmepumpen oder elektrische Wärmeerzeuger berücksichtigt werden.

Abhängig vom gewählten System können hier beispielsweise Netzeinspeisung und interner Verbrauch miteinander verglichen werden. So lässt sich nachvollziehen, wie Wärme- und Stromsektor im optimierten Betrieb zusammenwirken.

Speicherstand
-------------

Der Reiter **Speicherstand** zeigt die zeitliche Entwicklung der Speicherfüllstände sowie die Be- und Entladung der berücksichtigten thermischen Energiespeicher.

Die Darstellung hilft bei der Beurteilung,

* wie häufig und wie stark ein Speicher genutzt wird,
* über welche Zeiträume Wärme verschoben wird,
* ob die Speicherkapazität regelmäßig vollständig ausgeschöpft wird und
* wie der Speicher den Betrieb der übrigen Anlagen beeinflusst.

Ein häufig vollständig gefüllter oder entleerter Speicher kann darauf hinweisen, dass eine andere Dimensionierung untersucht werden sollte. Eine geringe Nutzung bedeutet dagegen nicht automatisch, dass der Speicher überflüssig ist: Auch die Bereitstellung von Leistung in wenigen kritischen Zeiträumen kann für das Gesamtsystem relevant sein.

Erweitert
---------

Im Reiter **Erweitert** kann der Solverlog eingesehen werden. Für weitere Informationen zu den Solverlogs siehe :doc:`/Dokumentation/Solver`.

Ergebnisse richtig einordnen
============================

Beim Vergleich und bei der Interpretation der Ergebnisse sollten immer die zugrunde liegenden Annahmen berücksichtigt werden. Besonders wichtig sind:

Betrachtungszeitraum
   Ergebnisse eines kurzen Testzeitraums lassen sich nicht ohne Weiteres auf ein vollständiges Jahr übertragen.

Kosten- und Preisdaten
   Die ermittelte Lösung gilt für die verwendeten Investitionskosten, Energiepreise und weiteren wirtschaftlichen Annahmen.

Technische Vereinfachungen
   Das Modell bildet die in der Optimierung hinterlegten Zusammenhänge ab. Es ersetzt keine detaillierte Anlagen-, Netz- oder Genehmigungsplanung.

Optimalität
   Wurde die Optimierung mit einer zulässigen Optimalitätslücke oder einem Zeitlimit beendet, ist die beste gefundene Lösung vermutlich nicht mathematisch optimal. Sie kann dennoch für die untersuchte Fragestellung ausreichend genau sein.

Für belastbare Aussagen sollten daher mehrere Szenarien berechnet, Eingangsparameter variiert und die Ergebnisse auf technische sowie wirtschaftliche Plausibilität geprüft werden.

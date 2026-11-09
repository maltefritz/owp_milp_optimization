~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Wärmespeicher parametrisieren
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ein Wärmespeicher kann Wärme zeitlich verschieben. Wärme wird in Stunden mit günstiger oder überschüssiger Erzeugung aufgenommen und zu einem späteren Zeitpunkt wieder abgegeben. Damit ein Speicher im OWP-Tool abgebildet und das Optimierungsergebnis korrekt interpretiert werden kann, müssen Speicherkapazität, Be- und Entladeleistung, Wärmeverluste, Anfangs- und Endzustand sowie wirtschaftliche Parameter sinnvoll vorgegeben werden.

Dieses How-To beschreibt die Parametrisierung des Wärmespeichers im Tool und zeigt, wie die Ergebnisse im Reiter **Speicherstand** ausgewertet werden können. Als Beispiel wird der Speicher aus dem Tutorial :doc:`/Erste_Schritte/Erstes_Energiesystem` verwendet.

Abbildung des Wärmespeichers im OWP-Tool
========================================

Ein Wärmespeicher wird im OWP-Tool durch seine energetische Kapazität in MWh und durch maximale Be- und Entladeleistungen beschrieben. Zusätzlich wird berücksichtigt, dass während der Speicherdauer Wärme verloren geht. Der Speicher kann beliebig zwischen leer und vollständig gefüllt betrieben werden.

Im aktuellen Modell werden keine separaten Lade- und Entladewirkungsgrade vorgegeben. Verluste werden über den **Relativen Oberflächenwärmeverlust** in Abhängigkeit vom aktuellen Speicherfüllstand abgebildet. Ebenso wird keine Mindestreserve des Speicherfüllstands parametrisiert.

Die maximale Be- und Entladeleistung wird nicht direkt in MW eingegeben, sondern über das Verhältnis von Leistung zu Speicherkapazität festgelegt. Dadurch ändert sich die maximal mögliche Leistung automatisch mit der gewählten oder optimierten Speicherkapazität.

Wärmespeicher hinzufügen
========================

Auf der Seite **Energiesystem** wird im Reiter **System** unter **Wähle die Wärmeversorgungsanlagen aus, die im System verwendet werden können** ein Wärmespeicher ausgewählt. Anschließend erscheint im Reiter **Anlagen** ein eigener Bereich **Wärmespeicher 1**.

Soll eine bereits vorhandene Speichergröße untersucht werden, bleibt **Kapazität optimieren** deaktiviert und im Feld **Installierte Speicherkapazität in MWh** wird die vorhandene Kapazität eingetragen.

Soll die Speichergröße durch die Optimierung bestimmt werden, wird **Kapazität optimieren** aktiviert. Anschließend werden mit **Minimal installierbare Speicherkapazität in MWh** und **Maximal installierbare Speicherkapazität in MWh** die zulässigen Grenzen der Auslegung festgelegt.

.. note::

   Wird die minimale Speicherkapazität auf ``0`` gesetzt, darf die Optimierung auch vollständig auf den Speicher verzichten.

Weitere Hinweise zu solchen Kapazitätsgrenzen befinden sich unter :doc:`Optimierungsgrenzen_Sensitivitaeten`.

Technische Speicherparameter
============================

Die technischen Parameter werden im Bereich **Wärmespeicher 1** unter **Technische Parameter** eingestellt.

.. list-table:: Technische Parameter des Wärmespeichers
   :header-rows: 1
   :widths: 35 65

   * - Parameter im OWP-Tool
     - Bedeutung
   * - **Installierte Speicherkapazität in MWh** beziehungsweise minimale und maximale installierbare Speicherkapazität
     - Maximale Wärmemenge, die bei vollständig gefülltem Speicher enthalten sein kann. Bei aktivierter Kapazitätsoptimierung wird die Kapazität innerhalb der angegebenen Grenzen bestimmt.
   * - **Verhältnis von Beladeleistung zur Speicherkapazität**
     - Legt fest, wie groß die maximal mögliche Beladeleistung relativ zur Speicherkapazität ist.
   * - **Verhältnis von Entladeleistung zur Speicherkapazität**
     - Legt fest, wie groß die maximal mögliche Entladeleistung relativ zur Speicherkapazität ist.
   * - **Relativer Oberflächenwärmeverlust in %**
     - Anteil des aktuellen Speicherinhalts, der pro Zeitschritt als Wärmeverlust berücksichtigt wird.
   * - **Initialspeicherstand in %**
     - Relativer Speicherfüllstand zu Beginn der Simulation.
   * - **Ausgeglichener Speicher über Betrachtungsperiode**
     - Erzwingt, dass der Speicher am Ende des Betrachtungszeitraums wieder denselben Füllstand wie zu Beginn aufweist.

Speicherkapazität und Leistung unterscheiden
--------------------------------------------

Die Speicherkapazität beschreibt eine Energiemenge in MWh. Die Be- und Entladeleistung beschreibt dagegen, wie schnell diese Energiemenge ein- oder ausgespeichert werden kann.

Für die maximale Beladeleistung gilt:

.. math::

   P_\mathrm{ein,max} = r_\mathrm{ein} \cdot Q_\mathrm{Speicher}

und entsprechend für die maximale Entladeleistung:

.. math::

   P_\mathrm{aus,max} = r_\mathrm{aus} \cdot Q_\mathrm{Speicher}

Bei der im OWP-Tool verwendeten stündlichen Zeitauflösung kann das Verhältnis von Leistung zu Kapazität als :math:`\mathrm{h^{-1}}` interpretiert werden. Ein Wert von ``0,1`` bedeutet damit, dass bei maximaler Leistung innerhalb von zehn Stunden eine Energiemenge entsprechend der gesamten Speicherkapazität ein- beziehungsweise ausgespeichert werden könnte.

.. important::

   Ein großer Speicher ist nicht automatisch leistungsstark. Wird beispielsweise eine hohe Speicherkapazität mit einem kleinen Verhältnis von Be- oder Entladeleistung kombiniert, kann viel Energie gespeichert werden, diese Energie jedoch nur langsam aufgenommen oder abgegeben werden.

Relativen Wärmeverlust verstehen
--------------------------------

Der **Relative Oberflächenwärmeverlust** wird von der Simulation pro Zeitschritt auf den jeweils vorhandenen Speicherinhalt angewendet. Vereinfacht gilt für den Verlust eines Zeitschritts:

.. math::

   Q_\mathrm{Verlust,t} = \lambda \cdot Q_\mathrm{Speicherinhalt,t}

Dabei bezeichnet :math:`\lambda` den als Dezimalzahl verwendeten Verlustanteil pro Zeitschritt (d.h. pro Stunde).

Ein eingetragener Wert von ``0,05 %`` entspricht beispielsweise einem Verlustanteil von ``0,0005`` pro Stunde. Ohne Be- oder Entladung verbleiben nach 24 Stunden noch :math:`(1-0{,}0005)^{24}` beziehungsweise rund 98,8 % der zuvor gespeicherten Wärmemenge.

.. important::
   Der Verlust wirkt auf den jeweiligen Speicherinhalt und nicht auf die gesamte installierte Kapazität. Ein halb gefüllter Speicher verliert bei demselben relativen Verlust daher absolut weniger Wärme als ein vollständig gefüllter Speicher.

Initialspeicherstand festlegen
------------------------------

Der **Initialspeicherstand** wird relativ zur installierten beziehungsweise optimierten Speicherkapazität angegeben. Bei einer Speicherkapazität von 100 MWh und einem Initialspeicherstand von 50 % befinden sich zu Beginn 50 MWh im Speicher. Wird die Kapazität optimiert, wird auch die absolute Anfangsenergiemenge erst durch das Optimierungsergebnis bestimmt.

Ausgeglichenen Speicherbetrieb verwenden
----------------------------------------

Ist **Ausgeglichener Speicher über Betrachtungsperiode** aktiviert, muss der Speicher am Ende der Simulation wieder denselben Füllstand wie am Anfang aufweisen.

Für eine Jahressimulation ist diese Einstellung in der Regel sinnvoll, weil verhindert wird, dass ein zu Beginn gefüllter Speicher über das Jahr lediglich entleert wird, ohne die entnommene Energie bis zum Ende wieder auszugleichen. Anfangs gespeicherte Wärme würde sonst die Wärmeversorgung des betrachteten Zeitraums unterstützen, obwohl ihre Erzeugung außerhalb des modellierten Zeitraums liegt - es wäre also kein nachhaltiger Betrieb des simulierten Wärmesystems über mehrere Jahre möglich.

Bei deaktiviertem ausgeglichenem Speicherbetrieb darf der Endfüllstand vom Anfangsfüllstand abweichen. Dies kann sinnvoll sein, wenn bewusst ein nicht zyklischer Zeitraum untersucht wird. In diesem Fall muss der Energieinhalt zu Beginn und am Ende bei der Interpretation ausdrücklich berücksichtigt werden.

.. important::

   Bei einem Vergleich mehrerer Jahresszenarien sollte die Einstellung zum ausgeglichenen Speicherbetrieb zwischen den Szenarien identisch sein. Andernfalls können sich Unterschiede allein daraus ergeben, dass in einem Szenario gespeicherte Anfangsenergie verbraucht werden darf und im anderen nicht.

Ökonomische Parameter
=====================

Die wirtschaftlichen Annahmen werden im selben Anlagenbereich unter **Ökonomische Parameter** hinterlegt. Für Wärmespeicher werden die spezifischen Kosten im Tool auf die Speicherkapazität in MWh bezogen.

.. list-table:: Ökonomische Parameter des Wärmespeichers
   :header-rows: 1
   :widths: 38 62

   * - Parameter im OWP-Tool
     - Bedeutung
   * - **Spezifische Investitionskosten in €/MWh**
     - Investitionskosten je installierter MWh Speicherkapazität.
   * - **Rel. Investitionskostenförderung in %**
     - Relativer Anteil der Investitionskosten, der im Modell durch eine Förderung finanziert wird.
   * - **Variable Betriebskosten in €/MWh**
     - Durchsatzabhängige Betriebskosten. Diese Kosten werden sowohl beim Beladen als auch beim Entladen angesetzt.
   * - **Jährliche fixe Betriebskosten in €/MWh**
     - Jährlich anfallende Kosten je installierter MWh Speicherkapazität.
   * - **Rel. Betriebskostenförderung in %**
     - Relative Minderung der angesetzten variablen und fixen Betriebskosten.

Bei einer Kapazitätsoptimierung wirken die Investitions- und fixen Betriebskosten direkt auf die wirtschaftlich optimale Speichergröße. Variable Betriebskosten beeinflussen zusätzlich, wie häufig der Speicher genutzt wird.

Ergebnisse im Reiter „Speicherstand“ auswerten
==============================================

Wenn mindestens ein Wärmespeicher im System enthalten ist, steht auf der Seite **Simulationsergebnisse** der Reiter **Speicherstand** zur Verfügung. Im Reiter werden für jeden Speicher folgende Informationen angezeigt:

* die installierte beziehungsweise optimierte **Kapazität in MWh**,
* die Summe der Speicherentladung im ausgewählten Zeitraum,
* die Summe der Speicherbeladung im ausgewählten Zeitraum und
* die als **Speicherverluste** ausgewiesene Differenz zwischen gesamter Beladung und gesamter Entladung.

Zusätzlich zeigt ein Liniendiagramm den **Speicherstand in MWh**. Darunter werden Be- und Entladung als zeitabhängige Größen dargestellt. Über **Zeitraum auswählen** kann die Darstellung auf einen Teil des Betrachtungszeitraums eingeschränkt werden. Dies ist besonders hilfreich, um einzelne Speicherzyklen in einer Woche oder einem Monat genauer zu untersuchen.

Speicherverluste im Ergebnis richtig interpretieren
----------------------------------------------------

Die im Reiter **Speicherstand** ausgewiesenen Speicherverluste werden im aktuellen Tool als Differenz zwischen der aufsummierten Beladung und der aufsummierten Entladung des ausgewählten Zeitraums berechnet.

Für einen vollständigen Betrachtungszeitraum mit aktiviertem **Ausgeglichenen Speicher über Betrachtungsperiode** kann diese Differenz als Wärmeverlust des Speichers interpretiert werden, da Anfangs- und Endfüllstand gleich sind.

Wird dagegen nur ein Teilzeitraum ausgewählt, kann sich der Speicherfüllstand zwischen Beginn und Ende des dargestellten Zeitraums verändern. In diesem Fall enthält die Differenz zwischen Be- und Entladung zusätzlich die Änderung des gespeicherten Energieinhalts und entspricht nicht ausschließlich den thermischen Verlusten.

.. note::

   Bei der Analyse einzelner Wochen oder Monate sollte deshalb immer auch der Speicherstand zu Beginn und Ende des ausgewählten Zeitraums betrachtet werden. Eine positive Differenz aus Beladung und Entladung kann in diesem Fall sowohl aus Wärmeverlusten als auch aus einem höheren Endfüllstand resultieren.

Typische Speicherverläufe erkennen
==================================

Aus dem Verlauf von Speicherstand sowie Be- und Entladung kann abgeleitet werden, welche Funktion der Speicher im optimierten System übernimmt.

.. list-table:: Typische Beobachtungen im Speicherbetrieb
   :header-rows: 1
   :widths: 36 64

   * - Beobachtung
     - Mögliche Interpretation
   * - Häufige Be- und Entladung innerhalb weniger Stunden oder Tage
     - Der Speicher wird überwiegend als Kurzzeitspeicher verwendet und gleicht kurzfristige Unterschiede zwischen Erzeugung und Nachfrage aus.
   * - Langsame Änderung des Speicherstands über Wochen oder Monate
     - Der Speicher übernimmt eine längerfristige Verschiebung von Wärme. Ob tatsächlich saisonale Speicherung vorliegt, sollte über den gesamten Jahresverlauf geprüft werden.
   * - Speicher erreicht häufig 100 % Füllstand
     - Die vorhandene Kapazität kann zeitweise vollständig genutzt werden. Bei optimierter Kapazität sollte geprüft werden, ob die Obergrenze der Speichergröße korrekt und notwendig ist.
   * - Speicher erreicht häufig 0 % Füllstand
     - Die gespeicherte Wärme wird regelmäßig vollständig genutzt. Dies ist nicht automatisch problematisch, kann aber auf eine knapp dimensionierte Kapazität oder Leistung hinweisen.
   * - Speicherstand ändert sich kaum
     - Der Speicher bietet unter den gewählten Annahmen möglicherweise nur einen geringen betrieblichen Nutzen oder seine Be- beziehungsweise Entladeleistung ist stark begrenzt.
   * - Starke Beladung bei niedrigen Erzeugungskosten und Entladung bei hohen Erzeugungskosten
     - Der Speicher verschiebt Wärme gezielt zwischen wirtschaftlich unterschiedlich günstigen Zeitpunkten.

Eine Jahresdauerlinie allein ist für die Analyse eines Speichers nur eingeschränkt geeignet, weil die zeitliche Reihenfolge der Stunden verloren geht. Für Speicher ist die chronologische Darstellung besonders wichtig, da der Füllstand eines Zeitschritts vom vorherigen Zustand abhängt.

Speichernutzung quantifizieren
==============================

Neben der grafischen Betrachtung kann die Intensität der Speichernutzung näherungsweise über einen äquivalenten Energieumsatz beschrieben werden. Eine einfache Kennzahl ergibt sich aus der jährlichen Entladung geteilt durch die installierte Speicherkapazität:

.. math::

   N_\mathrm{äquiv} = \frac{Q_\mathrm{Entladung}}{Q_\mathrm{Speicherkapazität}}

Diese Größe entspricht nicht zwingend einer Anzahl tatsächlich vollständig durchlaufener Ladezyklen. Viele Teilzyklen können denselben Energieumsatz verursachen. Sie ist jedoch hilfreich, um die Nutzung unterschiedlich großer Speicher oder verschiedener Szenarien miteinander zu vergleichen.

Beispiel aus dem Tutorial „Erstes Energiesystem“
================================================

Im Tutorial :doc:`/Erste_Schritte/Erstes_Energiesystem` wird ein Wärmespeicher mit einer zulässigen Kapazität zwischen 0 und 100 MWh optimiert. Die Optimierung ergibt eine Speicherkapazität von rund 74,4 MWh.

Für den Speicher werden ein Verhältnis von Beladeleistung zu Kapazität von ``0,1`` und ein gleiches Verhältnis für die Entladung verwendet. Daraus ergibt sich eine maximale Be- und Entladeleistung von rund 7,4 MW. Bei einem Initialspeicherstand von 50 % befinden sich zu Beginn rund 37,2 MWh im Speicher. Da der ausgeglichene Speicherbetrieb aktiviert ist, muss dieser Füllstand zum Ende des Jahres wieder erreicht werden.

Über das Jahr werden rund 5,72 GWh Wärme eingespeichert und etwa 5,65 GWh wieder entnommen. Die Differenz von rund 70 MWh kann für den vollständigen, ausgeglichenen Jahreszeitraum als Speicherverlust interpretiert werden.

Mit rund 5,65 GWh jährlicher Entladung und 74,4 MWh Speicherkapazität ergibt sich ein äquivalenter Entladeumsatz von etwa 76 Speicherkapazitäten pro Jahr. Der Speicher wird damit intensiv genutzt und dient in diesem Szenario vor allem der kurzfristigen beziehungsweise mehrtägigen Verschiebung von Wärme, nicht als saisonaler Speicher.

Die optimierte Kapazität liegt unterhalb der vorgegebenen Obergrenze von 100 MWh. Im Gegensatz zur Wärmepumpe desselben Tutorials wird die Speichergröße damit nicht unmittelbar durch die obere Kapazitätsgrenze begrenzt (siehe :doc:`Optimierungsgrenzen_Sensitivitaeten`).

Typische Fehlinterpretationen
=============================

**„Ein Speicher erzeugt zusätzliche Wärme.“**
   Ein Wärmespeicher verschiebt bereits erzeugte Wärme zwischen verschiedenen Zeitpunkten. Durch die modellierten Wärmeverluste muss über den gesamten Betrachtungszeitraum sogar etwas mehr Wärme eingespeichert als wieder entnommen werden.

**„100 MWh Speicherkapazität bedeuten 100 MW Leistung.“**
   Kapazität und Leistung sind unterschiedliche Größen. Die maximale Be- und Entladeleistung ergibt sich im OWP-Tool erst aus dem jeweiligen Verhältnis von Leistung zu Speicherkapazität.

**„Der Initialspeicherstand ist nicht wichtig für die Rechnung.“**
   Der Anfangsfüllstand enthält eine reale Energiemenge im Modell und kann den Anlagenbetrieb beeinflussen. Insbesondere bei nicht ausgeglichenem Speicherbetrieb muss berücksichtigt werden, woher diese Energie stammt beziehungsweise welcher Endfüllstand verbleibt.

**„Die angezeigten Speicherverluste sind in jedem ausgewählten Zeitraum reine Wärmeverluste.“**
   Bei Teilzeiträumen kann zusätzlich eine Veränderung des gespeicherten Energieinhalts enthalten sein. Eine eindeutige Interpretation als thermischer Verlust ist nur bei gleichem Anfangs- und Endfüllstand möglich.

**„Be- und Entladen können im Modell niemals gleichzeitig auftreten.“**
   Das aktuelle Speichermodell enthält keine separate Sperre, die eine gleichzeitige Be- und Entladung grundsätzlich ausschließt. Unter üblichen positiven Durchsatzkosten ist ein solcher Betrieb meist wirtschaftlich unattraktiv. Bei ungewöhnlichen Preis-, Förder- oder Kostenkonstellationen sollte ein entsprechendes Ergebnis jedoch geprüft werden.

Kurzcheck für Wärmespeicher
===========================

Vor der Interpretation eines optimierten Wärmespeichers sollte geprüft werden:

* Ist die Speicherkapazität fest vorgegeben oder wird sie innerhalb sinnvoller Grenzen optimiert?
* Passen die Verhältnisse von Be- und Entladeleistung zur gewünschten Speicheranwendung?
* Ist der relative Wärmeverlust plausibel?
* Ist der Initialspeicherstand nachvollziehbar gewählt?
* Soll der Speicher über den Betrachtungszeitraum ausgeglichen betrieben werden?
* Liegt die optimierte Kapazität nah an einer vorgegebenen Grenze?
* Wird bei Teilzeiträumen zwischen tatsächlichen Wärmeverlusten und einer Änderung des Speicherfüllstands unterschieden?
* Passt das beobachtete Speicherverhalten zur vorgesehenen Rolle als Kurzzeit-, Mehrtages- oder längerfristiger Speicher?

Durch die gemeinsame Betrachtung dieser Punkte lässt sich beurteilen, ob ein optimierter Speicher nicht nur mathematisch zulässig, sondern auch hinsichtlich seiner Dimensionierung und seines Einsatzes nachvollziehbar ist.
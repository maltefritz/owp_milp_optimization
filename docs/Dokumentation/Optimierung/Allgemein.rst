------------------------
Energiesystemoptimierung
------------------------

Um eine Wärmelast mithilfe verschiedener Versorgungsanlagen zu jeder Zeit aus
Sicht eines wirtschaftlich handelnden Akteurs bestmöglich zu decken, können
Auslegung und Einsatz der verfügbaren Anlagen hinsichtlich der Kosten und
Erlöse optimiert werden. Mithilfe von MILP wird eine Zielfunktion definiert,
deren Ergebnis im Lösungsverfahren minimiert wird. Der Lösungsraum kann über
zusätzliche lineare Nebenbe-dingungen, sogenannte Constraints, beschränkt
werden.

Die Zielfunktion besteht aus den in jedem Zeitschritt :math:`t` auftretenden
variablen Betriebskosten :math:`K_{op,var,a}` aller im System betrachteten
Anlagen :math:`a`, abzüglich möglicher Erlöse :math:`E`. Wenn darüber hinaus
die Kapazitäten einer bestimmten Untermenge von Anlagen :math:`b` zu
dimensionieren sind, werden zusätzlich die fixen Betriebskosten
:math:`K_{op,fix,b}` sowie die Annuitäten der Investitionen :math:`K_{inv,b}`
in der Zielfunktion berücksichtigt, wie in Gleichung :math:`\ref{eq:objective}`
zu erkennen ist.

.. math::
    min \left[ \sum_t \left( \sum_a K_{op,var,a}(t) \right) + \sum_b \left(  K_{op,fix,b} + K_{inv,b} \right) - \sum_t E(t) \right]
    \label{eq:objective}

Nichtsdestotrotz werden die Annuitäten und Fixkosten der nicht zu 
dimensionierenden Anlagen in der nachgelagerten Wirtschaftlichkeitsbetrachtung
berücksichtigt.

Alle Kosten und Erlöse sind abhängige Variablen des Optimierungsproblems und
ergeben sich aus Nebenbedingungen, die in
vollständig abgebildet sind. Bei der Auslegungsoptimierung wird die optimale
Zusammensetzung der im Wärmeversorgungssystem vorkommenden Versorgungsanlagen
ermittelt. Die unabhängigen Variablen im Sinne der Auslegungsoptimierung sind
beispielsweise die minimalen und maximalen Kapazitäten der Versorgungsanlagen.
Demgegenüber sind die unabhängigen Variablen der Einsatzoptimierung die zur
Deckung der Wärmelast nötigen Wärmeströme im Versorgungssystem. Somit werden
bei der kombinierten Auslegungs- und Einsatzoptimierung die verfügbaren
Wärmeströme aller Versorgungsanlagen durch die Limitierung ihrer jeweiligen
Kapazitäten begrenzt.

Die Annuitäten der Investition :math:`K_{inv,b}` sowie die fixen Betriebskosten
:math:`K_{op,fix,b}` sind zeitunabhängig und hängen von der Definition der
berücksichtigten Wärmeerzeugungsanlagen :math:`b` ab und sind in 
Gleichung :math:`\ref{eq:cost_inv}` und :math:`\ref{eq:cost_fix}` abgebildet.

.. math::
    K_{inv,b} = \dot Q_{b} \cdot k_{inv,b} \label{eq:cost_inv}

.. math::
    K_{op,fix,b} = \dot Q_{b} \cdot k_{op,fix,b} \label{eq:cost_fix}

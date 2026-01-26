~~~~~~~~~~~~~~~~~~~
Anwendungsbeispiele
~~~~~~~~~~~~~~~~~~~

Integriertes energetisches Quartierskonzept Steinbergkirche
-----------------------------------------------------------

Auslegung eines Wärmespeichers
------------------------------

Wärme:
   - Wärmelast: Flensburg 2024
   - Skalierung: 500 Haushalte
Netzlänge
   - Netzlänge: 12 km
   - Spez. Investionskosten: 12
   - Spez. Fixkosten: 100
   - Spez. var. Kosten: 0,10
Anlagen
   - 1x BHKW (6 identische)
   - 2x Externe Wärmequelle
   - 1x Solarthermie
   - 2x Wärmespeicher
Parametrisierung
   - BHKW:
      * Leistung: 6*90kW = 0,54 MW
      * Wärmeausbeute: 60% 
      * Stromausbeute: 30%
   - Solarthermie:
      * Kollektorfläche: 3000 m²
      * Kollektorwirkungsgrad: 50%
      * Rel. Investionskostenförderung: 50%
   - Externe Wärmequelle 1
      * Leistung: 3,2 MW
      * Investionskosten: 350.000 €/MW
      * Var. Betriebskosten: 18€/MW
   - Externe Wärmequelle 2
      * Leistung: Optimieren
      * Leistung_min: 0
      * Leistung_max: 2,5 MW
      * Investionskosten: 350.000 €/MW
      * Var. Betriebskosten: 18€/MW
   - Speicher 1 (Pufferspeicher)
      * Kapazität: 145 MWh
      * Verhältnis von Beladeleistung zur Kapazit: 0,15
      * Verhältnis von Entladeleistung zur Kapazit: 0,15
      * Rel. Investionskostenförderung: 30%
   - Speicher 2 (Saisonaler Speicher)
      * Kapazität: Optimieren
      * Leistung_min: 0
      * Leistung_max: 150.000 MWh
      * Verhältnis von Beladeleistung zur Kapazit: 0,15
      * Verhältnis von Entladeleistung zur Kapazit: 0,15
      * Rel. Investionskostenförderung: 40%
      * Investionskosten: 320 €/MWh (Baukosten Speicher: 320.000€)
      * Var. Betriebskosten: 25€/MW
      (Wärmepumpe hinter Speicher: wird in den var. Kosten berücksichtigt:
       COP=7, C_el=28Cent/kWh = 40€/MWh - Rückwärtsrechnen)
      * Ausgeglichen
      * Initialspeicherstand: 50%
Versorgung
   - Elektrizität:
      * konstant
      * 180 €/MWh
      * Bestandteile: 2024
   - Gas
      * konstant
      * Gaspreis: 75 €/MWh
      * CO_2-Preis: 30 €/t CO_2
      * Emissionsfatkor: 0,2012 t CO_2/MWh
Sonstige
   - Defaultwerte

Ergebnisse

Nächster Schritt:
   - Erhöhung der Solarthermiefläche auf 12.500 m²
   - Elektrizitskosten auf 250 €/MWh

Ergebnisse

Nächster Schritt:
   - S-TES var. Speicherkosten: 2,5 €/MWh ohne die Berücksichtigung der WP

Ergebnisse
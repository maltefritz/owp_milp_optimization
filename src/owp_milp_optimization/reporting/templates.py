"""HTML template components for reports."""

def get_report_template():
    """Get the main HTML report template."""
    return """
<div class="container">
    <!-- Header -->
    <div class="header">
        <div class="header-title">{{ title }}</div>
        <div class="header-meta">
            <div class="meta-item">
                <span class="meta-label">Generiert:</span>
                <span>{{ timestamp }}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Solver:</span>
                <span>{{ solver }}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Status:</span>
                <span>{{ status }}</span>
            </div>
        </div>
    </div>

    <!-- Key Performance Indicators -->
    <div class="section">
        <div class="section-title">Kennzahlen</div>
        <div class="kpi-grid">
            {{ kpi_cards }}
        </div>
    </div>

    <!-- System Configuration -->
    <div class="section">
        <div class="section-title">Systemkonfiguration</div>

        <div class="subsection-title">Optimierte Anlagenkapazitäten</div>
        <div class="grid-2">
            <div class="image-container">
                {{ topology_image }}
            </div>
            <div>
                {{ capacities_table }}
            </div>
        </div>

        <div class="subsection-title">Eingabeparameter</div>
        {{ parameters_table }}
    </div>

    <!-- Economic Analysis -->
    <div class="section">
        <div class="section-title">Wirtschaftliche Analyse</div>
        
        <div class="subsection-title">Kostenaufschlüsselung</div>
        {{ costs_table }}

        <div class="subsection-title">Wärmeproduktion nach Anlage</div>
        <div class="chart-container">
            <div id="heat-production-chart"></div>
        </div>
    </div>

    <!-- Ecological Analysis -->
    <div class="section">
        <div class="section-title">Ökologische Analyse</div>
        
        <div class="kpi-grid">
            {{ emission_cards }}
        </div>

    <!-- Results Charts -->
    {{ chart_sections }}

    <!-- Footer -->
    <div class="footer">
        <p>Dieser Bericht wurde automatisch von der OWP MILP Optimierungssoftware generiert.</p>
    </div>
</div>

<!-- Chart rendering scripts -->
<script>
{{ chart_specs }}
</script>
</body>
</html>
"""


def get_kpi_card_template():
    """Template for KPI cards."""
    return """<div class="kpi-card">
    <div class="kpi-label">{{ label }}</div>
    <div class="kpi-value">{{ value }}</div>
</div>"""


def get_chart_section_template():
    """Template for chart sections."""
    return """<div class="section">
    <div class="subsection-title">{{ title }}</div>
    <div class="chart-container">
        <div id="{{ chart_id }}"></div>
    </div>
</div>"""

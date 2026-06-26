"""HTML template components for reports."""

from owp_milp_optimization.helpers import txt

def get_report_template():
    """Get the main HTML report template."""
    return f"""
<div class="container">
    <!-- Header -->
    <div class="header">
        <div class="header-title">{{{{ title }}}}</div>
        <div class="header-meta">
            <div class="meta-item">
                <span class="meta-label">{txt('report.template.generated_label')}</span>
                <span>{{{{ timestamp }}}}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">{txt('report.template.solver_label')}</span>
                <span>{{{{ solver }}}}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">{txt('report.template.status_label')}</span>
                <span>{{{{ status }}}}</span>
            </div>
        </div>
    </div>

    <!-- Key Performance Indicators -->
    <div class="section">
        <div class="section-title">{txt('report.template.kpis')}</div>
        <div class="kpi-grid">
            {{{{ kpi_cards }}}}
        </div>
    </div>

    <!-- System Configuration -->
    <div class="section">
        <div class="section-title">{txt('report.template.system_configuration')}</div>

        <div class="subsection-title">{txt('report.template.optimized_capacities')}</div>
        <div class="grid-2">
            <div class="image-container">
                {{{{ topology_image }}}}
            </div>
            <div>
                {{{{ capacities_table }}}}
            </div>
        </div>

    </div>

    <!-- Economic Analysis -->
    <div class="section">
        <div class="section-title">{txt('report.template.economic_indicators')}</div>
        
        <div class="subsection-title">{txt('report.template.cost_breakdown')}</div>
        {{{{ costs_table }}}}

        <div class="subsection-title">{txt('report.template.heat_production_by_unit')}</div>
        <div class="chart-container">
            <div id="heat-production-chart"></div>
        </div>
    </div>

    <!-- Ecological Analysis -->
    <div class="section">
        <div class="section-title">{txt('report.template.ecological_indicators')}</div>

        <div class="kpi-grid">
            {{{{ emission_cards }}}}
        </div>
    </div>

    <!-- Results Charts -->
    {{{{ chart_sections }}}}

    <!-- Input parameter -->
    <div class="section">
        <div class="section-title">{txt('report.template.input')}</div>

        <div class="subsection-title">{txt('report.template.timeseries')}</div>
        {{{{ overview_table }}}}

        <div class="subsection-title">{txt('report.template.parameters')}</div>
        {{{{ parameters_table }}}}
    </div>

    <!-- Footer -->
    <div class="footer">
        <p>{txt('report.template.footer')}</p>
    </div>
</div>

<!-- Chart rendering scripts -->
<script>
{{{{ chart_specs }}}}
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

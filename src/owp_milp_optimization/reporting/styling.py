"""CSS styling for HTML reports."""

REPORT_CSS = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Optimierungsbericht</title>
    <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            background: white;
        }

        /* Header */
        .header {
            border-bottom: 3px solid #00395B;
            margin-bottom: 40px;
            padding-bottom: 30px;
        }

        .header-title {
            font-size: 32px;
            font-weight: bold;
            color: #00395B;
            margin-bottom: 10px;
        }

        .header-meta {
            display: flex;
            gap: 40px;
            font-size: 14px;
            color: #666;
            flex-wrap: wrap;
        }

        .meta-item {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .meta-label {
            font-weight: 600;
            color: #333;
        }

        /* Sections */
        .section {
            margin-bottom: 40px;
            page-break-inside: avoid;
        }

        .section-title {
            font-size: 24px;
            font-weight: bold;
            color: #00395B;
            border-left: 4px solid #B54036;
            padding-left: 15px;
            margin-bottom: 20px;
            margin-top: 30px;
        }

        .section-title:first-of-type {
            margin-top: 0;
        }

        .subsection-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-top: 20px;
            margin-bottom: 15px;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }

        th {
            background: #00395B;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }

        tr:hover {
            background: #f9f9f9;
        }

        tr:last-child td {
            border-bottom: none;
        }

        /* KPI Cards */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .kpi-card {
            background: linear-gradient(135deg, #00395B 0%, #003d66 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            page-break-inside: avoid;
        }

        .kpi-label {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 8px;
        }

        .kpi-value {
            font-size: 28px;
            font-weight: bold;
            word-break: break-word;
        }

        /* Charts */
        .chart-container {
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
            page-break-inside: avoid;
        }

        .chart-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }

        /* Images */
        .image-container {
            margin: 20px 0;
            text-align: center;
        }

        .image-container img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .image-caption {
            font-size: 12px;
            color: #666;
            margin-top: 8px;
            font-style: italic;
        }

        /* Grid layouts */
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 20px 0;
        }

        @media (max-width: 768px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
            
            .header-title {
                font-size: 24px;
            }
            
            .section-title {
                font-size: 20px;
            }
        }

        /* Footer */
        .footer {
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #999;
            text-align: center;
        }

        /* Print styles */
        @media print {
            body {
                background: white;
            }
            
            .container {
                padding: 20px;
                max-width: 100%;
            }
            
            .section {
                page-break-inside: avoid;
            }
            
            a {
                text-decoration: none;
                color: #00395B;
            }
        }

        /* Vega-Lite chart styling */
        .vega-embed {
            background: white;
            border-radius: 4px;
            overflow: hidden;
        }

        /* Utility */
        .text-right {
            text-align: right;
        }

        .text-center {
            text-align: center;
        }

        .mt-30 {
            margin-top: 30px;
        }

        .mb-20 {
            margin-bottom: 20px;
        }

        .highlight {
            background: #fffacd;
            padding: 2px 6px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
"""

from datetime import datetime
from typing import Dict
import json

class ReportGenerator:
    """
    Generates comprehensive HTML reports with interactive charts and detailed tables.
    """
    
    @staticmethod
    def _generate_detailed_tables(results: Dict) -> str:
        """Generates detailed HTML tables for each validation segment."""
        sections = []
        
        segment_titles = {
            "by_date": "Timeline Validation Matrix",
            "by_campaign": "Campaign Performance Integrity",
            "by_platform": "Platform Distribution Integrity",
            "by_placement": "Placement-Level Granularity Check",
            "by_gender": "Demographic: Gender Matching",
            "by_age": "Demographic: Age Group Analysis",
            "by_camp_date": "Deep Dive: Campaign + Date Reconciliation"
        }
        
        for key, rows in results.items():
            if key == "overall" or not rows:
                continue
            
            title = segment_titles.get(key, key.replace("_", " ").title())
            
            # Determine join key column
            sample = rows[0]
            join_key = [k for k in sample.keys() if '_csv' not in k and '_fab' not in k and k != 'perfect_match'][0]
            
            # Check if reach, purchases, and conversion_value exist in data
            has_reach = 'reach_csv' in sample or 'reach_fab' in sample
            has_purchases = 'purchases_csv' in sample or 'purchases_fab' in sample
            has_conv_value = 'conversion_value_csv' in sample or 'conversion_value_fab' in sample
            
            # Build header
            reach_header = '<th>Reach (CSV/Gold)</th>' if has_reach else ''
            purchases_header = '<th>Purchases (CSV/Gold)</th>' if has_purchases else ''
            conv_value_header = '<th>Conv Value (CSV/Gold)</th>' if has_conv_value else ''
            colspan = 5 + (1 if has_reach else 0) + (1 if has_purchases else 0) + (1 if has_conv_value else 0)
            
            table_html = f'''
            <div class="section">
                <h2>{title}</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <tr>
                            <th>{join_key.replace("_", " ").title()}</th>
                            <th>Cost (CSV/Gold)</th>
                            <th>Impr (CSV/Gold)</th>
                            <th>Clicks (CSV/Gold)</th>
                            {reach_header}
                            {purchases_header}
                            {conv_value_header}
                            <th>Status</th>
                        </tr>
            '''
            
            # Limit to top 50 rows for report size
            for row in rows[:50]:
                status = "PASS" if row.get('perfect_match') else "FAIL"
                status_class = "pass" if status == "PASS" else "fail"
                
                # Build reach, purchases, and conversion_value cells
                reach_cell = f"<td>{row.get('reach_csv', 0):,.0f} / {row.get('reach_fab', 0):,.0f}</td>" if has_reach else ''
                purchases_cell = f"<td>{row.get('purchases_csv', 0):,.0f} / {row.get('purchases_fab', 0):,.0f}</td>" if has_purchases else ''
                conv_value_cell = f"<td>{row.get('conversion_value_csv', 0):,.2f} / {row.get('conversion_value_fab', 0):,.2f}</td>" if has_conv_value else ''
                
                table_html += f'''
                        <tr>
                            <td>{row.get(join_key)}</td>
                            <td>{row.get('cost_csv', 0):,.2f} / {row.get('cost_fab', 0):,.2f}</td>
                            <td>{row.get('impressions_csv', 0):,.0f} / {row.get('impressions_fab', 0):,.0f}</td>
                            <td>{row.get('clicks_csv', 0):,.0f} / {row.get('clicks_fab', 0):,.0f}</td>
                            {reach_cell}
                            {purchases_cell}
                            {conv_value_cell}
                            <td class="{status_class}">{status}</td>
                        </tr>
                '''
            
            if len(rows) > 50:
                table_html += f'<tr><td colspan="{colspan}" style="text-align: center; font-style: italic; color: #94a3b8;">... and {len(rows)-50} more rows</td></tr>'
                
            table_html += '''
                    </table>
                </div>
            </div>
            '''
            sections.append(table_html)
            
        return "\n".join(sections)

    @staticmethod
    def generate_html_report(validation_results: Dict, summary: Dict, threshold: float = 3.0) -> str:
        """
        Generate a complete HTML report with all validation data.
        
        Args:
            validation_results: Full validation results dict
            summary: Summary statistics dict
            threshold: Validation threshold percentage
            
        Returns:
            HTML string ready to be saved as a file
        """
        
        # Prepare chart data
        overall_match_rate = summary.get('overall_match_rate', 0)
        total_segments = summary.get('total_segments', 0)
        passing_segments = summary.get('passing_segments', 0)
        
        # Summary table data
        details = summary.get('details', [])
        segment_labels = [d['type'].replace('_', ' ').title() for d in details]
        segment_percentages = [d['percent'] for d in details]
        
        # Color coding based on match rates
        segment_colors = [
            'rgba(16, 185, 129, 0.7)' if p > 95 else 
            'rgba(251, 191, 36, 0.7)' if p > 80 else 
            'rgba(239, 68, 68, 0.7)' 
            for p in segment_percentages
        ]
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NYX Data Validation Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: radial-gradient(circle at 20% 50%, rgba(102, 126, 234, 0.15) 0%, transparent 50%),
                        radial-gradient(circle at 80% 80%, rgba(245, 87, 108, 0.1) 0%, transparent 50%),
                        #0a0e27;
            padding: 40px 20px;
            min-height: 100vh;
            color: #f8fafc;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 60px 40px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
        }}

        .header h1 {{
            font-size: 3rem;
            font-weight: 900;
            margin-bottom: 15px;
            text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);
            letter-spacing: -0.05em;
        }}

        .header p {{
            font-size: 1.2rem;
            opacity: 0.95;
            font-weight: 600;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 24px;
            padding: 40px;
            background: rgba(15, 23, 42, 0.3);
        }}

        .metric-card {{
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
            backdrop-filter: blur(20px);
            padding: 30px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-5px);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.4);
        }}

        .metric-card h3 {{
            font-size: 0.75rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #94a3b8;
            margin-bottom: 15px;
        }}

        .metric-card .value {{
            font-size: 3rem;
            font-weight: 900;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }}

        .metric-card .desc {{
            font-size: 0.875rem;
            color: #94a3b8;
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(550px, 1fr));
            gap: 30px;
            padding: 40px;
        }}

        .chart-container {{
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
            backdrop-filter: blur(20px);
            padding: 30px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}

        .chart-container h3 {{
            font-size: 1.25rem;
            font-weight: 900;
            margin-bottom: 25px;
            color: #f8fafc;
        }}

        .chart-wrapper {{
            position: relative;
            height: 350px;
        }}

.content {{
            padding: 40px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 18px;
            text-align: left;
            font-weight: 900;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 1px;
        }}

        td {{
            padding: 16px 18px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #f8fafc;
        }}

        tr:hover {{
            background-color: rgba(255, 255, 255, 0.05);
        }}

        .pass {{
            color: #10b981;
            font-weight: 700;
        }}

        .fail {{
            color: #ef4444;
            font-weight: 700;
        }}

        .footer {{
            background: rgba(15, 23, 42, 0.6);
            color: #94a3b8;
            text-align: center;
            padding: 30px;
            font-size: 0.875rem;
        }}

        .section {{
            margin-bottom: 50px;
        }}

        .section h2 {{
            font-size: 2rem;
            font-weight: 900;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 25px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔮 NYX DATA VALIDATION REPORT</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Threshold: ±{threshold}%</p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Overall Match Rate</h3>
                <div class="value">{overall_match_rate:.1f}%</div>
                <div class="desc">Validation health score</div>
            </div>
            <div class="metric-card">
                <h3>Segments Passing</h3>
                <div class="value">{passing_segments}/{total_segments}</div>
                <div class="desc">Within threshold</div>
            </div>
            <div class="metric-card">
                <h3>Threshold</h3>
                <div class="value">±{threshold}%</div>
                <div class="desc">Acceptance margin</div>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="chart-container">
                <h3>📊 Segment Performance Distribution</h3>
                <div class="chart-wrapper">
                    <canvas id="segmentChart"></canvas>
                </div>
            </div>

            <div class="chart-container">
                <h3>🎯 Validation Health Radar</h3>
                <div class="chart-wrapper">
                    <canvas id="radarChart"></canvas>
                </div>
            </div>
        </div>

        <div class="content">
            <div class="section">
                <h2>Validation Summary</h2>
                <table>
                    <tr>
                        <th>Segment Type</th>
                        <th>Total</th>
                        <th>Matches</th>
                        <th>Match %</th>
                    </tr>
                    {"".join([f'''
                    <tr>
                        <td>{d["type"].replace("_", " ").title()}</td>
                        <td>{d["total"]}</td>
                        <td>{d["matches"]}</td>
                        <td class="{'pass' if d['percent'] > 95 else 'fail'}">{d["percent"]:.2f}%</td>
                    </tr>
                    ''' for d in details])}
                </table>
            </div>

            <div class="section">
                <h2>Overall Metrics Comparison</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Growth (CSV)</th>
                        <th>Gold (Fabric)</th>
                        <th>Difference</th>
                        <th>Diff %</th>
                        <th>Status</th>
                    </tr>
                    {"".join([f'''
                    <tr>
                        <td style="font-weight: 700; text-transform: capitalize;">{m["metric"]}</td>
                        <td>{m["csv"]:,.2f}</td>
                        <td>{m["fabric"]:,.2f}</td>
                        <td>{m["diff"]:,.2f}</td>
                        <td>{m["diff_pct"]:.2f}%</td>
                        <td class="{'pass' if m['match'] else 'fail'}">{'PASS' if m['match'] else 'FAIL'}</td>
                    </tr>
                    ''' for m in validation_results.get("overall", [])])}
                </table>
            </div>

            {ReportGenerator._generate_detailed_tables(validation_results)}
        </div>

        <div class="footer">
            <p><strong>NYX Data Validator</strong> | AI-Powered Validation Platform</p>
            <p>Overall Match Rate: {overall_match_rate:.1f}% | Threshold: ±{threshold}%</p>
        </div>
    </div>

    <script>
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.color = '#94a3b8';

        const segmentCtx = document.getElementById('segmentChart').getContext('2d');
        new Chart(segmentCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(segment_labels)},
                datasets: [{{
                    label: 'Match Rate (%)',
                    data: {json.dumps(segment_percentages)},
                    backgroundColor: {json.dumps(segment_colors)},
                    borderColor: {json.dumps([c.replace('0.7', '1') for c in segment_colors])},
                    borderWidth: 3,
                    borderRadius: 12
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: 'rgba(10, 14, 39, 0.95)',
                        padding: 16,
                        titleFont: {{ size: 14, weight: 'bold' }},
                        bodyFont: {{ size: 13 }},
                        borderColor: 'rgba(102, 126, 234, 0.5)',
                        borderWidth: 2,
                        cornerRadius: 12
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        grid: {{ color: 'rgba(255,255,255,0.05)' }},
                        ticks: {{ 
                            color: '#94a3b8',
                            font: {{ weight: 600 }}
                        }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ 
                            color: '#94a3b8',
                            font: {{ weight: 600 }}
                        }}
                    }}
                }}
            }}
        }});

        const radarCtx = document.getElementById('radarChart').getContext('2d');
        new Chart(radarCtx, {{
            type: 'radar',
            data: {{
                labels: {json.dumps(segment_labels)},
                datasets: [{{
                    label: 'Validation Score',
                    data: {json.dumps(segment_percentages)},
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: '#667eea',
                    borderWidth: 4,
                    pointBackgroundColor: '#667eea',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 3,
                    pointRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: 'rgba(10, 14, 39, 0.95)',
                        padding: 16,
                        borderColor: 'rgba(102, 126, 234, 0.5)',
                        borderWidth: 2,
                        cornerRadius: 12
                    }}
                }},
                scales: {{
                    r: {{
                        min: 0,
                        max: 100,
                        grid: {{ color: 'rgba(255,255,255,0.08)' }},
                        angleLines: {{ color: 'rgba(255,255,255,0.08)' }},
                        ticks: {{
                            color: '#94a3b8',
                            backdropColor: 'transparent',
                            font: {{ weight: 600 }}
                        }},
                        pointLabels: {{
                            color: '#f8fafc',
                            font: {{ weight: 700, size: 12 }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
        
        return html_content

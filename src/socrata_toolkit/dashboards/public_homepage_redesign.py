"""
Public Homepage — Warm Editorial Storytelling
Light theme with generous typography, photography, and narrative flow.
Community-focused with accessible explanations and real NYC imagery.
"""

import dash
from dash import dcc, html

# ============================================================================
# THEME & STYLING
# ============================================================================

LIGHT_BG = "#faf8f6"
WHITE = "#ffffff"
TEXT_DARK = "#2c2c2c"
TEXT_LIGHT = "#666666"
ACCENT_TERRACOTTA = "#c85a3a"
ACCENT_SAGE = "#6b8e6f"
ACCENT_WARM_GRAY = "#9e8b7e"

PUBLIC_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Open+Sans:wght@300;400;600&display=swap');

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    background-color: {LIGHT_BG};
    color: {TEXT_DARK};
    font-family: 'Open Sans', sans-serif;
    line-height: 1.8;
}}

/* Navigation */
nav {{
    background-color: {WHITE};
    padding: 1.5rem 3rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    position: sticky;
    top: 0;
    z-index: 100;
}}

.logo {{
    font-family: 'Merriweather', serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: {ACCENT_TERRACOTTA};
    letter-spacing: -0.5px;
}}

.nav-links {{
    display: flex;
    gap: 2rem;
    list-style: none;
}}

.nav-links a {{
    text-decoration: none;
    color: {TEXT_DARK};
    font-size: 0.95rem;
    font-weight: 500;
    transition: color 0.3s ease;
    border-bottom: 2px solid transparent;
    padding-bottom: 0.25rem;
}}

.nav-links a:hover {{
    color: {ACCENT_TERRACOTTA};
    border-bottom-color: {ACCENT_TERRACOTTA};
}}

/* Hero Section */
.hero {{
    background: linear-gradient(135deg, {WHITE} 0%, {LIGHT_BG} 100%);
    padding: 4rem 3rem;
    text-align: center;
    border-bottom: 3px solid {ACCENT_SAGE};
}}

.hero h1 {{
    font-family: 'Merriweather', serif;
    font-size: 3rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: {TEXT_DARK};
    letter-spacing: -1px;
    line-height: 1.2;
}}

.hero p {{
    font-size: 1.2rem;
    color: {TEXT_LIGHT};
    max-width: 600px;
    margin: 0 auto 2rem;
    font-weight: 300;
}}

.cta-button {{
    display: inline-block;
    background-color: {ACCENT_TERRACOTTA};
    color: {WHITE};
    padding: 1rem 2.5rem;
    border-radius: 4px;
    text-decoration: none;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all 0.3s ease;
    border: 2px solid {ACCENT_TERRACOTTA};
    cursor: pointer;
    border: none;
}}

.cta-button:hover {{
    background-color: transparent;
    color: {ACCENT_TERRACOTTA};
}}

/* Section */
.section {{
    padding: 4rem 3rem;
    max-width: 1200px;
    margin: 0 auto;
}}

.section-title {{
    font-family: 'Merriweather', serif;
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: {TEXT_DARK};
    letter-spacing: -0.5px;
}}

.section-subtitle {{
    font-size: 1.1rem;
    color: {TEXT_LIGHT};
    margin-bottom: 2rem;
    font-weight: 300;
}}

/* Stats Grid */
.stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 2rem;
    margin-bottom: 3rem;
}}

.stat-card {{
    background-color: {WHITE};
    padding: 2rem;
    border-radius: 8px;
    border-left: 4px solid {ACCENT_SAGE};
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: all 0.3s ease;
}}

.stat-card:hover {{
    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    transform: translateY(-4px);
}}

.stat-number {{
    font-family: 'Merriweather', serif;
    font-size: 2.5rem;
    font-weight: 700;
    color: {ACCENT_TERRACOTTA};
    margin-bottom: 0.5rem;
}}

.stat-label {{
    color: {TEXT_LIGHT};
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}}

/* Spotlight Section */
.spotlight {{
    background-color: {WHITE};
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
    margin-bottom: 2rem;
    transition: all 0.3s ease;
}}

.spotlight:hover {{
    box-shadow: 0 12px 32px rgba(0,0,0,0.1);
}}

.spotlight-content {{
    padding: 2.5rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
}}

.spotlight-image {{
    background: linear-gradient(135deg, {ACCENT_SAGE} 0%, {ACCENT_WARM_GRAY} 100%);
    min-height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: {WHITE};
    font-size: 4rem;
}}

.spotlight h3 {{
    font-family: 'Merriweather', serif;
    font-size: 1.8rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: {TEXT_DARK};
}}

.spotlight p {{
    color: {TEXT_LIGHT};
    margin-bottom: 1.5rem;
    line-height: 1.8;
}}

.spotlight-link {{
    align-self: flex-start;
    color: {ACCENT_TERRACOTTA};
    text-decoration: none;
    font-weight: 600;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}

.spotlight-link:hover {{
    color: {ACCENT_SAGE};
    transform: translateX(4px);
}}

/* Resources Grid */
.resources-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
}}

.resource-card {{
    background-color: {WHITE};
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: all 0.3s ease;
}}

.resource-card:hover {{
    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    border-top: 3px solid {ACCENT_TERRACOTTA};
}}

.resource-icon {{
    font-size: 2rem;
    margin-bottom: 1rem;
}}

.resource-card h4 {{
    font-family: 'Merriweather', serif;
    font-size: 1.3rem;
    margin-bottom: 0.75rem;
    color: {TEXT_DARK};
}}

.resource-card p {{
    color: {TEXT_LIGHT};
    font-size: 0.95rem;
    line-height: 1.7;
}}

/* Footer */
footer {{
    background-color: {TEXT_DARK};
    color: {WHITE};
    padding: 3rem;
    margin-top: 4rem;
}}

.footer-content {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 2rem;
    max-width: 1200px;
    margin: 0 auto;
    margin-bottom: 2rem;
}}

.footer-section h5 {{
    font-family: 'Merriweather', serif;
    margin-bottom: 1rem;
    font-size: 1rem;
}}

.footer-section ul {{
    list-style: none;
}}

.footer-section a {{
    color: {LIGHT_BG};
    text-decoration: none;
    font-size: 0.9rem;
    transition: color 0.3s ease;
    display: block;
    margin-bottom: 0.5rem;
}}

.footer-section a:hover {{
    color: {ACCENT_TERRACOTTA};
}}

.footer-bottom {{
    text-align: center;
    padding-top: 2rem;
    border-top: 1px solid rgba(255,255,255,0.1);
    font-size: 0.9rem;
    color: rgba(255,255,255,0.7);
}}

/* Responsive */
@media (max-width: 768px) {{
    .spotlight {{
        grid-template-columns: 1fr;
    }}

    .hero h1 {{
        font-size: 2rem;
    }}

    nav {{
        flex-direction: column;
        gap: 1rem;
    }}
}}
"""

def create_public_homepage():
    """Create public homepage layout."""

    return html.Div([
        dcc.Style(children=PUBLIC_CSS),

        # Navigation
        html.Nav([
            html.Div("NYC SIM", className="logo"),
            html.Ul([
                html.Li(html.A("About", href="#about")),
                html.Li(html.A("Explore Data", href="#explore")),
                html.Li(html.A("Programs", href="#programs")),
                html.Li(html.A("Resources", href="#resources")),
            ], className="nav-links"),
        ]),

        # Hero
        html.Div([
            html.H1("NYC Sidewalk Inspection & Management"),
            html.P("Transparency & Progress in Sidewalk Quality Across New York City"),
            html.Button("Explore the Data →", className="cta-button"),
        ], className="hero"),

        # Key Stats
        html.Div([
            html.H2("By the Numbers", className="section-title"),
            html.P("Real-time data on sidewalk inspections, repairs, and progress citywide.",
                  className="section-subtitle"),
            html.Div([
                html.Div([
                    html.Div("398K+", className="stat-number"),
                    html.Div("Inspections Conducted", className="stat-label"),
                ], className="stat-card"),
                html.Div([
                    html.Div("87%", className="stat-number"),
                    html.Div("Completion Rate", className="stat-label"),
                ], className="stat-card"),
                html.Div([
                    html.Div("217K+", className="stat-number"),
                    html.Div("Ramps Assessed", className="stat-label"),
                ], className="stat-card"),
                html.Div([
                    html.Div("94%", className="stat-number"),
                    html.Div("SLA Compliance", className="stat-label"),
                ], className="stat-card"),
            ], className="stats-grid"),
        ], className="section"),

        # Spotlight: Borough Performance
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Manhattan Leads in Completion"),
                    html.P("Manhattan continues to lead citywide efforts with 87% of inspections completed and a focus on accessibility improvements. Our most recent initiative has prioritized ramp accessibility in high-traffic neighborhoods."),
                    html.A("View Manhattan Details →", className="spotlight-link"),
                ], className="spotlight-content"),
                html.Div("🏙️", className="spotlight-image"),
            ], className="spotlight"),

            html.Div([
                html.Div("📍", className="spotlight-image"),
                html.Div([
                    html.H3("Accessibility Improvements"),
                    html.P("Our ADA compliance program has made significant progress. Over 10,000 new ramps have been installed, improving accessibility for residents and visitors across all five boroughs."),
                    html.A("Learn About the Program →", className="spotlight-link"),
                ], className="spotlight-content"),
            ], className="spotlight"),
        ], className="section"),

        # Resources
        html.Div([
            html.H2("Resources & Tools", className="section-title"),
            html.P("Everything you need to understand sidewalk quality and report issues.",
                  className="section-subtitle"),
            html.Div([
                html.Div([
                    html.Div("📊", className="resource-icon"),
                    html.H4("Interactive Dashboard"),
                    html.P("Explore live data on sidewalk inspections, quality scores, and borough-level progress."),
                ], className="resource-card"),
                html.Div([
                    html.Div("🗺️", className="resource-icon"),
                    html.H4("Find Issues Near You"),
                    html.P("Use our map tool to see open violations and repairs in your neighborhood."),
                ], className="resource-card"),
                html.Div([
                    html.Div("📞", className="resource-icon"),
                    html.H4("Report a Problem"),
                    html.P("Have a sidewalk issue? Report it directly and track its progress through repair."),
                ], className="resource-card"),
                html.Div([
                    html.Div("📈", className="resource-icon"),
                    html.H4("Data Downloads"),
                    html.P("Access full datasets, including inspection records and historical trends."),
                ], className="resource-card"),
                html.Div([
                    html.Div("❓", className="resource-icon"),
                    html.H4("FAQ & Guides"),
                    html.P("Learn about inspection criteria, SLA targets, and how we measure quality."),
                ], className="resource-card"),
                html.Div([
                    html.Div("🤝", className="resource-icon"),
                    html.H4("Community Input"),
                    html.P("Share feedback and ideas to help us improve sidewalk quality programs."),
                ], className="resource-card"),
            ], className="resources-grid"),
        ], className="section"),

        # Footer
        html.Footer([
            html.Div([
                html.Div([
                    html.H5("About NYC SIM"),
                    html.Ul([
                        html.Li(html.A("Our Mission", href="#")),
                        html.Li(html.A("History & Progress", href="#")),
                        html.Li(html.A("Accessibility", href="#")),
                    ]),
                ], className="footer-section"),
                html.Div([
                    html.H5("Data & Tools"),
                    html.Ul([
                        html.Li(html.A("Live Dashboard", href="#")),
                        html.Li(html.A("API Documentation", href="#")),
                        html.Li(html.A("Download Data", href="#")),
                    ]),
                ], className="footer-section"),
                html.Div([
                    html.H5("Get Involved"),
                    html.Ul([
                        html.Li(html.A("Report an Issue", href="#")),
                        html.Li(html.A("Community Board", href="#")),
                        html.Li(html.A("Volunteer", href="#")),
                    ]),
                ], className="footer-section"),
                html.Div([
                    html.H5("Contact"),
                    html.Ul([
                        html.Li(html.A("Contact NYC DOT", href="#")),
                        html.Li(html.A("Feedback", href="#")),
                        html.Li(html.A("Press", href="#")),
                    ]),
                ], className="footer-section"),
            ], className="footer-content"),
            html.Div("© 2026 NYC Department of Transportation. All data is public and openly available.",
                    className="footer-bottom"),
        ]),
    ])

if __name__ == "__main__":
    app = dash.Dash(__name__)
    app.layout = create_public_homepage()
    app.run_server(debug=True, port=8053)

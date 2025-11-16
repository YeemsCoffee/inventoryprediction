"""
Interactive What-If Scenario Dashboard
Web interface for running and comparing business scenarios.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.app import CustomerTrendApp
from src.models.scenario_simulator import ScenarioSimulator, ScenarioConfig


def create_scenario_dashboard(data_path: str = None):
    """
    Create interactive what-if scenario dashboard.

    Args:
        data_path: Path to sales data CSV (optional)

    Returns:
        Dash app instance
    """
    # Load data
    app_data = CustomerTrendApp()

    if data_path and os.path.exists(data_path):
        app_data.load_data(data_path)
        data_source = "Square API Data"
    else:
        app_data.create_sample_data(n_customers=200, n_transactions=10000)
        data_source = "Sample Data"

    # Initialize simulator
    simulator = ScenarioSimulator(app_data.processed_data)
    simulator.create_baseline_forecast(days_ahead=30)

    # Get product list
    products = sorted(app_data.processed_data['product'].unique())

    # Create Dash app
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )

    # Layout
    app.layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("🎯 What-If Scenario Simulator", className="text-primary"),
                html.P(f"Data Source: {data_source}", className="text-muted"),
                html.Hr()
            ])
        ]),

        dbc.Row([
            # Scenario Builder Panel
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("📝 Build Your Scenario")),
                    dbc.CardBody([
                        # Scenario Name
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Scenario Name"),
                                dbc.Input(
                                    id="scenario-name",
                                    placeholder="e.g., Black Friday Sale",
                                    value="My Scenario"
                                )
                            ])
                        ], className="mb-3"),

                        # Scenario Type
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Scenario Type"),
                                dcc.Dropdown(
                                    id="scenario-type",
                                    options=[
                                        {"label": "🎁 Promotion/Discount", "value": "promotion"},
                                        {"label": "💰 Pricing Change", "value": "pricing"},
                                        {"label": "📈 Demand Shift", "value": "demand"}
                                    ],
                                    value="promotion"
                                )
                            ])
                        ], className="mb-3"),

                        # Promotion Settings
                        html.Div(id="promotion-settings", children=[
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Discount %"),
                                    dbc.Input(
                                        id="discount-pct",
                                        type="number",
                                        value=20,
                                        min=0,
                                        max=100
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Label("Duration (days)"),
                                    dbc.Input(
                                        id="duration-days",
                                        type="number",
                                        value=7,
                                        min=1,
                                        max=30
                                    )
                                ], width=6)
                            ], className="mb-3"),
                        ]),

                        # Pricing Settings
                        html.Div(id="pricing-settings", style={"display": "none"}, children=[
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Price Change %"),
                                    dbc.Input(
                                        id="price-change-pct",
                                        type="number",
                                        value=10,
                                        min=-50,
                                        max=50
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Label("Price Elasticity"),
                                    dbc.Input(
                                        id="price-elasticity",
                                        type="number",
                                        value=-1.5,
                                        step=0.1
                                    )
                                ], width=6)
                            ], className="mb-3"),
                        ]),

                        # Demand Settings
                        html.Div(id="demand-settings", style={"display": "none"}, children=[
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Demand Multiplier"),
                                    dbc.Input(
                                        id="demand-multiplier",
                                        type="number",
                                        value=2.0,
                                        min=0.1,
                                        max=10.0,
                                        step=0.1
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Label("Duration (days)"),
                                    dbc.Input(
                                        id="demand-duration",
                                        type="number",
                                        value=7,
                                        min=1,
                                        max=30
                                    )
                                ], width=6)
                            ], className="mb-3"),
                        ]),

                        # Product Selection
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Affected Products"),
                                dcc.Dropdown(
                                    id="affected-products",
                                    options=[{"label": "All Products", "value": "all"}] +
                                           [{"label": p, "value": p} for p in products],
                                    value="all",
                                    multi=True
                                ),
                                dbc.FormText("Select specific products or 'All Products'")
                            ])
                        ], className="mb-3"),

                        # Run Button
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    "🚀 Run Scenario",
                                    id="run-scenario-btn",
                                    color="primary",
                                    size="lg",
                                    className="w-100"
                                )
                            ])
                        ])
                    ])
                ], className="mb-4"),

                # Active Scenarios
                dbc.Card([
                    dbc.CardHeader(html.H5("📋 Active Scenarios")),
                    dbc.CardBody([
                        html.Div(id="active-scenarios-list"),
                        dbc.Button(
                            "Clear All",
                            id="clear-scenarios-btn",
                            color="danger",
                            size="sm",
                            className="mt-2"
                        )
                    ])
                ])

            ], width=4),

            # Results Panel
            dbc.Col([
                # Summary Cards
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Baseline Revenue"),
                                html.H3(f"${simulator.baseline_forecast['revenue'].sum():,.0f}",
                                       className="text-primary"),
                                html.P("Next 30 Days", className="text-muted mb-0")
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Baseline Units"),
                                html.H3(f"{simulator.baseline_forecast['units'].sum():,.0f}",
                                       className="text-success"),
                                html.P("Next 30 Days", className="text-muted mb-0")
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Active Scenarios"),
                                html.H3("0", id="scenario-count", className="text-info"),
                                html.P("Currently Loaded", className="text-muted mb-0")
                            ])
                        ])
                    ], width=4)
                ], className="mb-4"),

                # Charts
                dbc.Card([
                    dbc.CardHeader(html.H4("📊 Scenario Comparison")),
                    dbc.CardBody([
                        dcc.Graph(id="scenario-chart", style={"height": "500px"}),
                        html.Hr(),
                        html.H5("Comparison Table"),
                        html.Div(id="comparison-table")
                    ])
                ])
            ], width=8)
        ]),

        # Hidden storage for scenarios
        dcc.Store(id="scenarios-store", data=[])

    ], fluid=True)

    # Callbacks
    @app.callback(
        [Output("promotion-settings", "style"),
         Output("pricing-settings", "style"),
         Output("demand-settings", "style")],
        Input("scenario-type", "value")
    )
    def toggle_settings(scenario_type):
        """Show/hide settings based on scenario type."""
        show = {"display": "block"}
        hide = {"display": "none"}

        if scenario_type == "promotion":
            return show, hide, hide
        elif scenario_type == "pricing":
            return hide, show, hide
        else:  # demand
            return hide, hide, show

    @app.callback(
        [Output("scenarios-store", "data"),
         Output("scenario-count", "children"),
         Output("active-scenarios-list", "children")],
        [Input("run-scenario-btn", "n_clicks"),
         Input("clear-scenarios-btn", "n_clicks")],
        [State("scenarios-store", "data"),
         State("scenario-name", "value"),
         State("scenario-type", "value"),
         State("discount-pct", "value"),
         State("duration-days", "value"),
         State("price-change-pct", "value"),
         State("price-elasticity", "value"),
         State("demand-multiplier", "value"),
         State("demand-duration", "value"),
         State("affected-products", "value")],
        prevent_initial_call=True
    )
    def manage_scenarios(run_clicks, clear_clicks, stored_scenarios,
                        name, scenario_type, discount, duration,
                        price_change, elasticity, demand_mult, demand_dur,
                        affected_products):
        """Add or clear scenarios."""
        ctx = callback_context
        if not ctx.triggered:
            return stored_scenarios, len(stored_scenarios), ""

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "clear-scenarios-btn":
            return [], 0, html.P("No scenarios loaded", className="text-muted")

        # Add new scenario
        if button_id == "run-scenario-btn":
            # Build scenario config
            scenario_data = {
                "name": name,
                "type": scenario_type,
                "discount": discount,
                "duration": duration,
                "price_change": price_change,
                "elasticity": elasticity,
                "demand_multiplier": demand_mult,
                "demand_duration": demand_dur,
                "products": affected_products
            }

            # Run simulation
            if scenario_type == "promotion":
                config = ScenarioConfig(
                    name=name,
                    scenario_type="promotion",
                    discount_percent=discount,
                    duration_days=duration,
                    affected_products=None if "all" in affected_products else affected_products
                )
                result = simulator.simulate_promotion(config)

            elif scenario_type == "pricing":
                config = ScenarioConfig(
                    name=name,
                    scenario_type="pricing",
                    price_change_percent=price_change,
                    price_elasticity=elasticity,
                    affected_products=None if "all" in affected_products else affected_products
                )
                result = simulator.simulate_pricing_change(config)

            else:  # demand
                config = ScenarioConfig(
                    name=name,
                    scenario_type="demand_shift",
                    demand_multiplier=demand_mult,
                    duration_days=demand_dur,
                    affected_products=None if "all" in affected_products else affected_products
                )
                result = simulator.simulate_demand_shift(config)

            # Store scenario
            scenario_data["revenue"] = result["revenue"].sum()
            scenario_data["units"] = result["units"].sum()

            stored_scenarios.append(scenario_data)

            # Create scenario list display
            scenario_items = []
            for i, s in enumerate(stored_scenarios):
                scenario_items.append(
                    dbc.ListGroupItem([
                        html.Div([
                            html.Strong(s["name"]),
                            html.Br(),
                            html.Small(f"Revenue: ${s['revenue']:,.0f} | Units: {s['units']:,.0f}",
                                     className="text-muted")
                        ])
                    ])
                )

            return stored_scenarios, len(stored_scenarios), dbc.ListGroup(scenario_items)

        return stored_scenarios, len(stored_scenarios), ""

    @app.callback(
        [Output("scenario-chart", "figure"),
         Output("comparison-table", "children")],
        Input("scenarios-store", "data")
    )
    def update_charts(stored_scenarios):
        """Update comparison charts."""
        if not stored_scenarios:
            # Show baseline only
            fig = go.Figure()
            daily_baseline = simulator.baseline_forecast.groupby('date')['revenue'].sum().reset_index()

            fig.add_trace(go.Scatter(
                x=daily_baseline['date'],
                y=daily_baseline['revenue'],
                name='Baseline',
                line=dict(color='#1f77b4')
            ))

            fig.update_layout(
                title="Daily Revenue Forecast (Baseline)",
                xaxis_title="Date",
                yaxis_title="Revenue ($)",
                hovermode='x unified'
            )

            return fig, html.P("Run a scenario to see comparisons", className="text-muted")

        # Compare scenarios
        scenario_names = [s["name"] for s in stored_scenarios]
        fig = simulator.visualize_scenario_comparison(scenario_names)

        # Create comparison table
        comparison_df = simulator.compare_scenarios(scenario_names)

        table = dbc.Table.from_dataframe(
            comparison_df.round(2),
            striped=True,
            bordered=True,
            hover=True
        )

        return fig, table

    return app


if __name__ == "__main__":
    # Create and run dashboard
    dashboard = create_scenario_dashboard('data/raw/square_sales.csv')
    print("\n" + "="*70)
    print("🎯 WHAT-IF SCENARIO SIMULATOR DASHBOARD")
    print("="*70)
    print("\n🚀 Starting server...")
    print("📱 Dashboard available at: http://127.0.0.1:8051")
    print("⏹️  Press Ctrl+C to stop\n")

    dashboard.run(host='127.0.0.1', port=8051, debug=True)

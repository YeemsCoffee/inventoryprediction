"""
Interactive Dashboard - Tableau/Power BI style interface using Plotly Dash.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.app import CustomerTrendApp
from src.models.customer_behavior import CustomerBehaviorPredictor


class BusinessIntelligenceDashboard:
    """Interactive BI Dashboard with real-time analytics."""

    def __init__(self, data_source: str = None):
        """
        Initialize dashboard.

        Args:
            data_source: Path to CSV file or 'square' for Square API
        """
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            suppress_callback_exceptions=True
        )

        self.data_source = data_source
        self.ml_app = None
        self.data = None

        self.setup_layout()

    def load_data(self):
        """Load data from source."""
        if self.data_source and self.data_source != 'square':
            self.ml_app = CustomerTrendApp()
            self.ml_app.load_data_from_csv(self.data_source)
            self.data = self.ml_app.processed_data
        else:
            # Use sample data for demo
            self.ml_app = CustomerTrendApp()
            self.ml_app.create_sample_data(n_customers=200, n_transactions=10000)
            self.data = self.ml_app.processed_data

    def setup_layout(self):
        """Create dashboard layout."""
        self.app.layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("🚀 Business Intelligence Dashboard",
                           className="text-center mb-4 mt-4"),
                    html.P("Advanced Analytics & ML-Powered Insights",
                          className="text-center text-muted mb-4")
                ])
            ]),

            # KPI Cards
            dbc.Row([
                dbc.Col(self.create_kpi_card("total-revenue", "💰 Total Revenue", "$0", "success"), width=3),
                dbc.Col(self.create_kpi_card("total-customers", "👥 Total Customers", "0", "info"), width=3),
                dbc.Col(self.create_kpi_card("avg-order-value", "🛒 Avg Order Value", "$0", "warning"), width=3),
                dbc.Col(self.create_kpi_card("churn-risk", "⚠️ At Risk Customers", "0", "danger"), width=3),
            ], className="mb-4"),

            # Tabs for different sections
            dbc.Tabs([
                dbc.Tab(label="📊 Overview", tab_id="overview"),
                dbc.Tab(label="📈 Trends & Forecasts", tab_id="trends"),
                dbc.Tab(label="👥 Customer Analysis", tab_id="customers"),
                dbc.Tab(label="📦 Product Insights", tab_id="products"),
                dbc.Tab(label="🔮 ML Predictions", tab_id="predictions"),
            ], id="tabs", active_tab="overview", className="mb-4"),

            html.Div(id="tab-content"),

            # Refresh button
            dbc.Row([
                dbc.Col([
                    dbc.Button("🔄 Refresh Data", id="refresh-btn",
                             color="primary", className="mt-3")
                ])
            ])
        ], fluid=True)

    def create_kpi_card(self, id_name: str, title: str, value: str, color: str):
        """Create a KPI card."""
        return dbc.Card([
            dbc.CardBody([
                html.H6(title, className="card-title"),
                html.H3(id=id_name, children=value, className=f"text-{color}")
            ])
        ])

    def create_overview_tab(self):
        """Create overview tab content."""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id="sales-over-time")
                ], width=8),
                dbc.Col([
                    dcc.Graph(id="top-products")
                ], width=4)
            ], className="mb-4"),

            dbc.Row([
                dbc.Col([
                    dcc.Graph(id="seasonal-performance")
                ], width=6),
                dbc.Col([
                    dcc.Graph(id="customer-segments")
                ], width=6)
            ])
        ])

    def create_trends_tab(self):
        """Create trends & forecasts tab."""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H4("📈 Demand Forecast"),
                    dcc.Graph(id="demand-forecast")
                ])
            ], className="mb-4"),

            dbc.Row([
                dbc.Col([
                    html.H4("📊 Yearly Growth Trends"),
                    dcc.Graph(id="yearly-trends")
                ], width=6),
                dbc.Col([
                    html.H4("🌡️ Seasonal Patterns"),
                    dcc.Graph(id="seasonal-heatmap")
                ], width=6)
            ])
        ])

    def create_customers_tab(self):
        """Create customer analysis tab."""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H4("🎯 Customer Segmentation"),
                    dcc.Graph(id="customer-seg-viz")
                ], width=6),
                dbc.Col([
                    html.H4("⚠️ Churn Risk Analysis"),
                    dcc.Graph(id="churn-analysis")
                ], width=6)
            ], className="mb-4"),

            dbc.Row([
                dbc.Col([
                    html.H4("💎 Customer Lifetime Value"),
                    dcc.Graph(id="clv-distribution")
                ])
            ])
        ])

    def create_products_tab(self):
        """Create product insights tab."""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H4("🏆 Best Performing Products"),
                    dcc.Graph(id="product-performance")
                ], width=6),
                dbc.Col([
                    html.H4("📦 Product Seasonality"),
                    dcc.Graph(id="product-seasonality-heat")
                ], width=6)
            ])
        ])

    def create_predictions_tab(self):
        """Create ML predictions tab."""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H4("🔮 Next 30 Days Forecast"),
                    dcc.Graph(id="ml-forecast")
                ])
            ], className="mb-4"),

            dbc.Row([
                dbc.Col([
                    html.H4("🎯 High-Risk High-Value Customers"),
                    html.Div(id="at-risk-table")
                ])
            ])
        ])

    def run(self, host: str = '127.0.0.1', port: int = 8050, debug: bool = True):
        """
        Run the dashboard server.

        Args:
            host: Host address
            port: Port number
            debug: Debug mode
        """
        print(f"🚀 Starting Business Intelligence Dashboard...")
        print(f"📊 Dashboard will be available at: http://{host}:{port}")
        print(f"⏳ Loading data...")

        self.load_data()

        print(f"✅ Data loaded successfully!")
        print(f"🌐 Opening browser...")

        self.setup_callbacks()

        self.app.run(host=host, port=port, debug=debug)

    def setup_callbacks(self):
        """Setup all dashboard callbacks."""

        @self.app.callback(
            Output("tab-content", "children"),
            Input("tabs", "active_tab")
        )
        def render_tab_content(active_tab):
            if active_tab == "overview":
                return self.create_overview_tab()
            elif active_tab == "trends":
                return self.create_trends_tab()
            elif active_tab == "customers":
                return self.create_customers_tab()
            elif active_tab == "products":
                return self.create_products_tab()
            elif active_tab == "predictions":
                return self.create_predictions_tab()

        @self.app.callback(
            [Output("total-revenue", "children"),
             Output("total-customers", "children"),
             Output("avg-order-value", "children"),
             Output("churn-risk", "children")],
            Input("refresh-btn", "n_clicks")
        )
        def update_kpis(n_clicks):
            if self.data is None:
                return "$0", "0", "$0", "0"

            total_revenue = f"${self.data['price'].sum():,.0f}" if 'price' in self.data.columns else f"{self.data['amount'].sum():,.0f} items"
            total_customers = f"{self.data['customer_id'].nunique():,}"
            avg_order = f"${self.data.groupby('date')['price'].sum().mean():,.2f}" if 'price' in self.data.columns else "N/A"

            # Simplified churn calculation
            recent_customers = self.data[self.data['date'] >= (self.data['date'].max() - pd.Timedelta(days=30))]
            churn_risk = f"{len(recent_customers['customer_id'].unique()):,}"

            return total_revenue, total_customers, avg_order, churn_risk

        @self.app.callback(
            Output("sales-over-time", "figure"),
            Input("refresh-btn", "n_clicks")
        )
        def update_sales_over_time(n_clicks):
            if self.data is None:
                return go.Figure()

            daily_sales = self.data.groupby('date').agg({
                'amount': 'sum',
                'price': 'sum' if 'price' in self.data.columns else 'count'
            }).reset_index()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily_sales['date'],
                y=daily_sales['price' if 'price' in self.data.columns else 'amount'],
                mode='lines',
                name='Sales',
                line=dict(color='#2E86AB', width=2)
            ))

            fig.update_layout(
                title="Sales Over Time",
                xaxis_title="Date",
                yaxis_title="Revenue" if 'price' in self.data.columns else "Items Sold",
                hovermode='x unified'
            )

            return fig

        @self.app.callback(
            Output("seasonal-performance", "figure"),
            Input("refresh-btn", "n_clicks")
        )
        def update_seasonal_performance(n_clicks):
            if self.data is None or self.ml_app is None:
                return go.Figure()

            seasonal_analysis = self.ml_app.analyze_seasonal_trends()
            seasonal_data = seasonal_analysis['seasonal_patterns']

            fig = go.Figure(data=[
                go.Bar(
                    x=seasonal_data['season'],
                    y=seasonal_data['transaction_count'],
                    marker_color=['#87CEEB', '#90EE90', '#FFD700', '#FFA07A']
                )
            ])

            fig.update_layout(
                title="Performance by Season",
                xaxis_title="Season",
                yaxis_title="Transactions"
            )

            return fig


def create_dashboard(data_source: str = None):
    """
    Create and return dashboard instance.

    Args:
        data_source: Path to data CSV or None for sample data

    Returns:
        Dashboard instance
    """
    return BusinessIntelligenceDashboard(data_source)


if __name__ == "__main__":
    dashboard = create_dashboard()
    dashboard.run(debug=True)

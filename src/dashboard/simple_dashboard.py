"""
Simplified Interactive Dashboard - Stable version without callback loops.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.app import CustomerTrendApp


def create_simple_dashboard(data_source: str = None):
    """Create a simple, stable dashboard."""

    # Initialize Dash app
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    # Load data
    ml_app = CustomerTrendApp()
    if data_source and data_source != 'square':
        ml_app.load_data_from_csv(data_source)
    else:
        ml_app.create_sample_data(n_customers=200, n_transactions=10000)

    data = ml_app.processed_data

    # Generate analyses once
    seasonal_analysis = ml_app.analyze_seasonal_trends()
    yearly_analysis = ml_app.analyze_yearly_trends()
    segmentation = ml_app.segment_customers(n_segments=4)

    # Calculate KPIs
    total_revenue = f"${data['price'].sum():,.0f}" if 'price' in data.columns else f"{data['amount'].sum():,.0f} items"
    total_customers = f"{data['customer_id'].nunique():,}"
    total_transactions = f"{len(data):,}"
    date_range = f"{data['date'].min().strftime('%Y-%m-%d')} to {data['date'].max().strftime('%Y-%m-%d')}"

    # Create figures

    # Sales over time
    daily_sales = data.groupby('date').agg({
        'amount': 'sum',
        'price': 'sum' if 'price' in data.columns else 'count'
    }).reset_index()

    sales_fig = go.Figure()
    sales_fig.add_trace(go.Scatter(
        x=daily_sales['date'],
        y=daily_sales['price' if 'price' in data.columns else 'amount'],
        mode='lines',
        name='Sales',
        line=dict(color='#2E86AB', width=2)
    ))
    sales_fig.update_layout(
        title="Sales Over Time",
        xaxis_title="Date",
        yaxis_title="Revenue" if 'price' in data.columns else "Items Sold",
        height=400
    )

    # Seasonal performance
    seasonal_data = seasonal_analysis['seasonal_patterns']
    seasonal_fig = go.Figure(data=[
        go.Bar(
            x=seasonal_data['season'],
            y=seasonal_data['transaction_count'],
            marker_color=['#87CEEB', '#90EE90', '#FFD700', '#FFA07A']
        )
    ])
    seasonal_fig.update_layout(
        title="Performance by Season",
        xaxis_title="Season",
        yaxis_title="Transactions",
        height=400
    )

    # Top products
    top_products = data.groupby('product')['amount'].sum().nlargest(10).reset_index()
    products_fig = go.Figure(data=[
        go.Bar(x=top_products['amount'], y=top_products['product'], orientation='h')
    ])
    products_fig.update_layout(
        title="Top 10 Products",
        xaxis_title="Units Sold",
        yaxis_title="Product",
        height=400
    )

    # Customer segments
    segment_data = segmentation['segment_analysis']
    segments_fig = go.Figure(data=[
        go.Pie(
            labels=[segmentation['segment_labels'].get(seg, f'Segment {seg}')
                   for seg in segment_data['segment']],
            values=segment_data['customer_count'],
            marker=dict(colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'])
        )
    ])
    segments_fig.update_layout(
        title="Customer Segments",
        height=400
    )

    # Yearly growth
    yearly_data = yearly_analysis['yearly_growth']
    yearly_fig = go.Figure()
    yearly_fig.add_trace(go.Scatter(
        x=yearly_data['year'],
        y=yearly_data['unique_customers'],
        mode='lines+markers',
        name='Customers',
        line=dict(color='#2E86AB', width=3),
        marker=dict(size=10)
    ))
    yearly_fig.update_layout(
        title="Customer Growth Over Years",
        xaxis_title="Year",
        yaxis_title="Unique Customers",
        height=400
    )

    # Layout
    app.layout = dbc.Container([
        html.H1("📊 Business Intelligence Dashboard", className="text-center my-4"),
        html.P("Advanced Analytics & ML-Powered Insights", className="text-center text-muted mb-4"),

        # KPI Cards
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H6("💰 Total Revenue"),
                    html.H3(total_revenue, className="text-success")
                ])
            ]), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H6("👥 Total Customers"),
                    html.H3(total_customers, className="text-info")
                ])
            ]), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H6("📦 Transactions"),
                    html.H3(total_transactions, className="text-warning")
                ])
            ]), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H6("📅 Date Range"),
                    html.P(date_range, className="text-muted", style={'fontSize': '0.9rem'})
                ])
            ]), width=3),
        ], className="mb-4"),

        # Charts
        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=sales_fig)
            ], width=8),
            dbc.Col([
                dcc.Graph(figure=products_fig)
            ], width=4)
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=seasonal_fig)
            ], width=6),
            dbc.Col([
                dcc.Graph(figure=segments_fig)
            ], width=6)
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=yearly_fig)
            ], width=12)
        ], className="mb-4"),

        html.Hr(),
        html.P("💡 Tip: This is a simplified stable dashboard. All data is pre-loaded to prevent callback loops.",
              className="text-muted text-center")

    ], fluid=True)

    return app


if __name__ == "__main__":
    print("🚀 Starting Business Intelligence Dashboard...")
    print("📊 Dashboard will be available at: http://127.0.0.1:8050")

    app = create_simple_dashboard()
    app.run(host='127.0.0.1', port=8050, debug=True)

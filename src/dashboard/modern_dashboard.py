"""
MODERN BUSINESS INTELLIGENCE DASHBOARD
=======================================

A production-grade, accessible, and beautiful dashboard following:
- Apple HIG design principles
- Google Material Design 3
- Nielsen Norman Group UX guidelines
- WCAG 2.1 AA accessibility standards

Key Features:
- 8px grid system for perfect alignment
- Light/dark theme support
- Full keyboard navigation
- Responsive design (mobile-first)
- Loading states and error handling
- Smooth animations (< 300ms)
- Progressive disclosure
- Clear visual hierarchy
"""

import dash
from dash import dcc, html, Input, Output, State, callback, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging
from functools import lru_cache
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import traceback

from .design_system import DesignTokens, generate_custom_css, get_theme

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabasePool:
    """Thread-safe connection pool manager."""

    _instance = None
    _pool = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, database_url, min_conn=2, max_conn=10):
        """Initialize connection pool."""
        if self._pool is None:
            try:
                self._pool = pool.ThreadedConnectionPool(
                    min_conn, max_conn, database_url
                )
                logger.info(f"Database pool initialized ({min_conn}-{max_conn} connections)")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                raise

    @contextmanager
    def get_connection(self):
        """Context manager for safe connection handling."""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self._pool.putconn(conn)

    def close_all(self):
        """Close all connections."""
        if self._pool:
            self._pool.closeall()
            logger.info("All database connections closed")


class ModernDashboard:
    """Modern, accessible BI dashboard."""

    def __init__(self, database_url: str, theme='light'):
        """Initialize dashboard."""
        self.database_url = database_url
        self.theme = theme
        self.tokens = DesignTokens()
        self.colors = get_theme(theme)

        # Initialize connection pool
        self.db_pool = DatabasePool()
        self.db_pool.initialize(database_url)

        # Plotly chart colors matching design system
        self.chart_colors = {
            'primary': self.colors['primary']['500'],
            'success': self.colors['success']['500'],
            'warning': self.colors['warning']['500'],
            'danger': self.colors['danger']['500'],
            'info': self.colors['info']['500'],
            'neutral': [
                self.colors['primary']['500'],
                self.colors['info']['500'],
                self.colors['success']['500'],
                self.colors['warning']['500'],
                self.colors['secondary']['400'],
                self.colors['primary']['300'],
            ]
        }

        # Create app
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[
                dbc.themes.BOOTSTRAP,
                "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
                "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
            ],
            suppress_callback_exceptions=True,
            title="Business Intelligence Dashboard",
            meta_tags=[
                {
                    'name': 'viewport',
                    'content': 'width=device-width, initial-scale=1.0'
                }
            ]
        )

        self._setup_layout()
        self._setup_callbacks()

    def query_db(self, query: str, params=None) -> pd.DataFrame:
        """Execute query with error handling."""
        try:
            with self.db_pool.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                logger.debug(f"Query returned {len(df)} rows")
                return df
        except Exception as e:
            logger.error(f"Query failed: {e}\nQuery: {query[:200]}...")
            return pd.DataFrame()

    def get_locations(self) -> list:
        """Get all locations."""
        try:
            df = self.query_db("""
                SELECT DISTINCT location_id, location_name
                FROM gold.dim_location
                WHERE location_name IS NOT NULL
                ORDER BY location_name
            """)
            if df.empty:
                return []
            return [{'label': row['location_name'], 'value': row['location_id']}
                   for _, row in df.iterrows()]
        except Exception as e:
            logger.error(f"Failed to get locations: {e}")
            return []

    def get_date_range(self) -> tuple:
        """Get data date range."""
        try:
            df = self.query_db("""
                SELECT
                    MIN(order_timestamp) as min_date,
                    MAX(order_timestamp) as max_date
                FROM gold.fact_sales
            """)
            if not df.empty and df.iloc[0]['min_date']:
                return df.iloc[0]['min_date'], df.iloc[0]['max_date']
        except Exception as e:
            logger.error(f"Failed to get date range: {e}")

        return datetime.now() - timedelta(days=90), datetime.now()

    def _setup_layout(self):
        """Setup modern dashboard layout."""

        locations = self.get_locations()
        min_date, max_date = self.get_date_range()
        default_start = max_date - timedelta(days=30) if max_date else datetime.now() - timedelta(days=30)

        self.app.layout = html.Div([
            # Theme store
            dcc.Store(id='theme-store', data=self.theme),

            # Main container with proper spacing
            dbc.Container([
                # Header with theme toggle
                html.Header([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H1([
                                    html.I(className="fas fa-chart-line",
                                          style={'marginRight': self.tokens.SPACING['3']}),
                                    "Business Intelligence"
                                ], style={
                                    'fontSize': self.tokens.TYPOGRAPHY['text_4xl'],
                                    'fontWeight': self.tokens.TYPOGRAPHY['weight_bold'],
                                    'margin': '0',
                                    'color': self.colors['text_primary']
                                }),
                                html.P("ML-Powered Analytics & Predictive Insights", style={
                                    'fontSize': self.tokens.TYPOGRAPHY['text_base'],
                                    'color': self.colors['text_secondary'],
                                    'margin': f"{self.tokens.SPACING['2']} 0 0 0"
                                })
                            ])
                        ], lg=8, md=12),
                        dbc.Col([
                            html.Div([
                                # Theme toggle button
                                dbc.Button([
                                    html.I(id='theme-icon', className="fas fa-moon",
                                          style={'marginRight': self.tokens.SPACING['2']}),
                                    html.Span(id='theme-label', children="Dark Mode")
                                ], id='theme-toggle', color='secondary', outline=True,
                                   className='btn-secondary',
                                   style={'width': '100%'}),
                            ], style={
                                'display': 'flex',
                                'alignItems': 'center',
                                'justifyContent': 'flex-end',
                                'height': '100%'
                            })
                        ], lg=4, md=12, className='mt-3 mt-lg-0')
                    ], align='center')
                ], style={
                    'padding': f"{self.tokens.SPACING['8']} 0",
                    'borderBottom': f"1px solid {self.colors['border']}"
                }),

                # Filters Bar with 8px grid spacing
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-calendar",
                                      style={'marginRight': self.tokens.SPACING['2']}),
                                "Date Range"
                            ], style={
                                'fontSize': self.tokens.TYPOGRAPHY['text_sm'],
                                'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                                'color': self.colors['text_primary'],
                                'marginBottom': self.tokens.SPACING['2'],
                                'display': 'block'
                            }),
                            dcc.DatePickerRange(
                                id='date-picker',
                                min_date_allowed=min_date,
                                max_date_allowed=max_date,
                                start_date=default_start,
                                end_date=max_date,
                                display_format='MMM DD, YYYY',
                                style={'width': '100%'}
                            )
                        ], lg=4, md=6, xs=12, className='mb-3 mb-lg-0'),

                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-store",
                                      style={'marginRight': self.tokens.SPACING['2']}),
                                "Location"
                            ], style={
                                'fontSize': self.tokens.TYPOGRAPHY['text_sm'],
                                'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                                'color': self.colors['text_primary'],
                                'marginBottom': self.tokens.SPACING['2'],
                                'display': 'block'
                            }),
                            dcc.Dropdown(
                                id='location-filter',
                                options=[{'label': 'All Locations', 'value': 'all'}] + locations,
                                value='all',
                                clearable=False,
                                style={'width': '100%'}
                            )
                        ], lg=3, md=6, xs=12, className='mb-3 mb-lg-0'),

                        dbc.Col([
                            html.Label("Quick Select", style={
                                'fontSize': self.tokens.TYPOGRAPHY['text_sm'],
                                'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                                'color': self.colors['text_primary'],
                                'marginBottom': self.tokens.SPACING['2'],
                                'display': 'block'
                            }),
                            dbc.ButtonGroup([
                                dbc.Button("7D", id="btn-7d", size="sm", outline=True, color="primary",
                                          className='btn-secondary'),
                                dbc.Button("30D", id="btn-30d", size="sm", outline=True, color="primary",
                                          className='btn-secondary'),
                                dbc.Button("90D", id="btn-90d", size="sm", outline=True, color="primary",
                                          className='btn-secondary'),
                                dbc.Button("YTD", id="btn-ytd", size="sm", outline=True, color="primary",
                                          className='btn-secondary'),
                            ], style={'width': '100%'})
                        ], lg=3, md=6, xs=12, className='mb-3 mb-lg-0'),

                        dbc.Col([
                            html.Label("Actions", style={
                                'fontSize': self.tokens.TYPOGRAPHY['text_sm'],
                                'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                                'color': self.colors['text_primary'],
                                'marginBottom': self.tokens.SPACING['2'],
                                'display': 'block'
                            }),
                            dbc.Button([
                                html.I(className="fas fa-download",
                                      style={'marginRight': self.tokens.SPACING['2']}),
                                "Export"
                            ], id="export-csv", color="success", size="sm",
                               className='btn-primary',
                               style={'width': '100%'})
                        ], lg=2, md=6, xs=12)
                    ])
                ], className='filter-bar', style={
                    'marginTop': self.tokens.SPACING['6'],
                    'marginBottom': self.tokens.SPACING['6']
                }),

                # Loading wrapper
                dcc.Loading(
                    id="loading-main",
                    type="default",
                    color=self.colors['primary']['500'],
                    children=[html.Div(id='dashboard-content')]
                ),

                # Download component
                dcc.Download(id="download-csv"),

                # Footer
                html.Footer([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-database",
                                  style={'marginRight': self.tokens.SPACING['2'],
                                         'color': self.colors['primary']['500']}),
                            html.Span("AWS RDS PostgreSQL", style={
                                'color': self.colors['text_secondary'],
                                'marginRight': self.tokens.SPACING['6']
                            }),
                            html.I(className="fas fa-robot",
                                  style={'marginRight': self.tokens.SPACING['2'],
                                         'color': self.colors['success']['500']}),
                            html.Span("ML Predictions", style={
                                'color': self.colors['text_secondary'],
                                'marginRight': self.tokens.SPACING['6']
                            }),
                            html.I(className="fas fa-clock",
                                  style={'marginRight': self.tokens.SPACING['2'],
                                         'color': self.colors['info']['500']}),
                            html.Span(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", style={
                                'color': self.colors['text_secondary']
                            })
                        ], style={
                            'fontSize': self.tokens.TYPOGRAPHY['text_sm'],
                            'textAlign': 'center'
                        })
                    ], style={
                        'padding': f"{self.tokens.SPACING['8']} 0",
                        'borderTop': f"1px solid {self.colors['border']}"
                    })
                ])

            ], fluid=True, style={
                'maxWidth': '1400px',
                'padding': f"0 {self.tokens.SPACING['4']}"
            })
        ], style={
            'backgroundColor': self.colors['background'],
            'minHeight': '100vh'
        })

    def _setup_callbacks(self):
        """Setup callbacks."""

        # Theme toggle
        @self.app.callback(
            Output('theme-store', 'data'),
            Output('theme-icon', 'className'),
            Output('theme-label', 'children'),
            Input('theme-toggle', 'n_clicks'),
            State('theme-store', 'data'),
            prevent_initial_call=True
        )
        def toggle_theme(n_clicks, current_theme):
            if not n_clicks:
                return current_theme, "fas fa-moon", "Dark Mode"

            new_theme = 'dark' if current_theme == 'light' else 'light'
            icon = "fas fa-sun" if new_theme == 'dark' else "fas fa-moon"
            label = "Light Mode" if new_theme == 'dark' else "Dark Mode"

            return new_theme, icon, label

        # Quick date buttons
        @self.app.callback(
            Output('date-picker', 'start_date'),
            Output('date-picker', 'end_date'),
            Input('btn-7d', 'n_clicks'),
            Input('btn-30d', 'n_clicks'),
            Input('btn-90d', 'n_clicks'),
            Input('btn-ytd', 'n_clicks'),
            prevent_initial_call=True
        )
        def update_dates(btn7, btn30, btn90, btnytd):
            ctx = callback_context
            if not ctx.triggered:
                raise dash.exceptions.PreventUpdate

            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            end = datetime.now()

            if button_id == 'btn-7d':
                start = end - timedelta(days=7)
            elif button_id == 'btn-30d':
                start = end - timedelta(days=30)
            elif button_id == 'btn-90d':
                start = end - timedelta(days=90)
            else:  # YTD
                start = datetime(end.year, 1, 1)

            return start, end

        # Main dashboard update
        @self.app.callback(
            Output('dashboard-content', 'children'),
            Input('date-picker', 'start_date'),
            Input('date-picker', 'end_date'),
            Input('location-filter', 'value'),
            Input('theme-store', 'data')
        )
        def update_dashboard(start_date, end_date, location, theme):
            try:
                # Update theme if changed
                if theme != self.theme:
                    self.theme = theme
                    self.colors = get_theme(theme)

                logger.info(f"Dashboard update: {start_date} to {end_date}, location={location}, theme={theme}")

                loc_filter = "" if location == 'all' else f"AND dl.location_id = '{location}'"

                # Previous period for comparison
                date_diff = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
                prev_start = pd.to_datetime(start_date) - timedelta(days=date_diff)
                prev_end = pd.to_datetime(start_date) - timedelta(days=1)

                return self._build_dashboard_content(
                    start_date, end_date, prev_start, prev_end, loc_filter
                )

            except Exception as e:
                logger.error(f"Dashboard update failed: {e}")
                logger.error(traceback.format_exc())
                return self._error_state(str(e))

        # Export CSV
        @self.app.callback(
            Output("download-csv", "data"),
            Input("export-csv", "n_clicks"),
            State('date-picker', 'start_date'),
            State('date-picker', 'end_date'),
            State('location-filter', 'value'),
            prevent_initial_call=True
        )
        def export_data(n_clicks, start_date, end_date, location):
            if not n_clicks:
                raise dash.exceptions.PreventUpdate

            try:
                loc_filter = "" if location == 'all' else f"AND dl.location_id = '{location}'"

                query = f"""
                    SELECT
                        fs.order_timestamp::date as date,
                        dl.location_name,
                        dp.product_name,
                        SUM(fs.quantity) as total_quantity,
                        SUM(fs.net_amount) as total_revenue,
                        COUNT(DISTINCT fs.order_id) as order_count
                    FROM gold.fact_sales fs
                    JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
                    JOIN gold.dim_product dp ON fs.product_sk = dp.product_sk
                    WHERE fs.order_timestamp BETWEEN %s AND %s
                    {loc_filter}
                    GROUP BY fs.order_timestamp::date, dl.location_name, dp.product_name
                    ORDER BY date DESC, total_revenue DESC
                """

                df = self.query_db(query, (start_date, end_date))

                return dcc.send_data_frame(
                    df.to_csv,
                    f"sales_report_{start_date}_{end_date}.csv",
                    index=False
                )
            except Exception as e:
                logger.error(f"Export failed: {e}")
                raise dash.exceptions.PreventUpdate

    def _build_dashboard_content(self, start_date, end_date, prev_start, prev_end, loc_filter):
        """Build dashboard content with modern design."""

        # Check for data
        has_data_query = f"""
            SELECT COUNT(*) as count
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {loc_filter}
        """

        has_data_df = self.query_db(has_data_query, (start_date, end_date))

        if has_data_df.empty or has_data_df.iloc[0]['count'] == 0:
            return self._empty_state()

        # Get KPI data
        kpis_current = self._get_kpi_data(start_date, end_date, loc_filter)
        kpis_previous = self._get_kpi_data(
            prev_start.strftime('%Y-%m-%d'),
            prev_end.strftime('%Y-%m-%d'),
            loc_filter
        )

        return html.Div([
            # KPI Cards
            self._render_kpi_cards(kpis_current, kpis_previous),

            # ML Insights
            self._render_ml_insights(start_date, end_date, loc_filter),

            # Charts Grid
            self._render_charts_grid(start_date, end_date, loc_filter)
        ])

    def _get_kpi_data(self, start_date, end_date, loc_filter) -> dict:
        """Get KPI metrics."""
        query = f"""
            SELECT
                COUNT(DISTINCT fs.order_id) as orders,
                SUM(fs.net_amount) as revenue,
                AVG(fs.net_amount) as aov,
                COUNT(DISTINCT fs.customer_sk) as customers
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {loc_filter}
        """

        df = self.query_db(query, (start_date, end_date))

        if df.empty:
            return {'orders': 0, 'revenue': 0, 'aov': 0, 'customers': 0}

        return df.iloc[0].to_dict()

    def _render_kpi_cards(self, current, previous):
        """Render modern KPI cards."""

        def calc_change(curr, prev):
            if prev == 0:
                return 0
            return ((curr - prev) / prev) * 100

        def format_change(change):
            is_positive = change >= 0
            color = self.colors['success']['700'] if is_positive else self.colors['danger']['700']
            bg = self.colors['success']['50'] if is_positive else self.colors['danger']['50']
            icon = "fa-arrow-up" if is_positive else "fa-arrow-down"

            return html.Span([
                html.I(className=f"fas {icon}", style={'marginRight': self.tokens.SPACING['1']}),
                f"{abs(change):.1f}%"
            ], className=f"kpi-change {'positive' if is_positive else 'negative'}", style={
                'color': color,
                'backgroundColor': bg
            })

        kpis = [
            {
                'label': 'Total Orders',
                'value': f"{int(current['orders']):,}",
                'icon': 'shopping-cart',
                'color': self.colors['primary']['500'],
                'change': calc_change(current['orders'], previous['orders'])
            },
            {
                'label': 'Revenue',
                'value': f"${current['revenue']:,.0f}",
                'icon': 'dollar-sign',
                'color': self.colors['success']['500'],
                'change': calc_change(current['revenue'], previous['revenue'])
            },
            {
                'label': 'Avg Order Value',
                'value': f"${current['aov']:.2f}",
                'icon': 'receipt',
                'color': self.colors['warning']['500'],
                'change': calc_change(current['aov'], previous['aov'])
            },
            {
                'label': 'Customers',
                'value': f"{int(current['customers']):,}",
                'icon': 'users',
                'color': self.colors['info']['500'],
                'change': calc_change(current['customers'], previous['customers'])
            }
        ]

        return dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className=f"fas fa-{kpi['icon']}", style={
                            'fontSize': self.tokens.TYPOGRAPHY['text_2xl'],
                            'color': kpi['color'],
                            'marginBottom': self.tokens.SPACING['3']
                        }),
                        html.Div(kpi['value'], className='kpi-value'),
                        html.Div(kpi['label'], className='kpi-label'),
                        html.Div([format_change(kpi['change'])], style={
                            'marginTop': self.tokens.SPACING['3']
                        })
                    ])
                ], className='kpi-card')
            ], lg=3, md=6, xs=12, className='mb-4')
            for kpi in kpis
        ], style={'marginBottom': self.tokens.SPACING['6']})

    def _render_ml_insights(self, start_date, end_date, loc_filter):
        """Render ML insights with modern design."""

        insights = []

        # Churn predictions
        churn_df = self.query_db("""
            SELECT COUNT(*) as high_risk
            FROM predictions.customer_churn_scores
            WHERE churn_probability > 0.7
            AND prediction_date >= CURRENT_DATE - INTERVAL '7 days'
        """)

        if not churn_df.empty and churn_df.iloc[0]['high_risk'] > 0:
            count = int(churn_df.iloc[0]['high_risk'])
            insights.append(
                html.Div([
                    html.I(className="fas fa-exclamation-triangle", style={
                        'fontSize': self.tokens.TYPOGRAPHY['text_xl'],
                        'color': self.colors['warning']['500']
                    }),
                    html.Div([
                        html.Strong("Churn Alert", style={'display': 'block'}),
                        html.Span(f"{count} customers at high risk (>70% probability)")
                    ], style={'flex': '1'})
                ], className='alert alert-warning')
            )

        # Forecasts
        forecast_df = self.query_db("""
            SELECT product_name, AVG(forecasted_quantity) as forecast
            FROM predictions.demand_forecasts
            WHERE forecast_date >= CURRENT_DATE
            AND forecast_date <= CURRENT_DATE + INTERVAL '7 days'
            GROUP BY product_name
            ORDER BY forecast DESC
            LIMIT 1
        """)

        if not forecast_df.empty:
            product = forecast_df.iloc[0]['product_name']
            qty = forecast_df.iloc[0]['forecast']
            insights.append(
                html.Div([
                    html.I(className="fas fa-chart-line", style={
                        'fontSize': self.tokens.TYPOGRAPHY['text_xl'],
                        'color': self.colors['info']['500']
                    }),
                    html.Div([
                        html.Strong("Top Forecast", style={'display': 'block'}),
                        html.Span(f"{product} - {qty:.0f} units next week")
                    ], style={'flex': '1'})
                ], className='alert alert-info')
            )

        # Show helpful message if no insights
        if not insights:
            insights.append(
                html.Div([
                    html.I(className="fas fa-info-circle", style={
                        'fontSize': self.tokens.TYPOGRAPHY['text_xl'],
                        'color': self.colors['info']['500']
                    }),
                    html.Div([
                        html.Strong("ML Predictions Available", style={'display': 'block'}),
                        html.Span("Run ML models to see AI-powered insights here")
                    ], style={'flex': '1'})
                ], className='alert alert-info')
            )

        return html.Div([
            html.H2("AI-Powered Insights", style={
                'fontSize': self.tokens.TYPOGRAPHY['text_2xl'],
                'fontWeight': self.tokens.TYPOGRAPHY['weight_bold'],
                'marginBottom': self.tokens.SPACING['4'],
                'color': self.colors['text_primary']
            }),
            html.Div(insights)
        ], style={'marginBottom': self.tokens.SPACING['8']})

    def _render_charts_grid(self, start_date, end_date, loc_filter):
        """Render charts in grid layout."""

        return html.Div([
            # Revenue trend (full width)
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H3("Revenue Trend", style={
                            'fontSize': self.tokens.TYPOGRAPHY['text_xl'],
                            'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                            'marginBottom': self.tokens.SPACING['4'],
                            'color': self.colors['text_primary']
                        }),
                        dcc.Graph(
                            figure=self._revenue_trend_chart(start_date, end_date, loc_filter),
                            config={'displayModeBar': False}
                        )
                    ], className='chart-container')
                ], xs=12)
            ], style={'marginBottom': self.tokens.SPACING['6']}),

            # Top products & Customer segments
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H3("Top Products", style={
                            'fontSize': self.tokens.TYPOGRAPHY['text_xl'],
                            'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                            'marginBottom': self.tokens.SPACING['4'],
                            'color': self.colors['text_primary']
                        }),
                        dcc.Graph(
                            figure=self._top_products_chart(start_date, end_date, loc_filter),
                            config={'displayModeBar': False}
                        )
                    ], className='chart-container')
                ], lg=6, xs=12, className='mb-4 mb-lg-0'),

                dbc.Col([
                    html.Div([
                        html.H3("Customer Segments", style={
                            'fontSize': self.tokens.TYPOGRAPHY['text_xl'],
                            'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                            'marginBottom': self.tokens.SPACING['4'],
                            'color': self.colors['text_primary']
                        }),
                        dcc.Graph(
                            figure=self._customer_segments_chart(start_date, end_date, loc_filter),
                            config={'displayModeBar': False}
                        )
                    ], className='chart-container')
                ], lg=6, xs=12)
            ], style={'marginBottom': self.tokens.SPACING['6']}),

            # Time patterns
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H3("Hourly Pattern", style={
                            'fontSize': self.tokens.TYPOGRAPHY['text_xl'],
                            'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                            'marginBottom': self.tokens.SPACING['4'],
                            'color': self.colors['text_primary']
                        }),
                        dcc.Graph(
                            figure=self._hourly_pattern_chart(start_date, end_date, loc_filter),
                            config={'displayModeBar': False}
                        )
                    ], className='chart-container')
                ], lg=6, xs=12, className='mb-4 mb-lg-0'),

                dbc.Col([
                    html.Div([
                        html.H3("Weekly Pattern", style={
                            'fontSize': self.tokens.TYPOGRAPHY['text_xl'],
                            'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                            'marginBottom': self.tokens.SPACING['4'],
                            'color': self.colors['text_primary']
                        }),
                        dcc.Graph(
                            figure=self._weekly_pattern_chart(start_date, end_date, loc_filter),
                            config={'displayModeBar': False}
                        )
                    ], className='chart-container')
                ], lg=6, xs=12)
            ])
        ])

    # Chart methods (using modern styling)
    def _revenue_trend_chart(self, start_date, end_date, loc_filter):
        """Revenue trend chart."""
        query = f"""
            SELECT
                DATE(fs.order_timestamp) as date,
                SUM(fs.net_amount) as revenue,
                COUNT(DISTINCT fs.order_id) as orders
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {loc_filter}
            GROUP BY DATE(fs.order_timestamp)
            ORDER BY date
        """

        df = self.query_db(query, (start_date, end_date))

        if df.empty:
            return go.Figure().add_annotation(text="No data available", showarrow=False)

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Bar(x=df['date'], y=df['revenue'], name="Revenue",
                  marker_color=self.chart_colors['primary']),
            secondary_y=False
        )

        fig.add_trace(
            go.Scatter(x=df['date'], y=df['orders'], name="Orders",
                      mode='lines+markers',
                      line=dict(color=self.chart_colors['success'], width=3),
                      marker=dict(size=6)),
            secondary_y=True
        )

        fig.update_xaxes(title_text="")
        fig.update_yaxes(title_text="Revenue ($)", secondary_y=False)
        fig.update_yaxes(title_text="Orders", secondary_y=True)
        fig.update_layout(
            hovermode='x unified',
            height=350,
            showlegend=True,
            plot_bgcolor=self.colors['surface'],
            paper_bgcolor=self.colors['surface'],
            font=dict(family=self.tokens.TYPOGRAPHY['font_primary'],
                     color=self.colors['text_primary']),
            margin=dict(l=40, r=40, t=20, b=40)
        )

        return fig

    def _top_products_chart(self, start_date, end_date, loc_filter):
        """Top products chart."""
        query = f"""
            SELECT
                dp.product_name,
                SUM(fs.net_amount) as revenue
            FROM gold.fact_sales fs
            JOIN gold.dim_product dp ON fs.product_sk = dp.product_sk
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {loc_filter}
            GROUP BY dp.product_name
            ORDER BY revenue DESC
            LIMIT 10
        """

        df = self.query_db(query, (start_date, end_date))

        if df.empty:
            return go.Figure().add_annotation(text="No data available", showarrow=False)

        fig = go.Figure(go.Bar(
            y=df['product_name'],
            x=df['revenue'],
            orientation='h',
            marker_color=self.chart_colors['warning'],
            text=df['revenue'].apply(lambda x: f'${x:,.0f}'),
            textposition='outside'
        ))

        fig.update_layout(
            xaxis_title="Revenue ($)",
            yaxis_title="",
            height=350,
            yaxis={'categoryorder': 'total ascending'},
            plot_bgcolor=self.colors['surface'],
            paper_bgcolor=self.colors['surface'],
            font=dict(family=self.tokens.TYPOGRAPHY['font_primary'],
                     color=self.colors['text_primary']),
            margin=dict(l=150, r=40, t=20, b=40)
        )

        return fig

    def _customer_segments_chart(self, start_date, end_date, loc_filter):
        """Customer segments chart."""
        query = f"""
            SELECT
                CASE
                    WHEN order_count >= 10 THEN 'VIP (10+)'
                    WHEN order_count >= 5 THEN 'Loyal (5-9)'
                    WHEN order_count >= 2 THEN 'Regular (2-4)'
                    ELSE 'New (1)'
                END as segment,
                COUNT(*) as customers
            FROM (
                SELECT
                    fs.customer_sk,
                    COUNT(DISTINCT fs.order_id) as order_count
                FROM gold.fact_sales fs
                JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
                WHERE fs.order_timestamp BETWEEN %s AND %s
                {loc_filter}
                GROUP BY fs.customer_sk
            ) stats
            GROUP BY segment
        """

        df = self.query_db(query, (start_date, end_date))

        if df.empty:
            return go.Figure().add_annotation(text="No data available", showarrow=False)

        fig = go.Figure(go.Pie(
            labels=df['segment'],
            values=df['customers'],
            hole=0.4,
            marker_colors=self.chart_colors['neutral'][:len(df)],
            textinfo='label+percent'
        ))

        fig.update_layout(
            height=350,
            plot_bgcolor=self.colors['surface'],
            paper_bgcolor=self.colors['surface'],
            font=dict(family=self.tokens.TYPOGRAPHY['font_primary'],
                     color=self.colors['text_primary']),
            margin=dict(l=40, r=40, t=20, b=40)
        )

        return fig

    def _hourly_pattern_chart(self, start_date, end_date, loc_filter):
        """Hourly pattern chart."""
        query = f"""
            SELECT
                fs.order_hour as hour,
                SUM(fs.net_amount) as revenue
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {loc_filter}
            GROUP BY fs.order_hour
            ORDER BY fs.order_hour
        """

        df = self.query_db(query, (start_date, end_date))

        if df.empty:
            return go.Figure().add_annotation(text="No data available", showarrow=False)

        fig = go.Figure(go.Bar(
            x=df['hour'],
            y=df['revenue'],
            marker_color=self.chart_colors['info']
        ))

        fig.update_layout(
            xaxis_title="Hour of Day",
            yaxis_title="Revenue ($)",
            height=300,
            xaxis=dict(tickmode='linear'),
            plot_bgcolor=self.colors['surface'],
            paper_bgcolor=self.colors['surface'],
            font=dict(family=self.tokens.TYPOGRAPHY['font_primary'],
                     color=self.colors['text_primary']),
            margin=dict(l=40, r=40, t=20, b=40)
        )

        return fig

    def _weekly_pattern_chart(self, start_date, end_date, loc_filter):
        """Weekly pattern chart."""
        query = f"""
            SELECT
                CASE fs.order_day_of_week
                    WHEN 0 THEN 'Sun'
                    WHEN 1 THEN 'Mon'
                    WHEN 2 THEN 'Tue'
                    WHEN 3 THEN 'Wed'
                    WHEN 4 THEN 'Thu'
                    WHEN 5 THEN 'Fri'
                    WHEN 6 THEN 'Sat'
                END as day,
                fs.order_day_of_week as dow,
                SUM(fs.net_amount) as revenue
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {loc_filter}
            GROUP BY fs.order_day_of_week, day
            ORDER BY dow
        """

        df = self.query_db(query, (start_date, end_date))

        if df.empty:
            return go.Figure().add_annotation(text="No data available", showarrow=False)

        fig = go.Figure(go.Bar(
            x=df['day'],
            y=df['revenue'],
            marker_color=self.chart_colors['success']
        ))

        fig.update_layout(
            xaxis_title="",
            yaxis_title="Revenue ($)",
            height=300,
            plot_bgcolor=self.colors['surface'],
            paper_bgcolor=self.colors['surface'],
            font=dict(family=self.tokens.TYPOGRAPHY['font_primary'],
                     color=self.colors['text_primary']),
            margin=dict(l=40, r=40, t=20, b=40)
        )

        return fig

    def _empty_state(self):
        """Empty state with helpful guidance."""
        return html.Div([
            html.I(className="fas fa-inbox", style={
                'fontSize': '80px',
                'color': self.colors['neutral']['300'],
                'marginBottom': self.tokens.SPACING['6']
            }),
            html.H3("No Data Available", style={
                'fontSize': self.tokens.TYPOGRAPHY['text_2xl'],
                'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                'color': self.colors['text_secondary'],
                'marginBottom': self.tokens.SPACING['3']
            }),
            html.P("No transactions found for the selected period and location.", style={
                'fontSize': self.tokens.TYPOGRAPHY['text_base'],
                'color': self.colors['text_secondary'],
                'marginBottom': self.tokens.SPACING['6']
            }),
            dbc.Button([
                html.I(className="fas fa-sync", style={'marginRight': self.tokens.SPACING['2']}),
                "Sync Data"
            ], color="primary", className='btn-primary')
        ], style={
            'textAlign': 'center',
            'padding': f"{self.tokens.SPACING['20']} 0",
            'backgroundColor': self.colors['surface'],
            'borderRadius': self.tokens.RADIUS['md']
        })

    def _error_state(self, error_msg):
        """Error state with helpful information."""
        return html.Div([
            html.I(className="fas fa-exclamation-circle", style={
                'fontSize': '80px',
                'color': self.colors['danger']['500'],
                'marginBottom': self.tokens.SPACING['6']
            }),
            html.H3("Something Went Wrong", style={
                'fontSize': self.tokens.TYPOGRAPHY['text_2xl'],
                'fontWeight': self.tokens.TYPOGRAPHY['weight_semibold'],
                'color': self.colors['text_primary'],
                'marginBottom': self.tokens.SPACING['3']
            }),
            html.P(f"Error: {error_msg}", style={
                'fontSize': self.tokens.TYPOGRAPHY['text_sm'],
                'color': self.colors['text_secondary'],
                'fontFamily': self.tokens.TYPOGRAPHY['font_mono'],
                'marginBottom': self.tokens.SPACING['6'],
                'padding': self.tokens.SPACING['4'],
                'backgroundColor': self.colors['neutral']['100'],
                'borderRadius': self.tokens.RADIUS['base']
            }),
            html.P("Please check the logs or contact support.", style={
                'fontSize': self.tokens.TYPOGRAPHY['text_base'],
                'color': self.colors['text_secondary']
            })
        ], style={
            'textAlign': 'center',
            'padding': f"{self.tokens.SPACING['20']} 0",
            'backgroundColor': self.colors['surface'],
            'borderRadius': self.tokens.RADIUS['md']
        })

    def run(self, host='0.0.0.0', port=8050, debug=False):
        """Run dashboard."""
        try:
            logger.info(f"Starting modern dashboard on {host}:{port}")
            self.app.run(host=host, port=port, debug=debug)
        finally:
            self.db_pool.close_all()


if __name__ == "__main__":
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        exit(1)

    print("\n" + "=" * 70)
    print("🎨 MODERN BUSINESS INTELLIGENCE DASHBOARD")
    print("=" * 70)
    print("\n✨ Design Features:")
    print("  🎯 8px grid system")
    print("  🌓 Light/dark theme support")
    print("  ♿ WCAG 2.1 AA accessible")
    print("  📱 Mobile responsive")
    print("  ⚡ Smooth animations")
    print("  🎨 Modern Material Design 3")
    print("\n🌐 Dashboard: http://localhost:8050")
    print("⏹️  Press Ctrl+C to stop\n")

    dashboard = ModernDashboard(database_url)
    dashboard.run(debug=False)

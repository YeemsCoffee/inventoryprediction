"""
Enhanced Production Dashboard with PostgreSQL Integration
Beautiful UI with date range selection, location filtering, and modern design
"""

import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()


class EnhancedDashboard:
    """Enhanced production dashboard with PostgreSQL integration."""

    def __init__(self, database_url: str):
        """
        Initialize dashboard.

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self.conn = None

        # Modern color scheme
        self.colors = {
            'primary': '#4F46E5',  # Indigo
            'secondary': '#10B981',  # Green
            'accent': '#F59E0B',  # Amber
            'danger': '#EF4444',  # Red
            'info': '#3B82F6',  # Blue
            'dark': '#1F2937',  # Dark gray
            'light': '#F3F4F6',  # Light gray
            'success': '#10B981',
            'warning': '#F59E0B'
        }

        # Create Dash app
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
            suppress_callback_exceptions=True
        )

        self._setup_layout()
        self._setup_callbacks()

    def connect_db(self):
        """Connect to PostgreSQL."""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(self.database_url)
        return self.conn

    def query_db(self, query: str, params=None) -> pd.DataFrame:
        """Execute query and return DataFrame."""
        conn = self.connect_db()
        return pd.read_sql_query(query, conn, params=params)

    def get_locations(self) -> list:
        """Get list of all locations."""
        try:
            df = self.query_db("SELECT DISTINCT location_id, location_name FROM gold.dim_location ORDER BY location_name")
            return [{'label': row['location_name'], 'value': row['location_id']}
                   for _, row in df.iterrows()]
        except:
            return [{'label': 'All Locations', 'value': 'all'}]

    def get_date_range(self) -> tuple:
        """Get min and max dates from data."""
        try:
            df = self.query_db("SELECT MIN(order_timestamp) as min_date, MAX(order_timestamp) as max_date FROM gold.fact_sales")
            if not df.empty and df.iloc[0]['min_date']:
                return df.iloc[0]['min_date'], df.iloc[0]['max_date']
        except:
            pass
        # Default to last 90 days
        return datetime.now() - timedelta(days=90), datetime.now()

    def _setup_layout(self):
        """Setup dashboard layout."""

        # Get initial data
        locations = self.get_locations()
        min_date, max_date = self.get_date_range()

        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H1([
                            html.I(className="fas fa-chart-line me-3"),
                            "Business Intelligence Dashboard"
                        ], className="display-4 fw-bold text-primary mb-2"),
                        html.P("Real-time analytics powered by AWS RDS PostgreSQL",
                              className="lead text-muted")
                    ], className="text-center py-4")
                ])
            ]),

            html.Hr(className="my-4"),

            # Filters Section
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        # Date Range Picker
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-calendar-alt me-2"),
                                "Date Range"
                            ], className="fw-bold mb-2"),
                            dcc.DatePickerRange(
                                id='date-range-picker',
                                min_date_allowed=min_date,
                                max_date_allowed=max_date,
                                start_date=max_date - timedelta(days=30),
                                end_date=max_date,
                                display_format='MMM DD, YYYY',
                                style={'width': '100%'}
                            )
                        ], md=4),

                        # Location Filter
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-map-marker-alt me-2"),
                                "Location"
                            ], className="fw-bold mb-2"),
                            dcc.Dropdown(
                                id='location-filter',
                                options=[{'label': 'All Locations', 'value': 'all'}] + locations,
                                value='all',
                                clearable=False
                            )
                        ], md=4),

                        # Quick Date Filters
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-clock me-2"),
                                "Quick Select"
                            ], className="fw-bold mb-2"),
                            dbc.ButtonGroup([
                                dbc.Button("7D", id="btn-7d", outline=True, color="primary", size="sm"),
                                dbc.Button("30D", id="btn-30d", outline=True, color="primary", size="sm"),
                                dbc.Button("90D", id="btn-90d", outline=True, color="primary", size="sm"),
                                dbc.Button("YTD", id="btn-ytd", outline=True, color="primary", size="sm"),
                                dbc.Button("All", id="btn-all", outline=True, color="primary", size="sm"),
                            ], className="w-100")
                        ], md=4)
                    ])
                ])
            ], className="shadow-sm mb-4"),

            # Loading Spinner
            dcc.Loading(
                id="loading",
                type="default",
                children=[
                    # KPI Cards
                    html.Div(id='kpi-cards'),

                    # Main Charts
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="fas fa-chart-area me-2"),
                                    "Revenue Trend"
                                ], className="fw-bold"),
                                dbc.CardBody([
                                    dcc.Graph(id='revenue-trend-chart')
                                ])
                            ], className="shadow-sm mb-4")
                        ], md=12)
                    ]),

                    # Product and Customer Analytics
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="fas fa-box me-2"),
                                    "Top Products"
                                ], className="fw-bold"),
                                dbc.CardBody([
                                    dcc.Graph(id='top-products-chart')
                                ])
                            ], className="shadow-sm mb-4")
                        ], md=6),

                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="fas fa-users me-2"),
                                    "Customer Segments"
                                ], className="fw-bold"),
                                dbc.CardBody([
                                    dcc.Graph(id='customer-segments-chart')
                                ])
                            ], className="shadow-sm mb-4")
                        ], md=6)
                    ]),

                    # Time Analysis
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="fas fa-clock me-2"),
                                    "Sales by Hour"
                                ], className="fw-bold"),
                                dbc.CardBody([
                                    dcc.Graph(id='hourly-sales-chart')
                                ])
                            ], className="shadow-sm mb-4")
                        ], md=6),

                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="fas fa-calendar-week me-2"),
                                    "Sales by Day of Week"
                                ], className="fw-bold"),
                                dbc.CardBody([
                                    dcc.Graph(id='dow-sales-chart')
                                ])
                            ], className="shadow-sm mb-4")
                        ], md=6)
                    ])
                ]
            ),

            # Footer
            html.Hr(className="my-4"),
            html.Div([
                html.P([
                    html.I(className="fas fa-database me-2"),
                    "Data updated from Square API → AWS RDS PostgreSQL"
                ], className="text-center text-muted small mb-0")
            ], className="py-3")

        ], fluid=True, style={'backgroundColor': '#F9FAFB', 'minHeight': '100vh', 'padding': '20px'})

    def _setup_callbacks(self):
        """Setup all dashboard callbacks."""

        # Quick date button callbacks
        @self.app.callback(
            Output('date-range-picker', 'start_date'),
            Output('date-range-picker', 'end_date'),
            Input('btn-7d', 'n_clicks'),
            Input('btn-30d', 'n_clicks'),
            Input('btn-90d', 'n_clicks'),
            Input('btn-ytd', 'n_clicks'),
            Input('btn-all', 'n_clicks'),
            prevent_initial_call=True
        )
        def update_date_range(btn_7d, btn_30d, btn_90d, btn_ytd, btn_all):
            ctx = callback.ctx
            if not ctx.triggered:
                raise dash.exceptions.PreventUpdate

            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            end_date = datetime.now()

            if button_id == 'btn-7d':
                start_date = end_date - timedelta(days=7)
            elif button_id == 'btn-30d':
                start_date = end_date - timedelta(days=30)
            elif button_id == 'btn-90d':
                start_date = end_date - timedelta(days=90)
            elif button_id == 'btn-ytd':
                start_date = datetime(end_date.year, 1, 1)
            else:  # btn-all
                min_date, _ = self.get_date_range()
                start_date = min_date

            return start_date, end_date

        # Main data update callback
        @self.app.callback(
            Output('kpi-cards', 'children'),
            Output('revenue-trend-chart', 'figure'),
            Output('top-products-chart', 'figure'),
            Output('customer-segments-chart', 'figure'),
            Output('hourly-sales-chart', 'figure'),
            Output('dow-sales-chart', 'figure'),
            Input('date-range-picker', 'start_date'),
            Input('date-range-picker', 'end_date'),
            Input('location-filter', 'value')
        )
        def update_dashboard(start_date, end_date, location):
            # Build location filter
            location_filter = "" if location == 'all' else f"AND dl.location_id = '{location}'"

            # Get KPI data
            kpis = self._get_kpis(start_date, end_date, location_filter)

            # Get charts
            revenue_trend = self._get_revenue_trend(start_date, end_date, location_filter)
            top_products = self._get_top_products(start_date, end_date, location_filter)
            customer_segments = self._get_customer_segments(start_date, end_date, location_filter)
            hourly_sales = self._get_hourly_sales(start_date, end_date, location_filter)
            dow_sales = self._get_dow_sales(start_date, end_date, location_filter)

            return kpis, revenue_trend, top_products, customer_segments, hourly_sales, dow_sales

    def _get_kpis(self, start_date, end_date, location_filter):
        """Get KPI metrics."""
        query = f"""
            SELECT
                COUNT(DISTINCT fs.order_id) as total_orders,
                SUM(fs.net_amount) as total_revenue,
                AVG(fs.net_amount) as avg_order_value,
                COUNT(DISTINCT fs.customer_sk) as unique_customers
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {location_filter}
        """

        df = self.query_db(query, (start_date, end_date))

        if df.empty:
            return html.Div("No data available", className="text-center text-muted")

        row = df.iloc[0]

        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-shopping-cart fa-2x text-primary mb-3"),
                            html.H3(f"{int(row['total_orders']):,}", className="fw-bold mb-0"),
                            html.P("Total Orders", className="text-muted mb-0")
                        ], className="text-center")
                    ])
                ], className="shadow-sm")
            ], md=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-dollar-sign fa-2x text-success mb-3"),
                            html.H3(f"${row['total_revenue']:,.0f}", className="fw-bold mb-0"),
                            html.P("Total Revenue", className="text-muted mb-0")
                        ], className="text-center")
                    ])
                ], className="shadow-sm")
            ], md=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-receipt fa-2x text-warning mb-3"),
                            html.H3(f"${row['avg_order_value']:.2f}", className="fw-bold mb-0"),
                            html.P("Avg Order Value", className="text-muted mb-0")
                        ], className="text-center")
                    ])
                ], className="shadow-sm")
            ], md=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-users fa-2x text-info mb-3"),
                            html.H3(f"{int(row['unique_customers']):,}", className="fw-bold mb-0"),
                            html.P("Unique Customers", className="text-muted mb-0")
                        ], className="text-center")
                    ])
                ], className="shadow-sm")
            ], md=3)
        ], className="mb-4")

    def _get_revenue_trend(self, start_date, end_date, location_filter):
        """Get revenue trend chart."""
        query = f"""
            SELECT
                DATE(fs.order_timestamp) as date,
                SUM(fs.net_amount) as revenue,
                COUNT(DISTINCT fs.order_id) as orders
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {location_filter}
            GROUP BY DATE(fs.order_timestamp)
            ORDER BY date
        """

        df = self.query_db(query, (start_date, end_date))

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Bar(x=df['date'], y=df['revenue'], name="Revenue",
                  marker_color=self.colors['primary']),
            secondary_y=False
        )

        fig.add_trace(
            go.Scatter(x=df['date'], y=df['orders'], name="Orders",
                      mode='lines+markers', line=dict(color=self.colors['secondary'], width=3)),
            secondary_y=True
        )

        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Revenue ($)", secondary_y=False)
        fig.update_yaxes(title_text="Orders", secondary_y=True)
        fig.update_layout(hovermode='x unified', height=400)

        return fig

    def _get_top_products(self, start_date, end_date, location_filter):
        """Get top products chart."""
        query = f"""
            SELECT
                dp.product_name,
                SUM(fs.net_amount) as revenue,
                SUM(fs.quantity) as quantity
            FROM gold.fact_sales fs
            JOIN gold.dim_product dp ON fs.product_sk = dp.product_sk
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {location_filter}
            GROUP BY dp.product_name
            ORDER BY revenue DESC
            LIMIT 10
        """

        df = self.query_db(query, (start_date, end_date))

        fig = go.Figure(go.Bar(
            y=df['product_name'],
            x=df['revenue'],
            orientation='h',
            marker_color=self.colors['accent'],
            text=df['revenue'].apply(lambda x: f'${x:,.0f}'),
            textposition='outside'
        ))

        fig.update_layout(
            xaxis_title="Revenue ($)",
            yaxis_title="",
            height=400,
            yaxis={'categoryorder': 'total ascending'}
        )

        return fig

    def _get_customer_segments(self, start_date, end_date, location_filter):
        """Get customer segments chart."""
        query = f"""
            SELECT
                CASE
                    WHEN order_count >= 10 THEN 'VIP (10+ orders)'
                    WHEN order_count >= 5 THEN 'Loyal (5-9 orders)'
                    WHEN order_count >= 2 THEN 'Regular (2-4 orders)'
                    ELSE 'New (1 order)'
                END as segment,
                COUNT(*) as customer_count,
                SUM(total_spent) as total_revenue
            FROM (
                SELECT
                    fs.customer_sk,
                    COUNT(DISTINCT fs.order_id) as order_count,
                    SUM(fs.net_amount) as total_spent
                FROM gold.fact_sales fs
                JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
                WHERE fs.order_timestamp BETWEEN %s AND %s
                {location_filter}
                GROUP BY fs.customer_sk
            ) customer_stats
            GROUP BY segment
            ORDER BY total_revenue DESC
        """

        df = self.query_db(query, (start_date, end_date))

        fig = go.Figure(go.Pie(
            labels=df['segment'],
            values=df['customer_count'],
            hole=0.4,
            marker_colors=[self.colors['primary'], self.colors['success'],
                          self.colors['warning'], self.colors['info']],
            textinfo='label+percent'
        ))

        fig.update_layout(height=400)

        return fig

    def _get_hourly_sales(self, start_date, end_date, location_filter):
        """Get hourly sales pattern."""
        query = f"""
            SELECT
                fs.order_hour as hour,
                SUM(fs.net_amount) as revenue,
                COUNT(DISTINCT fs.order_id) as orders
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {location_filter}
            GROUP BY fs.order_hour
            ORDER BY fs.order_hour
        """

        df = self.query_db(query, (start_date, end_date))

        fig = go.Figure(go.Bar(
            x=df['hour'],
            y=df['revenue'],
            marker_color=self.colors['info'],
            text=df['revenue'].apply(lambda x: f'${x:,.0f}'),
            textposition='outside'
        ))

        fig.update_layout(
            xaxis_title="Hour of Day",
            yaxis_title="Revenue ($)",
            height=400,
            xaxis=dict(tickmode='linear')
        )

        return fig

    def _get_dow_sales(self, start_date, end_date, location_filter):
        """Get day of week sales."""
        query = f"""
            SELECT
                CASE fs.order_day_of_week
                    WHEN 0 THEN 'Sunday'
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                END as day_name,
                fs.order_day_of_week as dow,
                SUM(fs.net_amount) as revenue
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            WHERE fs.order_timestamp BETWEEN %s AND %s
            {location_filter}
            GROUP BY fs.order_day_of_week, day_name
            ORDER BY dow
        """

        df = self.query_db(query, (start_date, end_date))

        fig = go.Figure(go.Bar(
            x=df['day_name'],
            y=df['revenue'],
            marker_color=self.colors['secondary'],
            text=df['revenue'].apply(lambda x: f'${x:,.0f}'),
            textposition='outside'
        ))

        fig.update_layout(
            xaxis_title="",
            yaxis_title="Revenue ($)",
            height=400
        )

        return fig

    def run(self, host='0.0.0.0', port=8050, debug=False):
        """Run the dashboard."""
        self.app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env")
        exit(1)

    print("\n" + "=" * 70)
    print("🚀 ENHANCED BUSINESS INTELLIGENCE DASHBOARD")
    print("=" * 70)
    print("\n📊 Features:")
    print("  • Date range selection")
    print("  • Location filtering")
    print("  • Real-time KPIs")
    print("  • Interactive charts")
    print("  • Modern, responsive UI")
    print("\n🔌 Data source: AWS RDS PostgreSQL")
    print("\n🌐 Dashboard URL: http://localhost:8050")
    print("⏹️  Press Ctrl+C to stop\n")

    dashboard = EnhancedDashboard(database_url)
    dashboard.run(debug=False)

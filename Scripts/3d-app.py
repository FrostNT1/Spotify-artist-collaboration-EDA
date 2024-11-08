from dash import Dash, html, dcc, callback, Output, Input
import plotly.graph_objects as go
import pandas as pd
import networkx as nx
import numpy as np
from networkx.drawing.layout import spring_layout

class SpotifyNetworkApp:
    def __init__(self):
        self.app = Dash(__name__)
        self.load_data()
        self.setup_network()
        self.setup_layout()
        self.setup_callbacks()

    def load_data(self):
        """Load and prepare data"""
        self.edges_df = pd.read_csv('../Data/edges.csv')
        self.nodes_df = pd.read_csv('../Data/nodes.csv')
        # Convert genres string to list
        self.nodes_df['genres'] = self.nodes_df['genres'].apply(lambda x: eval(x) if isinstance(x, str) else [])
        
    def setup_network(self):
        """Initialize network and calculate degrees"""
        self.G = nx.from_pandas_edgelist(self.edges_df, 'id_0', 'id_1')
        self.degrees = dict(self.G.degree())

    def get_top_artists(self, n=100):
        """Get top n artists by number of collaborations"""
        top_artists = sorted(self.degrees.items(), key=lambda x: x[1], reverse=True)[:n]
        return [artist[0] for artist in top_artists]

    def create_3d_network(self, artist_ids):
        """Create 3D network visualization"""
        # Create subgraph for selected artists
        subgraph = self.G.subgraph(artist_ids)
        
        # Get 3D layout
        pos_3d = spring_layout(subgraph, dim=3)
        
        # Create edges traces
        edge_x, edge_y, edge_z = [], [], []
        for edge in subgraph.edges():
            x0, y0, z0 = pos_3d[edge[0]]
            x1, y1, z1 = pos_3d[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_z.extend([z0, z1, None])
            
        edges_trace = go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='#888', width=1),
            hoverinfo='none'
        )
        
        # Create nodes trace
        node_x, node_y, node_z = [], [], []
        node_text = []
        node_size = []
        node_color = []
        
        for node in subgraph.nodes():
            x, y, z = pos_3d[node]
            node_x.append(x)
            node_y.append(y)
            node_z.append(z)
            
            artist_info = self.nodes_df[self.nodes_df['spotify_id'] == node].iloc[0]
            node_text.append(f"Artist: {artist_info['name']}<br>"
                           f"Followers: {artist_info['followers']:,}<br>"
                           f"Popularity: {artist_info['popularity']}")
            node_size.append(np.sqrt(self.degrees[node]))
            node_color.append(artist_info['popularity'])
            
        nodes_trace = go.Scatter3d(
            x=node_x, y=node_y, z=node_z,
            mode='markers',
            marker=dict(
                size=node_size,
                color=node_color,
                colorscale='Viridis',
                colorbar=dict(title='Popularity'),
                line=dict(color='#fff', width=0.5)
            ),
            text=node_text,
            hoverinfo='text'
        )
        
        return go.Figure(
            data=[edges_trace, nodes_trace],
            layout=go.Layout(
                title='3D Spotify Artist Collaboration Network',
                scene=dict(
                    xaxis=dict(showticklabels=False),
                    yaxis=dict(showticklabels=False),
                    zaxis=dict(showticklabels=False)
                ),
                margin=dict(l=0, r=0, t=40, b=0)
            )
        )

    def setup_layout(self):
        """Define app layout"""
        self.app.layout = html.Div([
            html.H1("Spotify Artists Collaboration Network (3D)", 
                   style={'textAlign': 'center'}),
            
            # Controls
            html.Div([
                html.Label("Number of top artists to show:"),
                dcc.Slider(
                    id='num-artists-slider',
                    min=10,
                    max=200,
                    step=10,
                    value=50,
                    marks={i: str(i) for i in range(0, 201, 50)}
                ),
            ], style={'margin': '20px'}),
            
            # Main content container
            html.Div([
                # 3D Network visualization
                html.Div([
                    dcc.Graph(
                        id='network-3d',
                        style={'height': '600px'}
                    )
                ], style={'width': '70%', 'display': 'inline-block'}),
                
                # Info panel
                html.Div([
                    html.Div(id='node-info', 
                            style={'padding': '20px', 
                                  'backgroundColor': '#f8f9fa',
                                  'borderRadius': '5px',
                                  'height': '100%'})
                ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top'})
            ], style={'display': 'flex'})
        ])

    def setup_callbacks(self):
        """Set up app callbacks"""
        @self.app.callback(
            Output('network-3d', 'figure'),
            Input('num-artists-slider', 'value')
        )
        def update_network(n_artists):
            top_artists = self.get_top_artists(n_artists)
            return self.create_3d_network(top_artists)

        @self.app.callback(
            Output('node-info', 'children'),
            Input('network-3d', 'tapNodeData')
        )
        def display_node_data(data):
            if not data:
                return html.Div([
                    html.H3("Artist Information"),
                    html.P("Click on a node to see artist details")
                ])
            
            return html.Div([
                html.H3("Artist Information", style={'color': '#2c3e50'}),
                html.Hr(),
                html.H4(data['name'], style={'color': '#e74c3c'}),
                html.Div([
                    html.P(f"🎵 Number of collaborations: {data['size']}", 
                          style={'fontSize': '16px'}),
                    html.P(f"👥 Followers: {data['followers']:,}", 
                          style={'fontSize': '16px'}),
                    html.P(f"⭐ Popularity score: {data['popularity']}", 
                          style={'fontSize': '16px'}),
                    html.H5("Genres:", style={'marginTop': '20px'}),
                    html.Ul([html.Li(genre) for genre in data['genres']], 
                           style={'maxHeight': '200px', 'overflowY': 'auto'})
                ], style={'backgroundColor': '#ffffff', 
                         'padding': '15px', 
                         'borderRadius': '5px',
                         'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
            ])

    def run_server(self, debug=True):
        """Run the application"""
        self.app.run_server(debug=debug)

if __name__ == '__main__':
    network_app = SpotifyNetworkApp()
    network_app.run_server()
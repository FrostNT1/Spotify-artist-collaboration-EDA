from dash import Dash, html, dcc, callback, Output, Input
import dash_cytoscape as cyto
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import ast


# Register the cose-bilkent layout
cyto.load_extra_layouts()

class SpotifyNetworkApp:
    def __init__(self):
        self.app = Dash(__name__)
        self.load_data()
        self.setup_network()
        self.setup_layout()
        self.setup_callbacks()

    def load_data(self):
        """Load and prepare cleaned data"""
        self.edges_df = pd.read_csv('../Data/edges.csv')
        self.nodes_df = pd.read_csv('../Data/nodes.csv')
        # Convert genres string to list
        self.nodes_df['genres'] = self.nodes_df['genres'].apply(lambda x: eval(x) if isinstance(x, str) else [])
        
        # Define top genres for classification
        self.top_genres = {
            'pop': ['pop', 'k-pop', 'j-pop', 'cantopop', 'mandopop', 'synthpop', 'electropop'],
            'rock': ['rock', 'hard rock', 'punk rock', 'alternative rock', 'indie rock', 'classic rock'],
            'hip-hop': ['hip hop', 'rap', 'trap', 'gangsta rap', 'alternative hip hop'],
            'edm': ['edm', 'electronic', 'house', 'techno', 'dubstep', 'trance'],
            'r&b': ['r&b', 'soul', 'neo soul', 'funk'],
            'country': ['country', 'country pop', 'outlaw country'],
            'jazz': ['jazz', 'bebop', 'swing', 'cool jazz', 'fusion'],
            'classical': ['classical', 'orchestral', 'chamber music', 'baroque', 'romantic', 'symphony'],
            'latin': ['latin', 'reggaeton', 'salsa', 'bachata', 'latin pop'],
            'reggae': ['reggae', 'dub', 'dancehall']
        }
        
        # Load and process the cleaned data
        self.top_artists_df = self.prepare_cleaned_data()

    def prepare_cleaned_data(self):
        """Prepare the cleaned dataset as shown in your analysis"""
        def map_to_top_genres(genre_str):
            if isinstance(genre_str, str):
                genre_list = [g.strip().strip("'") for g in genre_str.strip('[]').split(',')]
            elif isinstance(genre_str, list):
                genre_list = genre_str
            else:
                return []
            
            mapped_genres = set()
            for genre in genre_list:
                for top_genre, subgenres in self.top_genres.items():
                    if any(sub in genre.lower() for sub in subgenres):
                        mapped_genres.add(top_genre)
            return list(mapped_genres) if mapped_genres else []

        def expand_chart_hits(chart_hits_str):
            if pd.isna(chart_hits_str) or chart_hits_str == '[]':
                return []
            
            try:
                chart_hits = ast.literal_eval(chart_hits_str)
                expanded = []
                for entry in chart_hits:
                    country, hit_number = entry.replace("(", "").replace(")", "").split()
                    expanded.append({
                        'country_code': country,
                        'hit_number': int(hit_number)
                    })
                return expanded
            except Exception as e:
                print(f"Error processing chart hits: {e}")
                return []

        # Get top 100 artists by popularity
        top_artists = self.nodes_df.nlargest(100, 'popularity')
        
        # Apply genre mapping
        top_artists['cleaned_genres'] = top_artists['genres'].apply(map_to_top_genres)
        top_artists = top_artists[top_artists['cleaned_genres'].apply(len) > 0]
        top_artists['genre_count'] = top_artists['cleaned_genres'].apply(len)

        # Process chart hits
        expanded_hits = []
        for idx, row in top_artists.iterrows():
            chart_data = expand_chart_hits(row['chart_hits'])
            for hit in chart_data:
                expanded_hits.append({
                    'spotify_id': row['spotify_id'],  # Changed back to spotify_id
                    'country_code': hit['country_code'],
                    'hit_number': hit['hit_number']
                })

        expanded_hits_df = pd.DataFrame(expanded_hits)
        
        # Aggregate hits data
        grouped_hits = expanded_hits_df.groupby('spotify_id').agg(  # Changed back to spotify_id
            total_hits=('hit_number', 'sum'), 
            num_countries=('country_code', 'nunique')
        ).reset_index()

        # Merge and clean data
        top_artists = top_artists.merge(grouped_hits, on='spotify_id', how='left')  # Changed back to spotify_id
        top_artists = top_artists.dropna(subset=['total_hits', 'num_countries'])
        top_artists = top_artists.sort_values(by='popularity', ascending=False).head(100)

        # Remove outliers
        for column in ['followers', 'popularity']:
            Q1 = top_artists[column].quantile(0.025)
            Q3 = top_artists[column].quantile(0.975)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            top_artists = top_artists[
                (top_artists[column] >= lower_bound) & 
                (top_artists[column] <= upper_bound)
            ]

        # Process collaborations
        artist_collabs = pd.concat([self.edges_df['id_0'], self.edges_df['id_1']]).value_counts().reset_index()
        artist_collabs.columns = ['spotify_id', 'collab_count']  # Change 'id' to 'spotify_id'

        # Final dataset
        top_artists_with_collabs = top_artists.merge(artist_collabs, on='spotify_id', how='left')  # Change 'id' to 'spotify_id'
        top_artists_with_collabs['collab_count'] = top_artists_with_collabs['collab_count'].fillna(0)
        
        # Remove collaboration count outliers
        mean_collabs = top_artists_with_collabs['collab_count'].mean()
        std_collabs = top_artists_with_collabs['collab_count'].std()
        top_artists_with_collabs = top_artists_with_collabs[
            (top_artists_with_collabs['collab_count'] >= mean_collabs - 2*std_collabs) &
            (top_artists_with_collabs['collab_count'] <= mean_collabs + 2*std_collabs)
        ]

        return top_artists_with_collabs

    def setup_network(self):
        """Initialize network and calculate degrees"""
        self.G = nx.from_pandas_edgelist(self.edges_df, 'id_0', 'id_1')
        self.degrees = dict(self.G.degree())

    def get_top_artists(self, n=100):
        """Get top n artists by number of collaborations"""
        top_artists = sorted(self.degrees.items(), key=lambda x: x[1], reverse=True)[:n]
        return [artist[0] for artist in top_artists]

    def create_network_elements(self, artist_ids):
        """Create elements for cytoscape visualization"""
        elements = []
        
        # Add nodes
        for artist_id in artist_ids:
            artist_info = self.nodes_df[self.nodes_df['spotify_id'] == artist_id].iloc[0]  # Changed from id to spotify_id
            elements.append({
                'data': {
                    'id': artist_id,
                    'label': artist_info['name'],
                    'size': self.degrees[artist_id],
                    'followers': artist_info['followers'],
                    'popularity': artist_info['popularity'],
                    'genres': artist_info['genres'],
                    'name': artist_info['name']
                }
            })
        
        # Add edges
        for edge in self.G.edges():
            if edge[0] in artist_ids and edge[1] in artist_ids:
                elements.append({
                    'data': {
                        'source': edge[0],
                        'target': edge[1]
                    }
                })
        
        return elements

    def get_network_stylesheet(self):
        """Define network visualization style"""
        return [
            {
                'selector': 'node',
                'style': {
                    'label': 'data(label)',
                    'width': 'mapData(size, 0, 100, 20, 60)',
                    'height': 'mapData(size, 0, 100, 20, 60)',
                    'background-color': 'mapData(popularity, 0, 100, #FFA07A, #FF0000)',
                    'font-size': '8px',
                    'text-valign': 'center',
                    'text-halign': 'center',
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'width': 1,
                    'opacity': 0.5,
                    'line-color': '#888'
                }
            }
        ]

    def genre_collaboration_stats(self):
        """Calculate average collaborations by genre"""
        genre_stats = []
        for genre in self.top_genres.keys():
            genre_artists = self.top_artists_df[self.top_artists_df['cleaned_genres'].apply(lambda x: genre in x)]
            avg_collabs = genre_artists['collab_count'].mean() if not genre_artists.empty else 0
            genre_stats.append({'genre': genre, 'avg_collaborations': avg_collabs})
        return pd.DataFrame(genre_stats)

    def setup_layout(self):
        """Define app layout with multiple tabs"""
        self.app.layout = html.Div([
            html.H1("Spotify Artists Collaboration Network", 
                   style={'textAlign': 'center'}),
            
            dcc.Tabs([
                # Network View Tab
                dcc.Tab(label='Network Visualization', children=[
                    html.Div([
                        # Filters
                        html.Div([
                            html.Label("Filter by Genre:"),
                            dcc.Dropdown(
                                id='genre-filter',
                                options=[{'label': genre, 'value': genre} 
                                       for genre in self.top_genres.keys()],
                                multi=True
                            ),
                            html.Label("Minimum Popularity:"),
                            dcc.Input(
                                id='min-popularity',
                                type='number',
                                min=0,
                                max=100,
                                value=0
                            ),
                            html.Label("Maximum Popularity:"),
                            dcc.Input(
                                id='max-popularity',
                                type='number',
                                min=0,
                                max=100,
                                value=100
                            ),
                            html.Label("Number of Artists:"),
                            dcc.Slider(
                                id='num-artists-slider',
                                min=10,
                                max=100,
                                step=10,
                                value=50,
                                marks={i: str(i) for i in range(10, 101, 10)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                            html.Label("Layout:"),
                            dcc.Dropdown(
                                id='layout-dropdown',
                                options=[
                                    {'label': 'Cose-Bilkent', 'value': 'cose-bilkent'},
                                    {'label': 'Circle', 'value': 'circle'},
                                    {'label': 'Concentric', 'value': 'concentric'}
                                ],
                                value='cose-bilkent'
                            ),
                            html.Div(id='node-info', style={
                                'marginTop': '20px',
                                'padding': '10px',
                                'border': '1px solid #ddd',
                                'borderRadius': '5px'
                            })
                        ], style={'width': '20%', 'padding': '20px'}),
                        
                        # Network visualization
                        html.Div([
                            cyto.Cytoscape(
                                id='collaboration-network',
                                layout={'name': 'cose-bilkent'},
                                style={'width': '100%', 'height': '600px'},
                                elements=[]
                            )
                        ], style={'width': '80%'})
                    ], style={'display': 'flex'})
                ]),
                
                # Genre Clusters Tab
                dcc.Tab(label='Genre Clusters', children=[
                    html.Div([
                        html.Div([
                            html.H3("Genre Cluster Visualization", style={'textAlign': 'center'}),
                            html.P("This visualization shows artists grouped by their genres. Each cluster represents a genre.", 
                                   style={'textAlign': 'center'}),
                            cyto.Cytoscape(
                                id='genre-clusters',
                                layout={'name': 'concentric',  # Changed from circle to concentric for better visualization
                                       'minNodeSpacing': 50,
                                       'animate': True},
                                style={'width': '100%', 'height': '700px'},
                                elements=[],
                                stylesheet=[
                                    {
                                        'selector': 'node',
                                        'style': {
                                            'label': 'data(label)',
                                            'width': 'mapData(size, 0, 100, 20, 60)',
                                            'height': 'mapData(size, 0, 100, 20, 60)',
                                            'text-valign': 'center',
                                            'text-halign': 'center',
                                            'font-size': '10px',
                                            'background-opacity': 0.8
                                        }
                                    },
                                    {
                                        'selector': 'edge',
                                        'style': {
                                            'width': 1,
                                            'opacity': 0.5,
                                            'line-color': '#888'
                                        }
                                    },
                                    # Add specific styles for each genre
                                    {'selector': '.pop', 'style': {'background-color': '#FF69B4'}},
                                    {'selector': '.rock', 'style': {'background-color': '#CD5C5C'}},
                                    {'selector': '.hip-hop', 'style': {'background-color': '#4B0082'}},
                                    {'selector': '.edm', 'style': {'background-color': '#00CED1'}},
                                    {'selector': '.r&b', 'style': {'background-color': '#8B008B'}},
                                    {'selector': '.country', 'style': {'background-color': '#DAA520'}},
                                    {'selector': '.jazz', 'style': {'background-color': '#4682B4'}},
                                    {'selector': '.classical', 'style': {'background-color': '#800000'}},
                                    {'selector': '.latin', 'style': {'background-color': '#FF8C00'}},
                                    {'selector': '.reggae', 'style': {'background-color': '#228B22'}}
                                ]
                            ),
                            html.Div(id='genre-cluster-info', 
                                    style={
                                        'marginTop': '20px',
                                        'padding': '10px',
                                        'border': '1px solid #ddd',
                                        'borderRadius': '5px',
                                        'textAlign': 'center'
                                    })
                        ], style={'width': '100%', 'padding': '20px'})
                    ])
                ]),
                
                # Artist Rankings Tab
                dcc.Tab(label='Artist Rankings', children=[
                    html.Div([
                        dcc.Graph(id='collab-bubbles'),
                        dcc.Graph(id='genre-bubbles')
                    ])
                ]),
                
                # Collaboration Analysis Tab
                dcc.Tab(label='Collaboration Analysis', children=[
                    html.Div([
                        dcc.Graph(id='collab-country-scatter')
                    ])
                ]),
                
                # Popularity Analysis Tab
                dcc.Tab(label='Popularity Analysis', children=[
                    html.Div([
                        dcc.Graph(id='popularity-hits-scatter')
                    ])
                ])
            ])
        ])

    def setup_callbacks(self):
        """Set up callbacks for all tabs"""
        @self.app.callback(
            Output('collaboration-network', 'layout'),
            Input('layout-dropdown', 'value')
        )
        def update_layout(layout_name):
            return {
                'name': layout_name,
                'animate': True,
                'randomize': True,
                'nodeRepulsion': 8000,
                'idealEdgeLength': 100,
                'nodeOverlap': 20,
                'gravity': 0.5
            }

        @self.app.callback(
            Output('collaboration-network', 'elements'),
            [Input('num-artists-slider', 'value'),
             Input('min-popularity', 'value'),
             Input('max-popularity', 'value'),
             Input('genre-filter', 'value')]
        )
        def update_network(n_artists, min_pop, max_pop, selected_genres):
            filtered_artists = self.nodes_df[
                (self.nodes_df['popularity'] >= min_pop) &
                (self.nodes_df['popularity'] <= max_pop)
            ]
            
            if selected_genres:
                filtered_artists = filtered_artists[
                    filtered_artists['genres'].apply(
                        lambda x: any(any(subgenre in genre.lower() 
                                        for subgenre in self.top_genres[selected_genre])
                                    for selected_genre in selected_genres
                                    for genre in x)
                    )
                ]
            
            filtered_artists = filtered_artists['spotify_id'].tolist()  # Changed from id to spotify_id
            top_artists = [a for a in self.get_top_artists(n_artists) if a in filtered_artists]
            return self.create_network_elements(top_artists)

        @self.app.callback(
            Output('node-info', 'children'),
            Input('collaboration-network', 'tapNodeData')
        )
        def display_node_info(node_data):
            if not node_data:
                return "Click on a node to see artist details"
            
            return html.Div([
                html.H4(node_data['name']),
                html.P(f"Popularity: {node_data['popularity']}"),
                html.P(f"Followers: {node_data['followers']:,}"),
                html.P(f"Number of Collaborations: {node_data['size']}"),
                html.P("Genres: " + ", ".join(node_data['genres']))
            ])

        @self.app.callback(
            Output('genre-cluster-info', 'children'),
            Input('genre-clusters', 'tapNodeData')
        )
        def display_genre_cluster_info(node_data):
            if not node_data:
                return "Click on a node to see artist details"
            
            genre = node_data.get('genre', 'Unknown')
            label = node_data.get('label', 'Unknown')
            size = node_data.get('size', 0)
            
            return html.Div([
                html.H4(f"Artist: {label}"),
                html.P(f"Genre: {genre}"),
                html.P(f"Number of Collaborations: {size}")
            ])

        @self.app.callback(
            [Output('collab-bubbles', 'figure'),
             Output('genre-bubbles', 'figure')],
            Input('genre-filter', 'value')
        )
        def update_artist_rankings(selected_genres):
            top_20 = self.top_artists_df.nlargest(20, 'popularity')
            y_positions = list(range(len(top_20)))
            
            # Collaboration bubbles
            collab_fig = go.Figure()
            collab_fig.add_trace(go.Scatter(
                x=[0.5] * len(top_20),
                y=y_positions,
                mode='markers',
                marker=dict(
                    size=50,
                    color=top_20['collab_count'],
                    colorscale='Viridis',
                    showscale=True
                ),
                text=top_20['name'],
                hovertemplate='Artist: %{text}<br>Collaborations: %{marker.color}'
            ))
            collab_fig.update_layout(
                title='Top 20 Artists by Popularity (colored by collaboration count)',
                showlegend=False,
                xaxis_showgrid=False,
                xaxis_showticklabels=False
            )
            
            # Genre bubbles
            genre_fig = go.Figure()
            genre_fig.add_trace(go.Scatter(
                x=[0.5] * len(top_20),
                y=y_positions,
                mode='markers',
                marker=dict(
                    size=50,
                    color=top_20['genre_count'],
                    colorscale='Viridis',
                    showscale=True
                ),
                text=top_20['name'],
                hovertemplate='Artist: %{text}<br>Number of Genres: %{marker.color}'
            ))
            genre_fig.update_layout(
                title='Top 20 Artists by Popularity (colored by genre count)',
                showlegend=False,
                xaxis_showgrid=False,
                xaxis_showticklabels=False
            )
            
            return collab_fig, genre_fig

        @self.app.callback(
            Output('collab-country-scatter', 'figure'),
            Input('genre-filter', 'value')
        )
        def update_collab_country_analysis(selected_genres):
            fig = px.scatter(
                self.top_artists_df,
                x='collab_count',
                y='num_countries',
                title='Collaboration Count vs Number of Countries',
                hover_data=['name']
            )
            return fig

        @self.app.callback(
            Output('popularity-hits-scatter', 'figure'),
            Input('genre-filter', 'value')
        )
        def update_popularity_hits_analysis(selected_genres):
            fig = px.scatter(
                self.top_artists_df,
                x='popularity',
                y='total_hits',
                title='Popularity Score vs Total Chart Hits',
                hover_data=['name']
            )
            return fig

    def run_server(self, debug=True):
        """Run the application"""
        self.app.run_server(debug=debug)

if __name__ == '__main__':
    network_app = SpotifyNetworkApp()
    network_app.run_server()
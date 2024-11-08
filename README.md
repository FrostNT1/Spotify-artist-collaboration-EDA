# Spotify Artists Collaboration Network

An interactive visualization tool for exploring collaboration patterns between music artists on Spotify. This project analyzes and visualizes relationships between artists, their genres, popularity, and collaboration patterns.

## Features

- **2D Network Visualization**: Interactive network graph showing artist collaborations with filtering capabilities
- **3D Network View**: 3D visualization of the artist collaboration network
- **Genre Analysis**: Visual breakdown of artist genres and collaboration patterns
- **Popularity Analysis**: Insights into the relationship between artist popularity and collaborations
- **Chart Performance**: Analysis of chart performance across different countries

## Tech Stack

- **Python**: Core programming language
- **Dash**: Web application framework for visualization
- **Plotly**: Interactive plotting library
- **NetworkX**: Network/graph manipulation
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computations
- **Seaborn/Matplotlib**: Statistical data visualization

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Project Structure

```
.
├── Data/
│   ├── edges.csv         # Collaboration relationships
│   └── nodes.csv         # Artist information
├── Scripts/
│   ├── 2d-app.py        # 2D network visualization
│   └── 3d-app.py        # 3D network visualization
├── Experiments/         
│   ├── 00_importing-data.ipynb
│   ├── 01_visualizing-network.ipynb
│   ├── 02_data-cleaning.ipynb
│   ├── 03_genre-collaboration-rates.ipynb
│   ├── 04_popularity-collaborations.ipynb
│   └── 05_charthits.ipynb
└── requirements.txt
```

## Key Findings

1. **Genre Distribution**:
   - Pop and Hip-hop dominate the collaboration network
   - EDM artists show high collaboration rates but represent a smaller sample
   - Rock artists show relatively lower collaboration rates

2. **Popularity Correlation**:
   - Higher number of collaborations generally correlates with increased popularity
   - Artists with more collaborations tend to have more chart hits
   - Cross-genre collaborations are more common among highly popular artists

3. **Geographic Reach**:
   - Artists with more collaborations tend to chart in more countries
   - Latin artists show strong regional collaboration patterns
   - Hip-hop collaborations show strong presence in US charts

## Usage

### Running the 2D Visualization

The 2D visualization includes multiple tabs for different analyses:
```bash
python Scripts/2d-app.py
```

### Running the 3D Visualization

The 3D view provides an alternative perspective of the network:
```bash
python Scripts/3d-app.py
```

## Data Analysis

The project includes several Jupyter notebooks for detailed analysis:

1. **Data Import & Initial Processing**: Basic data loading and structure analysis
2. **Network Visualization**: Initial network visualization experiments
3. **Genre Analysis**: Detailed analysis of genre relationships and patterns
4. **Popularity Analysis**: Study of popularity metrics and their correlations
5. **Chart Performance**: Analysis of chart performance across different markets

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Acknowledgments

- Spotify Web API for providing the data
- NetworkX community for graph visualization tools
- Plotly team for interactive visualization capabilities
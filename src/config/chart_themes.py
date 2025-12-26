"""
Chart Theme Definitions
Provides predefined themes for the chart
"""

CHART_THEMES = {
    'Dark': {
        'name': 'Dark',
        'layout': {
            'backgroundColor': '#050505',
            'textColor': '#ffffff',
        },
        'grid': {
            'vertLines': {'color': '#222'},
            'horzLines': {'color': '#222'},
        },
        'candles': {
            'upColor': '#26a69a',
            'downColor': '#ef5350',
            'wickUpColor': '#26a69a',
            'wickDownColor': '#ef5350',
        },
        'priceScale': {
            'borderColor': '#444',
        },
        'timeScale': {
            'borderColor': '#444',
        },
    },
    'Light': {
        'name': 'Light',
        'layout': {
            'backgroundColor': '#ffffff',
            'textColor': '#000000',
        },
        'grid': {
            'vertLines': {'color': '#e0e0e0'},
            'horzLines': {'color': '#e0e0e0'},
        },
        'candles': {
            'upColor': '#26a69a',
            'downColor': '#ef5350',
            'wickUpColor': '#26a69a',
            'wickDownColor': '#ef5350',
        },
        'priceScale': {
            'borderColor': '#cccccc',
        },
        'timeScale': {
            'borderColor': '#cccccc',
        },
    },
    'Blue': {
        'name': 'Blue',
        'layout': {
            'backgroundColor': '#0a1929',
            'textColor': '#e3f2fd',
        },
        'grid': {
            'vertLines': {'color': '#1e3a5f'},
            'horzLines': {'color': '#1e3a5f'},
        },
        'candles': {
            'upColor': '#4caf50',
            'downColor': '#f44336',
            'wickUpColor': '#4caf50',
            'wickDownColor': '#f44336',
        },
        'priceScale': {
            'borderColor': '#2e4a6f',
        },
        'timeScale': {
            'borderColor': '#2e4a6f',
        },
    },
    'Green': {
        'name': 'Green',
        'layout': {
            'backgroundColor': '#0a1f0a',
            'textColor': '#e8f5e9',
        },
        'grid': {
            'vertLines': {'color': '#1f3f1f'},
            'horzLines': {'color': '#1f3f1f'},
        },
        'candles': {
            'upColor': '#66bb6a',
            'downColor': '#ef5350',
            'wickUpColor': '#66bb6a',
            'wickDownColor': '#ef5350',
        },
        'priceScale': {
            'borderColor': '#2f4f2f',
        },
        'timeScale': {
            'borderColor': '#2f4f2f',
        },
    },
}

def get_theme(theme_name: str) -> dict:
    """Get theme configuration by name"""
    return CHART_THEMES.get(theme_name, CHART_THEMES['Dark'])

def get_available_themes() -> list:
    """Get list of available theme names"""
    return list(CHART_THEMES.keys())


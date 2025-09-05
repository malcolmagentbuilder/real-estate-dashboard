import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="Real Estate Market Dashboard",
    page_icon="��",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .listing-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
</style>
""", unsafe_allow_html=True)

# Configuration - UPDATE THIS WITH YOUR ACTUAL WEBHOOK URL
N8N_WEBHOOK_URL = "https://n8n.srv883175.hstgr.cloud/webhook/saulestateagent"

@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_market_data():
    """Fetch data from n8n webhook"""
    try:
        response = requests.get(N8N_WEBHOOK_URL, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def process_listings_data(listings):
    """Process listings data for analysis"""
    if not listings:
        return pd.DataFrame()
    
    df = pd.DataFrame(listings)
    
    # Clean price data
    df['price_numeric'] = df['price'].str.replace(r'[$,+]', '', regex=True).astype(float, errors='ignore')
    df['bedrooms_numeric'] = pd.to_numeric(df['bedrooms'], errors='coerce')
    df['bathrooms_numeric'] = pd.to_numeric(df['bathrooms'], errors='coerce')
    df['sqft_numeric'] = pd.to_numeric(df['sqft'], errors='coerce')
    
    # Extract neighborhood from address
    df['neighborhood'] = df['address'].str.extract(r'([^,]+),')[0].str.strip()
    
    return df

def create_price_distribution_chart(df):
    """Create price distribution chart"""
    if df.empty or 'price_numeric' not in df.columns:
        return None
    
    fig = px.histogram(
        df, 
        x='price_numeric', 
        nbins=20,
        title="Price Distribution",
        labels={'price_numeric': 'Price ($)', 'count': 'Number of Listings'}
    )
    fig.update_layout(
        xaxis_title="Price ($)",
        yaxis_title="Number of Listings",
        showlegend=False
    )
    return fig

def create_bedroom_analysis_chart(df):
    """Create bedroom analysis chart"""
    if df.empty or 'bedrooms_numeric' not in df.columns:
        return None
    
    bedroom_counts = df['bedrooms_numeric'].value_counts().sort_index()
    
    fig = px.bar(
        x=bedroom_counts.index,
        y=bedroom_counts.values,
        title="Listings by Number of Bedrooms",
        labels={'x': 'Bedrooms', 'y': 'Number of Listings'}
    )
    fig.update_layout(showlegend=False)
    return fig

def create_neighborhood_chart(df):
    """Create neighborhood analysis chart"""
    if df.empty or 'neighborhood' not in df.columns:
        return None
    
    neighborhood_stats = df.groupby('neighborhood').agg({
        'price_numeric': ['mean', 'count']
    }).round(0)
    
    neighborhood_stats.columns = ['avg_price', 'count']
    neighborhood_stats = neighborhood_stats[neighborhood_stats['count'] >= 3].head(10)
    
    fig = px.bar(
        neighborhood_stats,
        x=neighborhood_stats.index,
        y='avg_price',
        title="Average Price by Neighborhood (min 3 listings)",
        labels={'x': 'Neighborhood', 'avg_price': 'Average Price ($)'}
    )
    fig.update_layout(showlegend=False)
    return fig

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>�� Real Estate Market Dashboard</h1>
        <p>AI-Powered Market Analysis & Property Insights</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Controls")
        
        # Refresh button
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Filters
        st.header("🔍 Filters")
        
        # Get data for filters
        data = fetch_market_data()
        if data and data.get('listings'):
            df = process_listings_data(data['listings'])
            
            if not df.empty:
                # Price range filter
                price_range = st.slider(
                    "Price Range ($)",
                    min_value=int(df['price_numeric'].min()) if 'price_numeric' in df.columns else 0,
                    max_value=int(df['price_numeric'].max()) if 'price_numeric' in df.columns else 10000,
                    value=(int(df['price_numeric'].min()) if 'price_numeric' in df.columns else 0, 
                           int(df['price_numeric'].max()) if 'price_numeric' in df.columns else 10000)
                )
                
                # Bedroom filter
                bedrooms = st.multiselect(
                    "Bedrooms",
                    options=sorted(df['bedrooms_numeric'].dropna().unique()),
                    default=sorted(df['bedrooms_numeric'].dropna().unique())
                )
                
                # Property type filter
                property_types = st.multiselect(
                    "Property Type",
                    options=df['property_type'].dropna().unique(),
                    default=df['property_type'].dropna().unique()
                )
        else:
            price_range = (0, 10000)
            bedrooms = []
            property_types = []
    
    # Main content
    if data is None:
        st.error("❌ Unable to fetch data. Please check your webhook URL and try again.")
        st.stop()
    
    # Key Metrics
    st.header("�� Market Overview")
    
    if data.get('listings'):
        df = process_listings_data(data['listings'])
        
        if not df.empty:
            # Apply filters
            if 'price_numeric' in df.columns:
                df_filtered = df[
                    (df['price_numeric'] >= price_range[0]) & 
                    (df['price_numeric'] <= price_range[1])
                ]
            else:
                df_filtered = df
                
            if bedrooms:
                df_filtered = df_filtered[df_filtered['bedrooms_numeric'].isin(bedrooms)]
            
            if property_types:
                df_filtered = df_filtered[df_filtered['property_type'].isin(property_types)]
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Listings",
                    len(df_filtered),
                    delta=f"{len(df_filtered) - len(df)}" if len(df_filtered) != len(df) else None
                )
            
            with col2:
                avg_price = df_filtered['price_numeric'].mean() if 'price_numeric' in df_filtered.columns else 0
                st.metric(
                    "Average Price",
                    f"${avg_price:,.0f}" if avg_price > 0 else "N/A"
                )
            
            with col3:
                avg_bedrooms = df_filtered['bedrooms_numeric'].mean() if 'bedrooms_numeric' in df_filtered.columns else 0
                st.metric(
                    "Avg Bedrooms",
                    f"{avg_bedrooms:.1f}" if avg_bedrooms > 0 else "N/A"
                )
            
            with col4:
                price_range_str = f"${df_filtered['price_numeric'].min():,.0f} - ${df_filtered['price_numeric'].max():,.0f}" if 'price_numeric' in df_filtered.columns else "N/A"
                st.metric(
                    "Price Range",
                    price_range_str
                )
            
            # Charts
            st.header("�� Market Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                price_chart = create_price_distribution_chart(df_filtered)
                if price_chart:
                    st.plotly_chart(price_chart, use_container_width=True)
            
            with col2:
                bedroom_chart = create_bedroom_analysis_chart(df_filtered)
                if bedroom_chart:
                    st.plotly_chart(bedroom_chart, use_container_width=True)
            
            # Neighborhood analysis
            neighborhood_chart = create_neighborhood_chart(df_filtered)
            if neighborhood_chart:
                st.plotly_chart(neighborhood_chart, use_container_width=True)
            
            # Listings table
            st.header("��️ Property Listings")
            
            # Display options
            display_col1, display_col2 = st.columns([3, 1])
            with display_col1:
                show_count = st.slider("Show listings", 1, len(df_filtered), min(20, len(df_filtered)))
            with display_col2:
                sort_by = st.selectbox("Sort by", ["price_numeric", "bedrooms_numeric", "address"])
            
            # Sort and display
            if sort_by in df_filtered.columns:
                df_display = df_filtered.sort_values(sort_by, ascending=False).head(show_count)
            else:
                df_display = df_filtered.head(show_count)
            
            # Display listings
            for idx, listing in df_display.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="listing-card">
                        <h4>{listing['address']}</h4>
                        <p><strong>Price:</strong> {listing['price']}</p>
                        <p><strong>Details:</strong> {listing['bedrooms']} bed • {listing['bathrooms'] or 'N/A'} bath • {listing['property_type'] or 'N/A'}</p>
                        {f"<p><strong>Square Feet:</strong> {listing['sqft']}</p>" if listing['sqft'] else ""}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Data export
            st.header("📥 Export Data")
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"real_estate_listings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No listings data available")
    else:
        st.warning("No listings found in the data")
    
    # AI Analysis
    if data.get('analysis'):
        st.header("�� AI Market Analysis")
        st.markdown(f"""
        <div class="metric-card">
            <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace;">{data['analysis']}</pre>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import requests

# gpt css
st.markdown("""
<style>
.pulsing-success {
    animation: pulse 1.5s ease-in-out infinite alternate;
}

@keyframes pulse {
    0% {
        transform: scale(1);
        opacity: 1;
    }
    100% {
        transform: scale(1.05);
        opacity: 0.8;
    }
}
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1:
    st.title("RFP Analyzer")
with col2:
    st.image("ruckus_dog.png", width=80)

# get data and convert to dataframe
try:
    data = requests.get("https://www.governmentnavigator.com/api/bidfeed?email=marcelo.molinari@commscope.com&token=22c7f7254d4202af5c73bd9108c527ed", timeout=10).json()
    df = pd.DataFrame(data.get('bids', data) if isinstance(data, dict) else data)
    
    # score and filter based on if open and location match
    df['Status Open?'] = df.get('opportunity_status', '').astype(str).str.lower().str.strip() == 'open'
    df['Location Match?'] = df.get('jurisdiction_title', '').astype(str).str.lower().str.strip().isin(['california', 'sunnyvale', 'claremont'])
    df['Good Fit'] = df['Status Open?'] & df['Location Match?']
    
    # define ruckus/networking keywords
    networking_keywords = [
        'wifi', 'wi-fi', 'wireless', 'wlan', 'access point', 'access points', 'ap',
        'network', 'networking', 'ethernet', 'switch', 'switches', 'router', 'routers',
        'iot', 'internet of things', 'controller', 'controllers', 'wlan controller',
        'smartzone', 'cloud wifi', 'enterprise network', 'lan', 'wireless lan',
        'connectivity', 'infrastructure', 'broadband', 'fiber', 'cable', 'internet',
        'ruckus', 'commscope', 'wireless infrastructure', 'network infrastructure',
        'mesh', 'meshed', 'outdoor wireless', 'indoor wireless', 'high density',
        'enterprise wireless', 'campus network', 'campus networking', 'it infrastructure',
        'network security', 'network management', 'centralized management',
        'network analytics', 'wireless analytics', 'cloudpath', 'assurance',
        'wireless bridge', 'point to point', 'point to multipoint', 'backhaul'
    ]
    
    # check for networking keywords in title and description
    def has_networking_keywords(row):
        text_fields = []
        if 'title' in row and pd.notna(row['title']):
            text_fields.append(str(row['title']).lower())
        if 'description' in row and pd.notna(row['description']):
            text_fields.append(str(row['description']).lower())
        if 'short_description' in row and pd.notna(row['short_description']):
            text_fields.append(str(row['short_description']).lower())
        
        combined_text = ' '.join(text_fields)
        return any(keyword in combined_text for keyword in networking_keywords)
    
    df['Networking Keywords Match?'] = df.apply(has_networking_keywords, axis=1)
    
    # display dataframe in table format
    cols = [c for c in ['id', 'title', 'type', 'due_date', 'opportunity_status', 'jurisdiction_title'] if c in df.columns] + ['Status Open?', 'Location Match?', 'Good Fit']
    st.subheader("All RFPs")
    st.dataframe(df[cols])
    
    st.subheader("✅Bids to Be Pursued")
    good_fit_bids = df[df['Good Fit']]
    if len(good_fit_bids) > 0:
        st.balloons()
        st.markdown(f'<div class="pulsing-success">🎉 Found {len(good_fit_bids)} great opportunities! 🎉</div>', unsafe_allow_html=True)
    st.dataframe(good_fit_bids[cols])
    
    st.subheader("🔎 Bids Matching Core Networking Keywords")
    networking_cols = cols + ['Networking Keywords Match?']
    networking_bids = df[df['Networking Keywords Match?']]
    if len(networking_bids) > 0:
        st.balloons()
        st.markdown(f'<div class="pulsing-success">🔍 Found {len(networking_bids)} networking opportunities! 🔍</div>', unsafe_allow_html=True)
    st.dataframe(networking_bids[networking_cols])
    
except Exception as e:
    st.error(f"Error: {e}")
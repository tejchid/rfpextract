#test change

import streamlit as st
import pandas as pd
import requests

st.title("RFP Analyzer")

# get data and convert to dataframe
try:
    data = requests.get("https://www.governmentnavigator.com/api/bidfeed?email=marcelo.molinari@commscope.com&token=22c7f7254d4202af5c73bd9108c527ed", timeout=10).json()
    df = pd.DataFrame(data.get('bids', data) if isinstance(data, dict) else data)
    
    # score and filter based on if open and location match
    df['Status Open?'] = df.get('opportunity_status', '').astype(str).str.lower().str.strip() == 'open'
    df['Location Match?'] = df.get('jurisdiction_title', '').astype(str).str.lower().str.strip().isin(['california', 'sunnyvale', 'claremont'])
    df['Good Fit'] = df['Status Open?'] & df['Location Match?']
    
    # display dataframe in table format
    cols = [c for c in ['id', 'title', 'type', 'due_date', 'opportunity_status', 'jurisdiction_title'] if c in df.columns] + ['Status Open?', 'Location Match?', 'Good Fit']
    st.subheader("All RFPs")
    st.dataframe(df[cols])
    st.subheader("✅Bids to Be Pursued")
    st.dataframe(df[df['Good Fit']][cols])
    
except Exception as e:
    st.error(f"Error: {e}")
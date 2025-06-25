import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import PyPDF2
import docx
import io
from urllib.parse import urljoin, urlparse
import time

# Page setup
st.set_page_config(page_title="Industry NAV RFP Analyzer", layout="wide")

# Clean CSS
st.markdown("""
<style>
.stApp {
    background-color: #f8f9fa;
}
.stSidebar {
    background-color: #ffffff;
    border-right: 1px solid #e9ecef;
}
.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.pulsing-success {
    animation: pulse 1.5s ease-in-out infinite alternate;
    background: linear-gradient(90deg, #28a745, #20c997);
    color: white;
    padding: 12px;
    border-radius: 8px;
    text-align: center;
    font-weight: 600;
    margin: 1rem 0;
}
@keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    100% { transform: scale(1.02); opacity: 0.9; }
}
.stDataFrame {
    border: 1px solid #e9ecef;
    border-radius: 8px;
    overflow: hidden;
}
h1, h2, h3 {
    color: #212529;
    font-weight: 600;
}
.stMetric {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# Sidebar filters
st.sidebar.header("Filters")
locations = st.sidebar.multiselect(
    "Target Locations", 
    ['california', 'sunnyvale', 'claremont', 'texas', 'florida'],
    default=['california', 'sunnyvale', 'claremont']
)
show_expired = st.sidebar.checkbox("Show Expired", value=False)
search_documents = st.sidebar.checkbox("Search Inside Documents", value=True, help="Downloads and searches PDF/Word documents for keywords (slower but more thorough)")

# Ruckus dog image in sidebar
try:
    st.sidebar.image("ruckus_battle_card.png", width=250)
except:
    st.sidebar.write("🐕 Ruckus Dog")

# Header
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🎯 Industry NAV RFP Analyzer")
with col2:
    st.write("")  # Empty space since dog is now in sidebar

# Keywords for networking
networking_keywords = [
    'wifi', 'wi-fi', 'wireless', 'wlan', 'access point', 'network', 'networking', 
    'ethernet', 'switch', 'router', 'iot', 'controller', 'infrastructure', 
    'ruckus', 'commscope', 'mesh', 'enterprise wireless', 'cybersecurity'
]

# Functions
def extract_text_from_pdf(file_content):
    """Extract text from PDF content"""
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + " "
        return text.lower()
    except:
        return ""

def extract_text_from_docx(file_content):
    """Extract text from Word document content"""
    try:
        doc_file = io.BytesIO(file_content)
        doc = docx.Document(doc_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + " "
        return text.lower()
    except:
        return ""

def download_and_search_documents(row, keywords):
    """Download and search documents for keywords"""
    if not search_documents:
        return False, ""
    
    # Look for document URLs in the row
    doc_urls = []
    for field in ['document_url', 'attachment_url', 'file_url', 'documents']:
        if field in row and pd.notna(row[field]):
            url = str(row[field])
            if url.startswith('http'):
                doc_urls.append(url)
    
    found_keywords = []
    
    for url in doc_urls[:3]:  # Limit to first 3 documents to avoid timeout
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                
                if 'pdf' in content_type:
                    text = extract_text_from_pdf(response.content)
                elif 'word' in content_type or 'document' in content_type:
                    text = extract_text_from_docx(response.content)
                else:
                    continue
                
                # Check for keywords in document content
                for keyword in keywords:
                    if keyword in text:
                        found_keywords.append(keyword)
                        
        except:
            continue
            
        time.sleep(0.1)  # Small delay to be respectful
    
    return len(found_keywords) > 0, ", ".join(found_keywords)

def has_networking_keywords(row):
    # Search in title/description (fast)
    text = ' '.join([
        str(row.get('title', '')).lower(),
        str(row.get('description', '')).lower(),
        str(row.get('short_description', '')).lower()
    ])
    title_match = any(keyword in text for keyword in networking_keywords)
    
    # Search in documents (slower but thorough)
    doc_match, found_keywords = download_and_search_documents(row, networking_keywords)
    
    return title_match or doc_match

def calculate_priority_score(row):
    score = 0
    # Due date urgency
    try:
        due_date = pd.to_datetime(row.get('due_date'))
        days_until_due = (due_date - datetime.now()).days
        if days_until_due <= 7: score += 30
        elif days_until_due <= 14: score += 20
        elif days_until_due <= 30: score += 10
    except: pass
    
    # Keyword matches
    text = ' '.join([str(row.get(f, '')).lower() for f in ['title', 'description', 'short_description']])
    score += sum(5 for keyword in networking_keywords if keyword in text)
    return score

# Load data
try:
    with st.spinner("Loading data..."):
        url = "https://www.governmentnavigator.com/api/bidfeed?email=marcelo.molinari@commscope.com&token=22c7f7254d4202af5c73bd9108c527ed"
        data = requests.get(url, timeout=15).json()
        df = pd.DataFrame(data.get('bids', data) if isinstance(data, dict) else data)
    
    # Process data
    with st.spinner("Processing RFP data and searching documents..." if search_documents else "Processing RFP data..."):
        df['Status Open?'] = df.get('opportunity_status', '').astype(str).str.lower() == 'open'
        df['Location Match?'] = df.get('jurisdiction_title', '').astype(str).str.lower().isin([l.lower() for l in locations])
        df['Good Fit'] = df['Status Open?'] & df['Location Match?']
        
        if search_documents:
            st.info("🔍 Searching inside documents for networking keywords... This may take a few minutes.")
        
        df['Networking Keywords Match?'] = df.apply(has_networking_keywords, axis=1)
        df['Priority Score'] = df.apply(calculate_priority_score, axis=1)
        df['Priority Level'] = df['Priority Score'].apply(lambda x: 'High' if x >= 40 else 'Medium' if x >= 20 else 'Low')
    
    # Apply filters
    if not show_expired:
        df = df[df['Status Open?'] == True]
    df = df.sort_values('Priority Score', ascending=False)
    
    # Key metrics
    st.subheader("📈 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total RFPs", len(df))
    with col2: st.metric("Good Fits", len(df[df['Good Fit']]))
    with col3: st.metric("Networking Matches", len(df[df['Networking Keywords Match?']]))
    with col4: st.metric("High Priority", len(df[df['Priority Level'] == 'High']))
    

    
    # Display columns
    cols = [c for c in ['id', 'title', 'type', 'due_date', 'opportunity_status', 'jurisdiction_title'] if c in df.columns]
    analysis_cols = ['Status Open?', 'Location Match?', 'Good Fit', 'Priority Level', 'Priority Score']
    
    # High Priority section
    st.subheader("🚨 High Priority Opportunities")
    high_priority = df[df['Priority Level'] == 'High']
    if len(high_priority) > 0:
        st.success(f"Found {len(high_priority)} high priority opportunities!")
        st.dataframe(high_priority[cols + analysis_cols], use_container_width=True)
    else:
        st.info("No high priority opportunities found.")
    
    # Good Fits section
    st.subheader("✅ Best Fit Opportunities")
    good_fits = df[df['Good Fit']]
    if len(good_fits) > 0:
        st.balloons()
        st.markdown(f'<div class="pulsing-success">🎉 Found {len(good_fits)} great opportunities! 🎉</div>', unsafe_allow_html=True)
        st.dataframe(good_fits[cols + analysis_cols], use_container_width=True)
    else:
        st.info("No good fits found.")
    
    # Networking Matches section
    st.subheader("🔍 Networking Technology Matches")
    networking = df[df['Networking Keywords Match?']]
    if len(networking) > 0:
        st.markdown(f'<div class="pulsing-success">🔍 Found {len(networking)} networking opportunities! 🔍</div>', unsafe_allow_html=True)
        st.dataframe(networking[cols + analysis_cols + ['Networking Keywords Match?']], use_container_width=True)
    else:
        st.info("No networking matches found.")
    
    # All RFPs (expandable)
    with st.expander("📋 All RFPs"):
        st.dataframe(df[cols + analysis_cols], use_container_width=True)
    
    # Export
    st.subheader("📥 Export")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Download All (CSV)", df.to_csv(index=False), f"rfp_data_{datetime.now().strftime('%Y%m%d')}.csv")
    with col2:
        if len(good_fits) > 0:
            st.download_button("Download Good Fits (CSV)", good_fits.to_csv(index=False), f"good_fits_{datetime.now().strftime('%Y%m%d')}.csv")

except Exception as e:
    st.error(f"Error: {str(e)}")
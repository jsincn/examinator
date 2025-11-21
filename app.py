import streamlit as st

# Configure page
st.set_page_config(layout="wide")

# Create columns for layout
left_col, right_col = st.columns([1, 2])

# Left column - file upload
with left_col:
    st.header("Upload File")
    uploaded_file = st.file_uploader("Choose a file", type=["csv", "txt", "pdf"])
    
    if uploaded_file is not None:
        st.success(f"Uploaded: {uploaded_file.name}")

# Right column - main content area
with right_col:
    st.header("Main Content")
    if uploaded_file is not None:
        st.write("File uploaded successfully!")
        # Add your file processing logic here
    else:
        st.info("Please upload a file to get started")
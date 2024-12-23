import streamlit as st
from streamlit_tags import st_tags_sidebar
import pandas as pd
import json
from datetime import datetime
from scraper import save_raw_data, format_data, save_formatted_data, calculate_price, html_to_markdown_with_readability, create_dynamic_listing_model, create_listings_container_model

# Initialize Streamlit app
st.set_page_config(page_title="GEN-AI SCRAPER")
st.title("GEN-AI SCRAPER")

# Sidebar components
st.sidebar.title("Settings")
model_selection = st.sidebar.selectbox("Model Selection", options=["gpt-4o-mini", "gpt-4o-2024-08-06"], index=0)

url_input = st.sidebar.text_input("Enter URL")


# Tags input specifically in the sidebar
tags = st.sidebar.empty()  # Create an empty placeholder in the sidebar
tags = st_tags_sidebar(
    label='Describe what to extract with natural language:',
    text='Press enter to add a tag',
    # value=[],  # Default values if any
    # key='tags_input'
)

st.sidebar.markdown("---")

# Process tags into a list
fields = tags

# Initialize variables to store token and cost information
input_tokens = output_tokens = total_cost = 0  # Default values

# Define the scraping function
def perform_scrape():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    markdown, screenshot_url, title, status_code = html_to_markdown_with_readability(url_input)
    save_raw_data(markdown, timestamp)
    
    if status_code == 200:
        st.write(f"✅ Successfully Crawled {url_input}")
        if screenshot_url:
            st.image(screenshot_url, caption="Screenshot of the page")
    else:
        st.write(f'{url_input} doesn\'t return 200. Please double check.')

    # Pydantic
    DynamicListingModel = create_dynamic_listing_model(fields)
    DynamicListingsContainer = create_listings_container_model(DynamicListingModel)

    # LLM
    formatted_data, prompt_tokens, completion_tokens = format_data(markdown, DynamicListingsContainer, model_selection)
    formatted_data_text = json.dumps(formatted_data.dict())

    # Cost Calculation
    input_tokens, output_tokens, total_cost = calculate_price(prompt_tokens, completion_tokens, model=model_selection)
    df = save_formatted_data(formatted_data, timestamp)

    return df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp, screenshot_url, title, status_code

# Handling button press for scraping
if 'perform_scrape' not in st.session_state:
    st.session_state['perform_scrape'] = False

if st.sidebar.button("Scrape"):
    with st.spinner('Please wait... Data is being scraped.'):
        st.session_state['results'] = perform_scrape()
        st.session_state['perform_scrape'] = True

if st.session_state.get('perform_scrape'):
    df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp, screenshot_url, title, status_code = st.session_state['results']
    # Display the DataFrame and other data
    st.write("Scraped Data:", df)
    st.sidebar.markdown("## Token Usage")
    st.sidebar.markdown(f"**Input Tokens:** {input_tokens}")
    st.sidebar.markdown(f"**Output Tokens:** {output_tokens}")
    st.sidebar.markdown(f"**Total Cost:** :green-background[***${total_cost:.4f}***]")

    # Create columns for download buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("Download JSON", data=json.dumps(formatted_data.dict(), indent=4), file_name=f"{timestamp}_data.json")
    with col2:
        # Convert formatted data to a dictionary if it's not already (assuming it has a .dict() method)
        data_dict = formatted_data.dict() if hasattr(formatted_data, 'dict') else formatted_data
        
        # Access the data under the dynamic key
        first_key = next(iter(data_dict))  # Safely get the first key
        main_data = data_dict[first_key]   # Access data using this key

        # Create DataFrame from the data
        df = pd.DataFrame(main_data)

        st.download_button("Download CSV", data=df.to_csv(index=False), file_name=f"{timestamp}_data.csv")
    with col3:
        st.download_button("Download Markdown", data=markdown, file_name=f"{timestamp}_data.md")

# Ensure that these UI components are persistent and don't rely on re-running the scrape function
if 'results' in st.session_state:
    df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp, screenshot_url, title, status_code = st.session_state['results']

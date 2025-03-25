import os
import streamlit as st
import requests
import openai
from dotenv import load_dotenv
import altair as alt
import pandas as pd

# Load environment variables from .env file
load_dotenv()

# Spotify API credentials from .env file
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# OpenAI API key from Streamlit secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in Streamlit secrets.")
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise ValueError("Spotify credentials are not set in .env file.")

# --- Spotify Functions ---

def get_spotify_access_token():
    """Gets an access token using Spotify's Client Credentials flow."""
    url = "https://accounts.spotify.com/api/token"
    data = {"grant_type": "client_credentials"}
    response = requests.post(url, data=data, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        st.error(f"Failed to get access token: {response.status_code}, {response.json()}")
        return None

def search_tracks(track_name, access_token):
    """Searches for tracks on Spotify by track name."""
    url = f"https://api.spotify.com/v1/search?q={track_name}&type=track&limit=5"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("tracks", {}).get("items", [])
    else:
        st.error(f"Error searching for track: {response.status_code}, {response.json()}")
        return []

# --- Web Search Placeholder ---
def search_web(query):
    """
    Placeholder function to simulate a web search.
    Replace this with an actual web search API call.
    """
    dummy_context = (
        f"Recent articles, reviews, and social media posts suggest that '{query}' is characterized by "
        "vibrant energy, catchy hooks, and an urban club vibe. Listeners describe it as a blend of pop "
        "and electronic music, ideal for festival and lounge settings."
    )
    return dummy_context

# --- Data Aggregation ---
def aggregate_track_context(track):
    """
    Aggregates Spotify track metadata and web search context.
    """
    track_name = track.get("name", "Unknown Track")
    artist_name = track["artists"][0].get("name", "Unknown Artist") if track.get("artists") else "Unknown Artist"
    album_name = track.get("album", {}).get("name", "Unknown Album")
    popularity = track.get("popularity", 0)
    
    # Build query for web search using track name and artist.
    search_query = f"{track_name} {artist_name} review"
    web_context = search_web(search_query)
    
    aggregated_context = (
        f"Track: {track_name}\n"
        f"Artist: {artist_name}\n"
        f"Album: {album_name}\n"
        f"Popularity: {popularity}\n\n"
        f"Web Context: {web_context}"
    )
    return aggregated_context

# --- LLM Synthesis using the new ChatCompletion API ---
def generate_llm_suggestions(aggregated_context):
    """
    Uses the GPT-o3-mini model (or another supported model) to generate a creative list of venue suggestions 
    and a track summary based on the aggregated context.
    """
    prompt = (
        "Based on the following information about a track and its web context, provide a creative list "
        "of 3-4 venues or settings where a DJ might play this track. Explain briefly why each setting "
        "suits the track. Also, give a brief summary of the track's vibe.\n\n"
        f"{aggregated_context}"
    )
    try:
        response = openai.ChatCompletion.create(
            model="o3-mini-2025-01-31",  # Change this to your desired model if needed.
            messages=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_completion_tokens=250
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        st.error(f"Error generating LLM suggestions: {str(e)}")
        return None

# --- Visual Analytics: Simple Popularity Chart ---
def display_popularity_chart(tracks):
    """
    Displays a simple bar chart of track popularity.
    """
    data = [{"Track": t["name"], "Popularity": t.get("popularity", 0)} for t in tracks]
    df = pd.DataFrame(data)
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Track:N", sort='-y'),
        y="Popularity:Q",
        tooltip=["Track", "Popularity"]
    ).properties(width=600, height=400)
    st.altair_chart(chart)

# --- Main Streamlit App ---
def main():
    st.set_page_config(page_title="Holistic Track Insight Dashboard", layout="wide")
    st.title("🎶 Holistic Track Insight Dashboard")
    st.markdown(
        """
        This app aggregates Spotify track data with web context and leverages an LLM to provide a multi-dimensional
        understanding of a track. You’ll get insights into the track’s vibe, creative venue suggestions, and visual analytics.
        """
    )
    
    track_input = st.text_input("Enter a Spotify Track Name", "")
    if track_input:
        progress = st.progress(0)
        progress.progress(10)
        
        access_token = get_spotify_access_token()
        if not access_token:
            st.error("Spotify authentication failed.")
            return
        
        progress.progress(30)
        tracks = search_tracks(track_input, access_token)
        if not tracks:
            st.warning("No tracks found.")
            return
        
        # Let user select a track from search results.
        track_options = {f"{t['name']} by {t['artists'][0]['name']}": t for t in tracks}
        selected_option = st.selectbox("Select the correct track", list(track_options.keys()))
        selected_track = track_options[selected_option]
        st.success(f"Selected: {selected_option}")
        progress.progress(50)
        
        # Aggregate track context.
        aggregated_context = aggregate_track_context(selected_track)
        st.markdown("**Aggregated Track Context:**")
        st.code(aggregated_context)
        progress.progress(65)
        
        # Generate LLM suggestions.
        suggestions = generate_llm_suggestions(aggregated_context)
        if suggestions:
            st.subheader("LLM-Generated Insights & Venue Suggestions")
            st.markdown(suggestions)
        else:
            st.error("Failed to generate suggestions.")
        progress.progress(80)
        
        # Display a simple popularity chart for the search results.
        st.subheader("Track Popularity Comparison")
        display_popularity_chart(tracks)
        progress.progress(100)

if __name__ == "__main__":
    main()

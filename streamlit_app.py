import os
import streamlit as st
import requests
from dotenv import load_dotenv
import altair as alt
import pandas as pd
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Spotify API credentials from .env file
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# OpenAI API key from Streamlit secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in Streamlit secrets.")
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise ValueError("Spotify credentials are not set in .env file.")

# Instantiate the OpenAI client using the new SDK
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Spotify Functions ---

def get_spotify_access_token():
    """Gets an access token using Spotify's Client Credentials flow."""
    url = "https://accounts.spotify.com/api/token"
    data = {"grant_type": "client_credentials"}
    response = requests.post(url, data=data, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        st.error(f"Failed to get access token: {response.status_code}, {response.text}")
        return None

def search_tracks(track_name, access_token):
    """Searches for tracks on Spotify by track name."""
    url = f"https://api.spotify.com/v1/search?q={track_name}&type=track&limit=5"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("tracks", {}).get("items", [])
    else:
        st.error(f"Error searching for track: {response.status_code}, {response.text}")
        return []

def get_artist_top_tracks(artist_id, access_token, country="US"):
    """Retrieves the top tracks for a given artist."""
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country={country}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("tracks", [])
    else:
        st.error(f"Error retrieving artist top tracks: {response.status_code}, {response.text}")
        return []

def get_artist_albums(artist_id, access_token, include_groups="album,single", limit=10, market="US"):
    """Retrieves albums for a given artist."""
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups={include_groups}&limit={limit}&market={market}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        st.error(f"Error retrieving artist albums: {response.status_code}, {response.text}")
        return []

def get_album_tracks(album_id, access_token, limit=50):
    """Retrieves tracks for a given album."""
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks?limit={limit}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        st.error(f"Error retrieving album tracks: {response.status_code}, {response.text}")
        return []

def get_recommendations(track_id, access_token, limit=5):
    """Retrieves track recommendations based on a seed track."""
    url = f"https://api.spotify.com/v1/recommendations?seed_tracks={track_id}&limit={limit}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if not response.text or "No similar track recommendations found" in response.text:
        st.warning("No similar track recommendations found.")
        return []
    try:
        data = response.json()
    except Exception as e:
        st.error(f"Error parsing JSON for recommendations: {str(e)}. Raw response: {response.text}")
        return []
    if response.status_code == 200:
        return data.get("tracks", [])
    else:
        st.error(f"Error retrieving recommendations: {response.status_code}, {data}")
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

# --- LLM Synthesis using Streaming with new SDK ---
def generate_llm_suggestions_stream(aggregated_context):
    """
    Uses the gpt-3.5-turbo model via the new OpenAI SDK to generate a creative list of venue suggestions
    and a track summary, streaming the response.
    """
    prompt = (
        "Based on the following information about a track and its web context, provide a creative list "
        "of 3-4 venues or settings where a DJ might play this track. Explain briefly why each setting "
        "suits the track. Also, give a brief summary of the track's vibe.\n\n"
        f"{aggregated_context}"
    )
    try:
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_completion_tokens=250,
            stream=True
        )
        full_text = ""
        placeholder = st.empty()
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full_text += delta.content
                placeholder.text(full_text)
        return full_text
    except Exception as e:
        st.error(f"Error streaming LLM suggestions: {str(e)}")
        return None

# --- Visual Analytics: Simple Popularity Chart ---
def display_popularity_chart(tracks, title="Track Popularity"):
    """
    Displays a simple bar chart of track popularity.
    """
    data = [{"Track": t["name"], "Popularity": t.get("popularity", 0)} for t in tracks]
    df = pd.DataFrame(data)
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Track:N", sort='-y'),
        y="Popularity:Q",
        tooltip=["Track", "Popularity"]
    ).properties(title=title, width=600, height=400)
    st.altair_chart(chart)

# --- Display Artist's Albums with Track Lists ---
def display_artist_albums(albums, access_token):
    """
    Displays the artist's albums as a grid of album covers with album name, release date,
    and an expander to show the album's tracks.
    """
    if not albums:
        st.warning("No albums found for this artist.")
        return

    cols = st.columns(3)
    for i, album in enumerate(albums):
        image_url = album.get("images", [{}])[0].get("url", None)
        album_name = album.get("name", "Unknown Album")
        release_date = album.get("release_date", "Unknown Date")
        album_id = album.get("id")
        with cols[i % 3]:
            if image_url:
                st.image(image_url, use_container_width=True)
            st.write(f"**{album_name}**")
            st.write(f"Release Date: {release_date}")
            with st.expander("Show Album Tracks"):
                tracks = get_album_tracks(album_id, access_token)
                if tracks:
                    for t in tracks:
                        track_name = t.get("name", "Unknown Track")
                        duration_ms = t.get("duration_ms", 0)
                        duration_min = duration_ms / 60000
                        st.write(f"- {track_name} ({duration_min:.2f} min)")
                else:
                    st.write("No tracks found for this album.")

# --- Main Streamlit App ---
def main():
    st.set_page_config(page_title="Holistic Track Insight Dashboard", layout="wide")
    st.title("🎶 Holistic Track Insight Dashboard")
    st.markdown(
        """
        This app aggregates Spotify track data with web context and leverages an LLM to provide a multi-dimensional
        understanding of a track. You’ll get insights into the track’s vibe, creative venue suggestions, and additional 
        visual analytics on related tracks and the artist's discography.
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
        
        track_options = {f"{t['name']} by {t['artists'][0]['name']}": t for t in tracks}
        selected_option = st.selectbox("Select the correct track", list(track_options.keys()))
        selected_track = track_options[selected_option]
        st.success(f"Selected: {selected_option}")
        progress.progress(50)
        
        aggregated_context = aggregate_track_context(selected_track)
        st.markdown("**Aggregated Track Context:**")
        st.code(aggregated_context)
        progress.progress(65)
        
        st.subheader("LLM-Generated Insights & Venue Suggestions (Streaming)")
        suggestions = generate_llm_suggestions_stream(aggregated_context)
        if not suggestions:
            st.error("Failed to generate suggestions.")
        progress.progress(80)
        
        st.subheader("Other Tracks by the Same Artist")
        artist_id = selected_track["artists"][0]["id"]
        artist_tracks = get_artist_top_tracks(artist_id, access_token)
        if artist_tracks:
            display_popularity_chart(artist_tracks, title="Artist Top Tracks Popularity")
        else:
            st.warning("No additional tracks found for the artist.")
        
        st.subheader("Artist's Albums")
        albums = get_artist_albums(artist_id, access_token)
        display_artist_albums(albums, access_token)
        
        progress.progress(100)

if __name__ == "__main__":
    main()

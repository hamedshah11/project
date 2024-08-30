import os
import streamlit as st
import requests
import plotly.express as px
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Spotify and OpenAI API credentials from environment variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Function to get Spotify access token using Client Credentials Flow
def get_spotify_access_token():
    url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code == 200:
        token_info = response.json()
        access_token = token_info.get("access_token")
        return access_token
    else:
        st.error(f"Failed to get access token: {response.status_code}")
        return None

# Function to search for tracks by name
def search_tracks(track_name, access_token):
    url = f"https://api.spotify.com/v1/search?q={track_name}&type=track&limit=5"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        tracks = response.json().get('tracks', {}).get('items', [])
        return tracks
    else:
        st.error(f"Error searching for track: {response.status_code}")
        return []

# Function to get audio features of a track
def get_audio_features(track_id, access_token):
    url = f"https://api.spotify.com/v1/audio-features/{track_id}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching data: {response.status_code}")
        return None

# Function to plot enhanced mood visualization with Plotly
def plot_enhanced_mood(features, track_name):
    fig = px.scatter(
        x=[features['valence']], 
        y=[features['energy']],
        size=[features['tempo']],  # Size based on tempo
        color=[features['danceability']],  # Color based on danceability
        hover_name=track_name,  # Show track name on hover
        labels={
            "x": "Valence (Positivity)",
            "y": "Energy",
            "color": "Danceability",
            "size": "Tempo"
        },
        title=f"Mood and Energy Visualization for {track_name}"
    )
    
    fig.update_layout(
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 1]),
        xaxis_title="Valence (Positivity)",
        yaxis_title="Energy",
        showlegend=False
    )
    
    st.plotly_chart(fig)

# Streamlit app main function
def main():
    st.title("Spotify Track Dashboard")

    track_name = st.text_input("Enter Spotify Track Name", "")
    if track_name:
        access_token = get_spotify_access_token()
        
        if access_token:
            tracks = search_tracks(track_name, access_token)
            
            if tracks:
                track_options = {f"{track['name']} by {track['artists'][0]['name']}": track['id'] for track in tracks}
                selected_track = st.selectbox("Select the correct track", options=list(track_options.keys()))
                
                if selected_track:
                    track_id = track_options[selected_track]
                    features = get_audio_features(track_id, access_token)
                    
                    if features:
                        # Enhanced Scatter Plot
                        plot_enhanced_mood(features, selected_track)

if __name__ == "__main__":
    main()

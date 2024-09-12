import os
import streamlit as st
import requests
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

# Function to get recommendations based on a song's audio features
def get_recommendations_by_features(features, access_token):
    url = (
        f"https://api.spotify.com/v1/recommendations?"
        f"limit=10"
        f"&target_acousticness={features['acousticness']}"
        f"&target_danceability={features['danceability']}"
        f"&target_energy={features['energy']}"
        f"&target_instrumentalness={features['instrumentalness']}"
        f"&target_liveness={features['liveness']}"
        f"&target_speechiness={features['speechiness']}"
        f"&target_tempo={features['tempo']}"
        f"&target_valence={features['valence']}"
    )
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('tracks', [])
    else:
        st.error(f"Error fetching recommendations: {response.status_code}")
        return None

# Function to generate track description using GPT-4 Mini model
def generate_description(features):
    description_prompt = f"""
    You are describing a music track based on its audio features. Use the following information to describe the track's overall mood, possible genre, and suggest scenarios or locations where it would be best enjoyed. Here's a breakdown of the key audio features for the track:
    
    1. **Acousticness**: This measures how acoustic the track is, with a value between 0.0 and 1.0. A higher value means the track is more likely to be acoustic. This track has an acousticness of {features['acousticness']}.
    
    2. **Danceability**: This describes how suitable the track is for dancing. Values closer to 1.0 mean the track is more danceable. The danceability score for this track is {features['danceability']}.
    
    3. **Energy**: This measures the intensity and activity of the track.

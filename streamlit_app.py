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
client = OpenAI(
    api_key=OPENAI_API_KEY,
)

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

# Function to generate track description using the latest OpenAI API
def generate_description(features):
    description_prompt = f"""
    Describe the following track features in a detailed paragraph:

    Acousticness: {features['acousticness']}
    Danceability: {features['danceability']}
    Duration (ms): {features['duration_ms']}
    Energy: {features['energy']}
    Instrumentalness: {features['instrumentalness']}
    Key: {features['key']}
    Liveness: {features['liveness']}
    Loudness: {features['loudness']}
    Mode: {features['mode']}
    Speechiness: {features['speechiness']}
    Tempo: {features['tempo']}
    Time Signature: {features['time_signature']}
    Valence: {features['valence']}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": description_prompt}
            ],
            model="gpt-4"
        )
        
        return chat_completion.choices[0].message.content.strip()
    
    except Exception as e:
        st.error(f"Error generating description: {str(e)}")
        return None

# Streamlit app main function
def main():
    st.title("Spotify Track Audio Features Analyzer")

    track_name = st.text_input("Enter Spotify Track Name", "")
    if track_name:
        st.write("Fetching access token...")
        access_token = get_spotify_access_token()
        
        if access_token:
            st.write(f"Searching for tracks matching: {track_name}...")
            tracks = search_tracks(track_name, access_token)
            
            if tracks:
                # Display a dropdown menu for the user to select the correct track
                track_options = {f"{track['name']} by {track['artists'][0]['name']}": track['id'] for track in tracks}
                selected_track = st.selectbox("Select the correct track", options=list(track_options.keys()))
                
                if selected_track:
                    track_id = track_options[selected_track]
                    st.write("Fetching audio features...")
                    features = get_audio_features(track_id, access_token)
                    
                    if features:
                        st.write("Audio Features:", features)
                        st.write("Generating track description...")
                        description = generate_description(features)
                        st.write("Track Description:", description)

if __name__ == "__main__":
    main()

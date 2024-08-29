import streamlit as st
import requests
import openai
import base64
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Spotify and OpenAI API credentials from environment variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Function to get Spotify access token
def get_spotify_access_token():
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials"
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        st.error("Failed to get access token")
        return None

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

# Function to generate track description using GPT-4 Mini model
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

    response = openai.Completion.create(
        model="gpt-4-mini",
        prompt=description_prompt,
        max_tokens=150,
        temperature=0.7,
        api_key=OPENAI_API_KEY
    )

    return response.choices[0].text.strip()

# Streamlit app main function
def main():
    st.title("Spotify Track Audio Features Analyzer")

    track_id = st.text_input("Enter Spotify Track ID", "")
    if track_id:
        st.write("Fetching access token...")
        access_token = get_spotify_access_token()
        
        if access_token:
            st.write("Fetching audio features...")
            features = get_audio_features(track_id, access_token)
            
            if features:
                st.write("Audio Features:", features)
                st.write("Generating track description...")
                description = generate_description(features)
                st.write("Track Description:", description)

if __name__ == "__main__":
    main()

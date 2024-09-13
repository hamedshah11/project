import os
import streamlit as st
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Spotify credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Function to get Spotify access token using Client Credentials Flow
def get_spotify_access_token():
    try:
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
            st.write("Access Token:", access_token)  # Display the access token to check if it's working
            return access_token
        else:
            st.error(f"Failed to get access token: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error during authentication: {str(e)}")
        return None

# Function to search for tracks by name
def search_tracks(track_name, access_token):
    try:
        url = f"https://api.spotify.com/v1/search?q={track_name}&type=track&limit=5"
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tracks = response.json().get('tracks', {}).get('items', [])
            st.write("Tracks Found:", tracks)  # Display the tracks to check if it's working
            return tracks
        else:
            st.error(f"Error searching for track: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error during track search: {str(e)}")
        return []

# Main Streamlit app function
def main():
    st.title("DJAI - The DJ's AI Assistant")

    # Input for the track name
    track_name = st.text_input("Enter Spotify Track Name", "")

    if track_name:
        # Get the Spotify access token
        access_token = get_spotify_access_token()
        if access_token:
            # Search for the track
            search_tracks(track_name, access_token)

if __name__ == "__main__":
    main()

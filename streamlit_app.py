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
            return tracks
        else:
            st.error(f"Error searching for track: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error during track search: {str(e)}")
        return []

# Function to get audio features of a track
def get_audio_features(track_id, access_token):
    try:
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
    except Exception as e:
        st.error(f"Error fetching audio features: {str(e)}")
        return None

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
            tracks = search_tracks(track_name, access_token)
            if tracks:
                # Create a selectbox for user to choose the correct track
                track_options = {f"{track['name']} by {track['artists'][0]['name']}": track['id'] for track in tracks}
                selected_track = st.selectbox("Select the correct track", options=list(track_options.keys()))
                
                if selected_track:
                    st.success(f"You selected: {selected_track}")
                    track_id = track_options[selected_track]

                    # Get and display audio features
                    features = get_audio_features(track_id, access_token)
                    if features:
                        st.subheader("Audio Features of the Track")
                        st.write(features)  # Display audio features in a structured way
            else:
                st.warning("No tracks found for the given search")

if __name__ == "__main__":
    main()

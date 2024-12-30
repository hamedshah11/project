import os
import streamlit as st
import requests
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Spotify API credentials from environment variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# OpenAI API key from Streamlit secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in secrets.")
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise ValueError("Spotify credentials are not set in .env file.")

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

# Function to recommend DJ places based on track audio features
def recommend_dj_places(features):
    description_prompt = f"""
    Based on the following audio features of the track, suggest the top 3-4 places or settings where a DJ could play this track, focusing on the overall feel and mood of the song, not just its tempo:

    1. Acousticness: {features['acousticness']}
    2. Danceability: {features['danceability']}
    3. Energy: {features['energy']}
    4. Instrumentalness: {features['instrumentalness']}
    5. Liveness: {features['liveness']}
    6. Loudness: {features['loudness']} dB
    7. Speechiness: {features['speechiness']}
    8. Tempo: {features['tempo']} BPM
    9. Valence: {features['valence']}

    Suggest unique settings based on the energy, mood, and vibe of the song. Output should only be the 4 places numbered 1-4, nothing else.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": description_prompt}
            ]
        )
        places = response['choices'][0]['message']['content'].strip().split('\n')
        clean_places = [place.lstrip("0123456789. ") for place in places if place]
        return clean_places
    except Exception as e:
        st.error(f"Error generating DJ places recommendation: {str(e)}")
        return None

# Function to generate a brief description and DALL-E image for the track based on audio features
def generate_image_based_on_description(features):
    description_prompt = f"""
    Create a single, intriguing sentence to describe the track based on the following audio features:

    1. Acousticness: {features['acousticness']}
    2. Danceability: {features['danceability']}
    3. Energy: {features['energy']}
    4. Instrumentalness: {features['instrumentalness']}
    5. Liveness: {features['liveness']}
    6. Loudness: {features['loudness']}
    7. Speechiness: {features['speechiness']}
    8. Tempo: {features['tempo']} BPM
    9. Valence: {features['valence']}

    Summarize the song in one captivating sentence.
    """

    try:
        # Generate text description
        text_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": description_prompt}
            ]
        )
        description = text_response['choices'][0]['message']['content'].strip()

        # Generate the image prompt
        image_prompt = f"Generate an abstract, visually stunning HD art piece based on this track with acousticness {features['acousticness']}, danceability {features['danceability']}, energy {features['energy']}, tempo {features['tempo']} BPM, and valence {features['valence']}."

        # Generate the image
        image_response = openai.Image.create(
            prompt=image_prompt,
            n=1,
            size="1024x1024"
        )
        image_url = image_response['data'][0]['url']

        return description, image_url

    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None, None

# Main Streamlit app function
def main():
    st.set_page_config(page_title="DJAI - The DJ's AI Assistant", layout="wide")

    # Title
    st.title("\ud83c\udfb6 DJAI - The DJ's AI Assistant")
    st.markdown("This app helps DJs discover the perfect settings for their tracks, generate visuals based on track audio features, and find similar music.")

    # Input for the track name
    track_name = st.text_input("Enter Spotify Track Name", "")

    if track_name:
        # Progress bar and placeholder for loading
        progress_bar = st.progress(0)
        placeholder = st.empty()

        # Get the Spotify access token
        progress_bar.progress(10)
        access_token = get_spotify_access_token()
        if access_token:
            # Search for the track
            progress_bar.progress(30)
            tracks = search_tracks(track_name, access_token)
            if tracks:
                # Create a selectbox for user to choose the correct track
                track_options = {f"{track['name']} by {track['artists'][0]['name']}": track['id'] for track in tracks}
                selected_track = st.selectbox("Select the correct track", options=list(track_options.keys()))

                if selected_track:
                    track_id = track_options[selected_track]
                    st.success(f"You selected: {selected_track}")

                    # Get audio features for the selected track
                    progress_bar.progress(50)
                    features = get_audio_features(track_id, access_token)

                    if features:
                        # Display track details and recommendations in columns
                        col1, col2 = st.columns([2, 1])

                        with col1:
                            # Generate DJ places recommendations
                            st.subheader("\ud83c\udfa7 Where would a DJ play this track?")
                            dj_places = recommend_dj_places(features)
                            if dj_places:
                                st.markdown("**Best Places or Settings for this Track:**")
                                for i, place in enumerate(dj_places, 1):
                                    st.markdown(f"{i}. {place}")

                            # Generate an image based on the audio features
                            st.subheader("\ud83c\udfa8 Generated Artwork for this Track")
                            description, image_url = generate_image_based_on_description(features)
                            if description:
                                st.markdown(f"**Track Description:** {description}")
                            if image_url:
                                st.image(image_url, caption="AI Generated Artwork")

                        with col2:
                            # Get similar track recommendations
                            st.subheader("\ud83c\udfb5 Similar Track Recommendations")
                            recommendations = search_tracks(track_name, access_token)
                            if recommendations:
                                for track in recommendations:
                                    track_name = track['name']
                                    artist_name = track['artists'][0]['name']
                                    track_url = track['external_urls']['spotify']
                                    st.markdown(f"- **[{track_name} by {artist_name}]({track_url})**")

                        progress_bar.progress(100)
            else:
                st.warning("No tracks found for the given search")
        else:
            st.error("Spotify Authentication Failed")

if __name__ == "__main__":
    main()

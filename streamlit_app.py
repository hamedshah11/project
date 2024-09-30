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

    Suggest unique settings (clubs, lounges, outdoor festivals, intimate settings, etc.) based on the energy, mood, and vibe of the song.
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": description_prompt}
            ],
            model="gpt-4o-mini"
        )
        places = chat_completion.choices[0].message.content.strip().split('\n')
        clean_places = [place.lstrip("0123456789. ") for place in places if place]  # Remove any unwanted numbers
        return clean_places
    except Exception as e:
        st.error(f"Error generating DJ places recommendation: {str(e)}")
        return None

# Function to generate a description and DALL-E image for the track based on audio features
def generate_image_based_on_description(features):
    description_prompt = f"""
    Create a description of the track based on the following audio features:

    1. Acousticness: {features['acousticness']}
    2. Danceability: {features['danceability']}
    3. Energy: {features['energy']}
    4. Instrumentalness: {features['instrumentalness']}
    5. Liveness: {features['liveness']}
    6. Loudness: {features['loudness']}
    7. Speechiness: {features['speechiness']}
    8. Tempo: {features['tempo']} BPM
    9. Valence: {features['valence']}

    Based on these characteristics, write a brief description of the song.
    """

    try:
        # Generate text description
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": description_prompt}
            ],
            model="gpt-4o-mini"
        )
        description = chat_completion.choices[0].message.content.strip()

        # Generate the image prompt
        prompt_instruction = f"Generate an abstract, visually stunning HD art piece based on this track with acousticness {features['acousticness']}, danceability {features['danceability']}, energy {features['energy']}, tempo {features['tempo']} BPM, and valence {features['valence']}."

        # Generate the image
        response = client.images.generate(prompt=prompt_instruction, size="1024x1024")
        image_url = response.data[0].url

        return description, image_url

    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None, None

# Function to get track recommendations based on audio features
def get_track_recommendations(track_id, features, access_token):
    try:
        url = f"https://api.spotify.com/v1/recommendations?seed_tracks={track_id}&limit=10"
        params = {
            "min_energy": features['energy'] - 0.1,
            "max_energy": features['energy'] + 0.1,
            "min_tempo": features['tempo'] - 10,
            "max_tempo": features['tempo'] + 10,
            "min_danceability": features['danceability'] - 0.1,
            "max_danceability": features['danceability'] + 0.1
        }
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            recommendations = response.json().get('tracks', [])
            return recommendations
        else:
            st.error(f"Error fetching recommendations: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching recommendations: {str(e)}")
        return []

# Main Streamlit app function
def main():
    st.set_page_config(page_title="DJAI - The DJ's AI Assistant", layout="wide")

    # Title
    st.title("🎶 DJAI - The DJ's AI Assistant")
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
                            st.subheader("🎧 Where would a DJ play this track?")
                            dj_places = recommend_dj_places(features)
                            if dj_places:
                                st.markdown("**Best Places or Settings for this Track:**")
                                for i, place in enumerate(dj_places, 1):  # Manually number the places
                                    st.markdown(f"{i}. {place}")

                            # Generate an image based on the audio features
                            st.subheader("🎨 Generated Artwork for this Track")
                            description, image_url = generate_image_based_on_description(features)
                            if description:
                                st.markdown(f"**Description of the Track:** {description}")
                            if image_url:
                                st.image(image_url, caption="AI Generated Artwork")

                        with col2:
                            # Get similar track recommendations
                            st.subheader("🎵 Similar Track Recommendations")
                            recommendations = get_track_recommendations(track_id, features, access_token)
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

import os
import streamlit as st
import requests
import openai
from openai.error import OpenAIError
from dotenv import load_dotenv
import urllib.parse

# Load environment variables from .env file
load_dotenv()

# Spotify and OpenAI API credentials from environment variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Check if environment variables are loaded
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET or not OPENAI_API_KEY:
    st.error("One or more environment variables are missing. Please check your .env file.")
    st.stop()

# Initialize the OpenAI API key
openai.api_key = OPENAI_API_KEY

# Function to get Spotify access token using Client Credentials Flow
def get_spotify_access_token():
    try:
        auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
        b64_auth_str = urllib.parse.quote(auth_str)
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": f"Basic {b64_auth_str}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials"
        }
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info.get("access_token")
            return access_token
        else:
            st.error(f"Failed to get access token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error during authentication: {str(e)}")
        return None

# Function to search for tracks by name
def search_tracks(track_name, access_token):
    try:
        url = "https://api.spotify.com/v1/search"
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        params = {
            'q': track_name,
            'type': 'track',
            'limit': 5
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            tracks = response.json().get('tracks', {}).get('items', [])
            return tracks
        else:
            st.error(f"Error searching for track: {response.status_code} - {response.text}")
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
            st.error(f"Error fetching audio features: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error fetching audio features: {str(e)}")
        return None

# Function to recommend DJ places based on track audio features
def recommend_dj_places(features):
    description_prompt = f"""
    Based on the following audio features of the track, suggest the top 3-4 places or settings where a DJ could play this track:

    1. Acousticness: {features['acousticness']}
    2. Danceability: {features['danceability']}
    3. Energy: {features['energy']}
    4. Instrumentalness: {features['instrumentalness']}
    5. Liveness: {features['liveness']}
    6. Loudness: {features['loudness']} dB
    7. Speechiness: {features['speechiness']}
    8. Tempo: {features['tempo']} BPM
    9. Valence: {features['valence']}

    Focus on the feel of the track and suggest unique settings based on the energy, mood, and vibe of the song.
    """

    try:
        chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use "gpt-4" if you have access
            messages=[
                {"role": "user", "content": description_prompt}
            ]
        )
        # Process the response to remove any numbering from the model's output
        places = chat_completion.choices[0].message.content.strip().split('\n')
        clean_places = [place.lstrip("0123456789. ") for place in places if place]
        return clean_places
    except OpenAIError as e:
        st.error(f"Error generating DJ places recommendation: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None

# Function to generate an image based on audio features
def generate_image_based_on_description(features):
    # Create a prompt for image generation
    prompt_instruction = f"An abstract, visually stunning HD art piece that captures the mood of a track with acousticness {features['acousticness']}, danceability {features['danceability']}, energy {features['energy']}, tempo {features['tempo']} BPM, and valence {features['valence']}."

    if len(prompt_instruction) > 1000:
        prompt_instruction = prompt_instruction[:997] + "..."

    try:
        # Generate the image using OpenAI's Image API
        response = openai.Image.create(
            prompt=prompt_instruction,
            n=1,
            size="1024x1024"
        )
        image_url = response['data'][0]['url']
        return image_url
    except OpenAIError as e:
        st.error(f"Error generating image: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None

# Function to get track recommendations based on audio features
def get_track_recommendations(track_id, features, access_token):
    try:
        url = "https://api.spotify.com/v1/recommendations"
        params = {
            "seed_tracks": track_id,
            "limit": 10,
            "min_energy": max(0, features['energy'] - 0.1),
            "max_energy": min(1, features['energy'] + 0.1),
            "min_tempo": max(0, features['tempo'] - 10),
            "max_tempo": features['tempo'] + 10,
            "min_danceability": max(0, features['danceability'] - 0.1),
            "max_danceability": min(1, features['danceability'] + 0.1)
        }
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            recommendations = response.json().get('tracks', [])
            return recommendations
        else:
            st.error(f"Error fetching recommendations: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"Error fetching recommendations: {str(e)}")
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
            with st.spinner('Searching for tracks...'):
                tracks = search_tracks(track_name, access_token)
            if tracks:
                # Create a selectbox for the user to choose the correct track
                track_options = {f"{track['name']} by {track['artists'][0]['name']}": track['id'] for track in tracks}
                selected_track_name = st.selectbox("Select the correct track", options=list(track_options.keys()))

                if selected_track_name:
                    st.success(f"You selected: {selected_track_name}")
                    track_id = track_options[selected_track_name]

                    # Get audio features for the selected track
                    with st.spinner('Fetching audio features...'):
                        features = get_audio_features(track_id, access_token)
                    if features:
                        # Generate DJ places recommendations
                        st.subheader("Where would a DJ play this track?")
                        with st.spinner('Generating recommendations...'):
                            dj_places = recommend_dj_places(features)
                        if dj_places:
                            st.markdown("**Best Places or Settings for this Track:**")
                            for i, place in enumerate(dj_places, 1):
                                st.markdown(f"{i}. {place}")

                        # Generate an image based on the audio features
                        st.subheader("Generated Artwork for this Track")
                        with st.spinner('Generating artwork...'):
                            image_url = generate_image_based_on_description(features)
                        if image_url:
                            st.image(image_url, caption="AI Generated Artwork")

                        # Get similar track recommendations
                        st.subheader("Similar Track Recommendations")
                        with st.spinner('Fetching recommendations...'):
                            recommendations = get_track_recommendations(track_id, features, access_token)
                        if recommendations:
                            for rec_track in recommendations:
                                rec_track_name = rec_track['name']
                                rec_artist_name = rec_track['artists'][0]['name']
                                rec_track_url = rec_track['external_urls']['spotify']
                                st.markdown(f"- **[{rec_track_name} by {rec_artist_name}]({rec_track_url})**")
                    else:
                        st.error("Failed to fetch audio features.")
                else:
                    st.warning("Please select a track from the dropdown.")
            else:
                st.warning("No tracks found for the given search.")
        else:
            st.error("Failed to obtain Spotify access token.")
    else:
        st.info("Please enter a track name to begin.")

if __name__ == "__main__":
    main()

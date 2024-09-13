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
    Based on the following detailed audio features of the track, suggest the top 3-4 places or settings where a DJ could play this track:

    1. Acousticness: {features['acousticness']} (A measure of how acoustic a track is. Values closer to 1 indicate a more acoustic sound.)
    2. Danceability: {features['danceability']} (This describes how suitable a track is for dancing. Values closer to 1 indicate higher suitability for dancing.)
    3. Energy: {features['energy']} (Energy is a perceptual measure of intensity and activity. Higher values suggest a more energetic and lively track.)
    4. Instrumentalness: {features['instrumentalness']} (This predicts whether the track contains no vocals. Values closer to 1 suggest instrumental tracks.)
    5. Liveness: {features['liveness']} (Liveness detects the presence of an audience. Higher values suggest a live performance.)
    6. Loudness: {features['loudness']} dB (The overall loudness of the track in decibels.)
    7. Speechiness: {features['speechiness']} (Speechiness detects spoken words in a track. Values closer to 1 indicate more speech-like qualities.)
    8. Tempo: {features['tempo']} BPM (The tempo of the track in beats per minute.)
    9. Valence: {features['valence']} (A measure of the musical positiveness conveyed by the track. Higher values sound more positive and cheerful, while lower values sound more negative and moody.)

    Based on these characteristics, suggest appropriate settings like clubs, outdoor events, lounges, or other social environments where this track would resonate the most.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": description_prompt}
            ],
            model="gpt-4o-mini"
        )
        # Process the response to remove any numbering from the model's output
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

        # Ensure prompt length is within 1000 characters
        prompt_instruction = f"Generate an abstract, visually stunning HD art piece based on this track with acousticness {features['acousticness']}, danceability {features['danceability']}, energy {features['energy']}, tempo {features['tempo']} BPM, and valence {features['valence']}."

        if len(prompt_instruction) > 1000:
            prompt_instruction = prompt_instruction[:997] + "..."

        # Generate the image
        response = client.images.generate(prompt=prompt_instruction, size="1024x1024")
        image_url = response.data[0].url

        return image_url

    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None

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

                    # Get audio features for the selected track
                    features = get_audio_features(track_id, access_token)
                    if features:
                        # Generate DJ places recommendations
                        st.subheader("Where would a DJ play this track?")
                        dj_places = recommend_dj_places(features)
                        if dj_places:
                            st.markdown(f"**Best Places or Settings for this Track:**")
                            for i, place in enumerate(dj_places, 1):  # Manually number the places
                                st.markdown(f"{i}. {place}")

                        # Generate an image based on the audio features
                        st.subheader("Generated Artwork for this Track")
                        image_url = generate_image_based_on_description(features)
                        if image_url:
                            st.image(image_url, caption="AI Generated Artwork")

                        # Get similar track recommendations
                        st.subheader("Similar Track Recommendations")
                        recommendations = get_track_recommendations(track_id, features, access_token)
                        if recommendations:
                            for track in recommendations:
                                track_name = track['name']
                                artist_name = track['artists'][0]['name']
                                track_url = track['external_urls']['spotify']
                                st.markdown(f"- **[{track_name} by {artist_name}]({track_url})**")
            else:
                st.warning("No tracks found for the given search")

if __name__ == "__main__":
    main()

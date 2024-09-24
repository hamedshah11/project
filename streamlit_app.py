import os
import streamlit as st
import requests
import openai
import openai.error  # Import the error module
from dotenv import load_dotenv
import plotly.graph_objs as go

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
            st.error(f"Error fetching data: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error fetching audio features: {str(e)}")
        return None

# Function to recommend DJ places based on track audio features
def recommend_dj_places(features):
    description_prompt = f"""
    Based on the following audio features of the track, suggest the top 3-4 places or settings where a DJ could play this track, focusing on the overall feel and mood of the song, not just its tempo:

    1. Acousticness: {features['acousticness']} (A measure of how acoustic a track is.)
    2. Danceability: {features['danceability']} (Suitability for dancing.)
    3. Energy: {features['energy']} (Intensity and activity.)
    4. Instrumentalness: {features['instrumentalness']} (Presence of vocals.)
    5. Liveness: {features['liveness']} (Presence of an audience.)
    6. Loudness: {features['loudness']} dB (Overall loudness.)
    7. Speechiness: {features['speechiness']} (Presence of spoken words.)
    8. Tempo: {features['tempo']} BPM (Speed of the track.)
    9. Valence: {features['valence']} (Musical positiveness.)

    Focus on the feel of the track, considering how the combination of these features would influence the environment where it could be best played. Suggest unique settings (clubs, lounges, outdoor festivals, intimate settings, etc.) based on the energy, mood, and vibe of the song.
    """

    try:
        chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": description_prompt}
            ]
        )
        # Process the response to remove any numbering from the model's output
        response_text = chat_completion.choices[0].message.content.strip()
        places = response_text.split('\n')
        clean_places = [place.lstrip("0123456789. ") for place in places if place]
        return clean_places
    except openai.error.OpenAIError as e:
        st.error(f"OpenAI API error: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
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
        chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": description_prompt}
            ]
        )
        description = chat_completion.choices[0].message.content.strip()

        # Ensure prompt length is within 1000 characters
        prompt_instruction = f"Generate an abstract, visually stunning HD art piece based on this track with acousticness {features['acousticness']}, danceability {features['danceability']}, energy {features['energy']}, tempo {features['tempo']} BPM, and valence {features['valence']}. The art should capture the mood and essence of the music."

        if len(prompt_instruction) > 1000:
            prompt_instruction = prompt_instruction[:997] + "..."

        # Generate the image
        response = openai.Image.create(
            prompt=prompt_instruction,
            n=1,
            size="1024x1024"
        )
        image_url = response['data'][0]['url']

        return image_url

    except openai.error.OpenAIError as e:
        st.error(f"OpenAI API error: {e}")
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

# Function to visualize audio features
def visualize_audio_features(features):
    # Select features to visualize
    feature_names = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence']
    feature_values = [features[name] for name in feature_names]

    # Create radar chart
    fig = go.Figure(data=go.Scatterpolar(
        r=feature_values + [feature_values[0]],  # Close the loop
        theta=feature_names + [feature_names[0]],
        fill='toself'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=False,
        title="Audio Features Radar Chart"
    )

    st.plotly_chart(fig)

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
                st.subheader("Select the correct track")
                # Display track options with album art
                track_options = []
                for idx, track in enumerate(tracks):
                    track_info = {
                        'id': track['id'],
                        'name': track['name'],
                        'artist': track['artists'][0]['name'],
                        'album': track['album']['name'],
                        'album_art': track['album']['images'][0]['url'] if len(track['album']['images']) > 0 else None
                    }
                    track_options.append(track_info)

                # Display tracks with images
                selected_track_id = None
                for idx, track in enumerate(track_options):
                    st.write(f"**{idx+1}. {track['name']}** by {track['artist']}")
                    if track['album_art']:
                        st.image(track['album_art'], width=100)
                    st.write(f"Album: {track['album']}")
                    st.write("---")

                selected_index = st.number_input(
                    "Enter the number of the correct track",
                    min_value=1,
                    max_value=len(track_options),
                    step=1
                ) - 1

                if selected_index is not None and 0 <= selected_index < len(track_options):
                    selected_track = track_options[selected_index]
                    st.success(f"You selected: {selected_track['name']} by {selected_track['artist']}")
                    track_id = selected_track['id']

                    # Get audio features for the selected track
                    with st.spinner('Fetching audio features...'):
                        features = get_audio_features(track_id, access_token)
                    if features:
                        # Visualize audio features
                        st.subheader("Audio Features Visualization")
                        visualize_audio_features(features)

                        # Generate DJ places recommendations
                        st.subheader("Where would a DJ play this track?")
                        with st.spinner('Generating recommendations...'):
                            dj_places = recommend_dj_places(features)
                        if dj_places:
                            st.markdown(f"**Best Places or Settings for this Track:**")
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
                            for track in recommendations:
                                track_name = track['name']
                                artist_name = track['artists'][0]['name']
                                track_url = track['external_urls']['spotify']
                                st.markdown(f"- **[{track_name} by {artist_name}]({track_url})**")
            else:
                st.warning("No tracks found for the given search")
        else:
            st.error("Failed to obtain Spotify access token.")
    else:
        st.info("Please enter a track name to begin.")

if __name__ == "__main__":
    main()

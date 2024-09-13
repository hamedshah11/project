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
    if response.status_code == 200):
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

# Function to get track recommendations based on audio features
def get_track_recommendations(track_id, access_token):
    url = f"https://api.spotify.com/v1/recommendations?seed_tracks={track_id}&limit=10"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        recommendations = response.json().get('tracks', [])
        return recommendations
    else:
        st.error(f"Error fetching recommendations: {response.status_code}")
        return []

# Function to recommend places or scenes where a DJ could play the track
def recommend_dj_places(features):
    description_prompt = f"""
    Based on the following audio features of the track, suggest places or scenes where a DJ could play this track:

    1. **Acousticness**: {features['acousticness']}
    2. **Danceability**: {features['danceability']}
    3. **Energy**: {features['energy']}
    4. **Instrumentalness**: {features['instrumentalness']}
    5. **Liveness**: {features['liveness']}
    6. **Loudness**: {features['loudness']}
    7. **Speechiness**: {features['speechiness']}
    8. **Tempo**: {features['tempo']} BPM
    9. **Valence**: {features['valence']}
    
    Suggest scenarios, venues, or settings where the track would be appropriate for a DJ set, based on its energy, danceability, and mood.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": description_prompt}
            ],
            model="gpt-4o-mini"
        )
        
        return chat_completion.choices[0].message.content.strip()
    
    except Exception as e:
        st.error(f"Error generating DJ places recommendation: {str(e)}")
        return None

# Function to generate a description for the track and an associated image using DALL-E
def generate_description_and_image(features):
    description_prompt = f"""
    Create a description of the track based on the following audio features:
    
    1. **Acousticness**: {features['acousticness']}
    2. **Danceability**: {features['danceability']}
    3. **Energy**: {features['energy']}
    4. **Instrumentalness**: {features['instrumentalness']}
    5. **Liveness**: {features['liveness']}
    6. **Loudness**: {features['loudness']}
    7. **Speechiness**: {features['speechiness']}
    8. **Tempo**: {features['tempo']} BPM
    9. **Valence**: {features['valence']}
    
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

        # Simplified and safe image generation prompt
        image_prompt = (
            f"Generate an abstract image representing the mood and style of a music track that has the following attributes: "
            f"Acousticness {features['acousticness']}, Danceability {features['danceability']}, Energy {features['energy']}, "
            f"Tempo {features['tempo']} BPM, and Valence {features['valence']}. Focus on abstract shapes and colors, no text."
        )
        
        if len(image_prompt) > 1000:
            image_prompt = image_prompt[:997] + "..."  # Truncate the prompt if it's still too long
        
        response = client.images.generate(prompt=image_prompt, size="1024x1024")
        image_url = response.data[0].url
        
        return description, image_url
    
    except Exception as e:
        st.error(f"Error generating description or image: {str(e)}")
        return None, None

# Streamlit app main function
def main():
    st.title("Spotify DJ Scene Recommendation, Track Description & Similar Tracks")

    track_name = st.text_input("Enter Spotify Track Name", "")
    if track_name:
        access_token = get_spotify_access_token()
        
        if access_token:
            tracks = search_tracks(track_name, access_token)
            
            if tracks:
                track_options = {f"{track['name']} by {track['artists'][0]['name']}": track['id'] for track in tracks}
                selected_track = st.selectbox("Select the correct track", options=list(track_options.keys()))
                
                if selected_track:
                    track_id = track_options[selected_track]
                    features = get_audio_features(track_id, access_token)
                    
                    if features:
                        st.subheader("Where would a DJ play this track?")
                        dj_places = recommend_dj_places(features)
                        if dj_places:
                            st.write(dj_places)

                        st.subheader("Track Description and Visual Representation")
                        description, image_url = generate_description_and_image(features)
                        if description:
                            st.write(description)
                        if image_url:
                            st.image(image_url, caption="Generated Artwork")
                    
                    # Get Recommendations for Similar Tracks
                    st.subheader("Similar Track Recommendations")
                    recommendations = get_track_recommendations(track_id, access_token)
                    if recommendations:
                        for track in recommendations:
                            st.write(f"{track['name']} by {track['artists'][0]['name']}")

if __name__ == "__main__":
    main()

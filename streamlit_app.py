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
    if response.status_code == 200):
        return response.json()
    else:
        st.error(f"Error fetching data: {response.status_code}")
        return None

# Function to generate track description using GPT-4 Mini model
def generate_description(features):
    description_prompt = f"""
    Imagine you're describing a piece of music. Based on the following characteristics, describe the overall mood, suggest places where it might be best enjoyed, and guess the genre:
    
    1. The track has a certain amount of energy, which might make it feel lively or laid-back.
    2. It has a danceability factor, meaning it could either be great for dancing or more suited for relaxing.
    3. The positivity of the track varies, making it sound either cheerful, neutral, or somewhat serious.
    4. It has an acoustic quality that might make it feel organic, or it might be more electronic and produced.
    5. There is a certain level of instrumentalness, meaning it might have vocals or could be an instrumental piece.
    6. The tempo of the track is {features['tempo']} BPM, which can influence the genre. For example, a higher tempo (around 120-130 BPM) is often associated with house music or dance tracks, while a lower tempo might suggest a more relaxed genre.
    
    Based on these aspects, describe the track in a few sentences, recommend a general setting where this track would be best enjoyed, and guess the genre, especially considering how the tempo might influence the style of the music.
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
        st.error(f"Error generating description: {str(e)}")
        return None

# Function to generate an image for the track using DALL-E
def generate_image(description):
    try:
        # Create a more focused prompt with explicit instructions to exclude text
        image_prompt = (
            f"Create an abstract, visually captivating image representing the following description: {description}. "
            "The image should reflect the mood and style of the track, capturing its energy and genre. "
            "Please ensure that the image contains no words, text, or letters, focusing only on colors, shapes, and abstract visual elements."
        )
        
        if len(image_prompt) > 1000:
            image_prompt = image_prompt[:997] + "..."  # Truncate the prompt if it's still too long
        
        response = client.images.generate(prompt=image_prompt, size="1024x1024")
        
        # Correctly access the URL from the response object
        image_url = response.data[0].url
        
        return image_url
    
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None

# Streamlit app main function
def main():
    st.title("Spotify Track Description and Artwork Generator")

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
                        description = generate_description(features)
                        if description:
                            st.write(description)
                            
                            image_url = generate_image(description)
                            if image_url:
                                st.image(image_url, caption="Generated Artwork")

if __name__ == "__main__":
    main()

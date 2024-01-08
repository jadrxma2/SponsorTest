import streamlit as st
from apify_client import ApifyClient 
import os
import hashlib
import time
import speech_recognition as sr
import json

# Streamlit page configuration
st.set_page_config(page_title="Audio Transcription App", layout="wide")

# Streamlit sidebar for input
st.sidebar.title("Settings")
API_TOKEN = st.sidebar.text_input("API Token", "Enter your API token here")  # Replace with your actual API token
ACTOR_ID = st.sidebar.text_input("Actor ID", "Enter your actor ID here")  # Replace with your actor ID
SAVE_DIRECTORY = st.sidebar.text_input("Save Directory", "/path/to/save")  # Enter the default save directory

# Streamlit main area
st.title("Audio Transcription App")
start_button = st.button('Start Transcription Process')

# Function definitions remain the same
# ...
def generate_filename(url):
    return hashlib.md5(url.encode()).hexdigest()

def download_audio(url, download_path, filename):
    command = f"youtube-dl -x --audio-format wav --postprocessor-args '-ar 16000' '{url}' -o '{download_path}/{filename}.%(ext)s'"
    if os.system(command) != 0:
        print(f"Failed to download or convert audio from {url}")
        return False
    return True

def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except Exception as e:
        print(f"Error transcribing audio file {audio_path}: {e}")
        return None

def save_transcript(transcript, file_path):
    with open(file_path, 'w') as file:
        file.write(transcript)

def start_and_wait_for_actor():
    run_input = {
        "name": "aitools",
        "limit": 1,
        "proxyConfiguration": {"useApifyProxy": True}
    }

    run = client.actor(ACTOR_ID).call(run_input=run_input)

    # Wait for the actor to finish
    while True:
        run_detail = client.run(run['id']).get()
        if run_detail['status'] in ['SUCCEEDED', 'FAILED', 'ABORTED']:
            return run_detail
        time.sleep(10)  # Check every 10 seconds

def get_video_links(run_detail):
    video_links = []

    # Debugging: print the keys of run_detail to understand its structure
    print("Keys in run_detail:", run_detail.keys())

    # Assuming 'defaultDatasetId' is a key in run_detail that leads to the dataset
    dataset_id = run_detail.get('defaultDatasetId', None)
    if not dataset_id:
        print("No dataset ID found in run_detail")
        return video_links

    # Fetching the dataset - this part might need to be adjusted
    dataset = client.dataset(dataset_id).iterate_items()  # Adjust this if needed

    for item in dataset:
        # Convert item to dictionary if it's a string
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                continue

        # Debugging: print the keys of the item
        print("Keys in item:", item.keys())

        # Navigate to the 'play_addr' key inside the 'video' key
        video_info = item.get('video', {})
        play_addr_info = video_info.get('play_addr', {})
        url_list = play_addr_info.get('url_list', [])

        # Extract the specific URL
        if url_list:
            desired_url = url_list[-1]  # Gets the last URL in the list
            video_links.append(desired_url)

    return video_links

def process_videos(video_links):
    for video_url in video_links:
        filename = generate_filename(video_url)
        audio_file = os.path.join(SAVE_DIRECTORY, f"{filename}.wav")
        transcript_file = os.path.join(SAVE_DIRECTORY, f"transcript_{filename}.txt")

        if not os.path.exists(SAVE_DIRECTORY):
            os.makedirs(SAVE_DIRECTORY)

        print(f"Processing video: {video_url}")
        if not download_audio(video_url, SAVE_DIRECTORY, filename):
            continue

        print("Transcribing audio...")
        transcript = transcribe_audio(audio_file)
        if transcript is not None:
            save_transcript(transcript, transcript_file)
            print(f"Transcript saved to {transcript_file}")
        else:
            print(f"Failed to transcribe {video_url}")
            
def main():
    if start_button:
        with st.spinner('Processing...'):
            run_detail = start_and_wait_for_actor()
            if run_detail and run_detail['status'] == 'SUCCEEDED':
                video_links = get_video_links(run_detail)
                if video_links:
                    process_videos(video_links)
                    st.success("Processing completed.")
                else:
        
                    st.error("No video links found.")
            else:
                st.error(f"Actor run did not succeed, status: {run_detail['status']}")

# Call main function when the start button is pressed
if __name__ == "__main__":
    main()
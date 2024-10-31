import os
import json
from supabase_client import SupabaseClient

def upload_existing_transcripts():
    supabase = SupabaseClient()
    transcripts_dir = "/home/dd/ekko_docker/app/transcripts/"
    
    # Load podcast tracker
    with open('/home/dd/ekko_docker/app/podcast_tracker.json', 'r') as f:
        podcast_tracker = json.load(f)
    
    # Iterate through episodes in the tracker
    for episode_title, episode_data in podcast_tracker.items():
        transcript_path = episode_data['transcript']
        transcript_filename = os.path.basename(transcript_path)
        
        # Construct full path to transcript
        full_transcript_path = os.path.join(os.path.dirname(transcripts_dir), transcript_filename)
        
        try:
            with open(full_transcript_path, 'r') as f:
                transcript_text = f.read()
            
            # Prepare metadata
            metadata = {
                'episode_title': episode_title,
                'mp3_url': episode_data['mp3_url'],
                'date': episode_data['date'],
                'duration': episode_data['duration'],
                'processed_date': episode_data['processed_date']
            }
            
            try:
                supabase.upload_transcript(
                    episode_title=episode_title,
                    transcript_text=transcript_text,
                    metadata=metadata
                )
                print(f"Uploaded transcript for {episode_title}")
            except Exception as e:
                print(f"Failed to upload {episode_title}: {str(e)}")
                
        except FileNotFoundError:
            print(f"Warning: Transcript file not found for {episode_title} at {full_transcript_path}")
        except Exception as e:
            print(f"Error reading transcript for {episode_title}: {str(e)}")

if __name__ == "__main__":
    upload_existing_transcripts()
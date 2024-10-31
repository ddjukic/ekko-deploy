import streamlit as st
from tools.feed_parser import DefaultFeedParserStrategy
from tools.summary_creator import TranscriptSummarizer
from tools.podcast_chatbot import ChatBotInterface
from tools.supabase_client import SupabaseClient
import readtime
import feedparser
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Optional
import tempfile
import os

@dataclass
class Episode:
    title: str
    publication_date: str
    duration: str
    html_content: str  # Store raw HTML content
    mp3_url: Optional[str] = None

# Initialize clients
supabase = SupabaseClient()
FEED_URL = "https://feeds.buzzsprout.com/763010.rss"

@st.cache_data
def get_episodes():
    try:
        feed_content = feedparser.parse(FEED_URL)
        enriched_episodes = []
        
        for entry in feed_content.entries[:106]:
            # Extract basic info
            title = entry.get('title', '').strip()
            published = entry.get('published', '')
            duration = entry.get('itunes_duration', '')
            
            # Get the raw HTML content
            html_content = entry.content[0].value if 'content' in entry and entry.content else entry.get('summary', '')
            
            # Format duration
            try:
                duration_secs = int(duration)
                minutes = duration_secs // 60
                duration_formatted = f"{minutes} minutes"
            except:
                duration_formatted = duration
            
            # Create serializable Episode object
            episode = Episode(
                title=title,
                publication_date=published,
                duration=duration_formatted,
                html_content=html_content,
                mp3_url=entry.links[0].href if entry.links else None
            )
            
            enriched_episodes.append(episode)
        
        # Sort by date (newest first)
        enriched_episodes.sort(
            key=lambda x: datetime.strptime(x.publication_date, '%a, %d %b %Y %H:%M:%S %z'), 
            reverse=True
        )
        
        st.write(f"Found {len(enriched_episodes)} episodes")
        return enriched_episodes
    
    except Exception as e:
        st.error(f"Error fetching episodes: {str(e)}")
        return []

def get_or_create_summary(episode_title: str, transcript_text: str):
    try:
        # Check if summary exists in Supabase
        existing_summary = supabase.get_summary(episode_title)
        if existing_summary:
            st.markdown("### Summary")
            st.markdown(existing_summary)
            st.write(f'Estimated reading time: {str(readtime.of_text(existing_summary).text)}')
            return existing_summary
        
        # Create new summary
        summarizer = TranscriptSummarizer(system_file_path='./tools/prompts/extrac_widom_refined_claude.md')
        
        # Stream the summary to the screen first
        st.markdown("### Summary")
        summary = st.write_stream(summarizer.summarize_transcript(transcript_text))
        st.write(f'Estimated reading time: {str(readtime.of_text(summary).text)}')
        
        # Store in Supabase after streaming is complete
        metadata = {'episode_title': episode_title}
        supabase.upload_summary(transcript_id=None, summary_text=summary, metadata=metadata)
        
        return summary
    except Exception as e:
        st.error(f"Error in summary creation: {str(e)}")
        return None
    
@st.fragment
def chat_with_podcast(transcript_text: str, episode_title: str):
    # Create a temporary file for the transcript
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
        # Write the transcript text to the temporary file
        tmp.write(transcript_text)
        tmp_path = tmp.name
        
        try:
            with st.spinner('Loading the chatbot...'):
                # Load the chatbot interface with the temporary file path
                chatbot = ChatBotInterface(
                    transcript_path=tmp_path
                )
                chatbot.chat(episode_title)
        finally:
            # Clean up the temporary file
            os.unlink(tmp_path)

def display_episodes(episodes):
    if not episodes:
        st.warning("No episodes found")
        return

    for idx, episode in enumerate(episodes):
        try:
            with st.expander(f":orange[**{episode.title}**]"):
                # Display metadata
                st.markdown(f"**Published on:** {episode.publication_date}")
                st.markdown(f"**Duration:** {episode.duration}")
                
                # Display HTML content directly
                st.html(episode.html_content)
                
                if st.button("Summarize & Chat", key=f"summarize_{episode.title}"):
                    transcript = supabase.get_transcript(episode.title)
                    
                    if transcript:
                        with st.spinner('Generating summary...'):
                            summary = get_or_create_summary(episode.title, transcript)
                            # if summary:
                            #     st.markdown("### Summary")
                            #     st.markdown(summary)
                            #     st.write(f'Estimated reading time: {str(readtime.of_text(summary).text)}')
                        
                        # Enable chat
                        chat_with_podcast(transcript, episode.title)
                    else:
                        st.error(f"Transcript not found for episode: {episode.title}")
        except Exception as e:
            st.error(f"Error processing episode {episode.title}: {str(e)}")

def main():
    st.title("Future Weekly Podcast Episode Summaries")
    
    # Load podcast feed
    st.write("Loading podcast feed...")  # Debug info
    episodes = get_episodes()
    
    # Display episodes
    display_episodes(episodes)

if __name__ == "__main__":
    main()
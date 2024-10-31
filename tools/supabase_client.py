from supabase import create_client
import streamlit as st

class SupabaseClient:
    def __init__(self):
        self.url = st.secrets["supabase"]["url"]
        self.key = st.secrets["supabase"]["key"]
        self.client = create_client(self.url, self.key)

    def upload_transcript(self, episode_title: str, transcript_text: str, metadata: dict):
        data = {
            'content': transcript_text,
            'metadata': metadata
        }
        return self.client.table('transcripts').insert(data).execute()

    def get_transcript(self, episode_title: str):
        response = self.client.table('transcripts')\
            .select('content')\
            .eq('metadata->>episode_title', episode_title)\
            .execute()
        return response.data[0]['content'] if response.data else None

    def upload_summary(self, transcript_id: str, summary_text: str, metadata: dict):
        data = {
            'transcript_id': transcript_id,
            'content': summary_text,
            'metadata': metadata
        }
        return self.client.table('summaries').insert(data).execute()

    def get_summary(self, episode_title: str):
        response = self.client.table('summaries')\
            .select('content')\
            .eq('metadata->>episode_title', episode_title)\
            .execute()
        return response.data[0]['content'] if response.data else None
import streamlit as st
from openai import OpenAI
import json

# TODO:
# - rename the 'system_content' and everything related to something more descriptive,
# like 'pattern' or whatever
class TranscriptSummarizer:
    """Summarizes podcast transcripts using the OpenAI API."""

    def __init__(self, model="gpt-4o", system_file_path="system.md", credentials_file_path="./ekko/ekko_prototype/creds/openai_credentials.json"):
        """Initialize the summarizer with the specified model, system file, and credentials file.

        Args:
            model (str): The model to use for the OpenAI API.
            system_file_path (str): The path to the system context file.
            credentials_file_path (str): The path to the JSON file containing the OpenAI API key.
        """
        self.model = model
        self.system_content = self._load_system_content(system_file_path)
        self.api_key = self._load_api_key(credentials_file_path)
        self.client = OpenAI(api_key=self.api_key)

    def _load_system_content(self, file_path):
        """Load the system context from a markdown file.

        Args:
            file_path (str): The path to the markdown file containing the system context.

        Returns:
            str: The content of the system context file.
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _load_api_key(self, file_path):
        """Load the OpenAI API key from a JSON file.

        Args:
            file_path (str): The path to the JSON file containing the OpenAI API key.

        Returns:
            str: The OpenAI API key.
        """
        with open(file_path, 'r') as file:
            credentials = json.load(file)
            return credentials['api_key']

    def summarize_transcript(self, transcript):
        """Summarize the provided transcript using the OpenAI API.

        Args:
            transcript (str): The transcript text to summarize.

        Returns:
            Generator: A generator that streams the response from the API.
        """
        system_message = {"role": "system", "content": self.system_content}
        user_message = {"role": "user", "content": transcript}
        messages = [system_message, user_message]


        try:
            response_stream = self.client.chat.completions.create(model=self.model,
            messages=messages,
            temperature=0.0,
            top_p=1,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            stream=True
            )
        except Exception as e:
            st.error(e)

        for chunk in response_stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

        
# Example usage:
# summarizer = TranscriptSummarizer()
# for summary_part in summarizer.summarize_transcript("Here is some transcript text..."):
#     print(summary_part)  # Or integrate with streaming in a web app

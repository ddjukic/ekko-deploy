import os
import logging
from groq import Groq
from pydub import AudioSegment
import tempfile
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GroqTranscriber:
    """
    A class to handle audio transcription using Groq's API.
    """

    def __init__(self, api_key: str):
        """
        Initialize the GroqTranscriber.

        :param api_key: The API key for Groq.
        :type api_key: str
        """
        self.client = Groq(api_key=api_key)
        self.model = 'distil-whisper-large-v3-en'

    def transcribe_episode(self, episode_url: str, episode_title: str, podcast_title: str) -> str:
        """
        Transcribe an entire podcast episode.

        :param episode_url: URL of the episode audio file.
        :type episode_url: str
        :param episode_title: Title of the episode.
        :type episode_title: str
        :param podcast_title: Title of the podcast.
        :type podcast_title: str
        :return: Path to the saved transcription file.
        :rtype: str
        """
        audio_file = self._download_audio(episode_url, podcast_title, episode_title)
        transcription = self.transcribe_long_audio(audio_file)
        transcription_file_path = self._save_transcription(transcription, podcast_title, episode_title)
        os.remove(audio_file)
        logging.info(f"Successfully transcribed episode: {episode_title} from podcast: {podcast_title}")
        return transcription_file_path

    def _download_audio(self, url: str, podcast_title: str, episode_title: str) -> str:
        """
        Download the audio file from the given URL.

        :param url: URL of the audio file.
        :type url: str
        :param podcast_title: Title of the podcast.
        :type podcast_title: str
        :param episode_title: Title of the episode.
        :type episode_title: str
        :return: Path to the downloaded audio file.
        :rtype: str
        :raises Exception: If the download fails.
        """
        response = requests.get(url)
        if response.status_code == 200:
            audio_dir = f"./audio/{podcast_title}"
            os.makedirs(audio_dir, exist_ok=True)
            audio_file = f"{audio_dir}/{episode_title}.mp3"
            with open(audio_file, "wb") as f:
                f.write(response.content)
            logging.info(f"Downloaded audio file: {audio_file}")
            return audio_file
        else:
            raise Exception(f"Failed to download audio file. Status code: {response.status_code}")

    def _save_transcription(self, transcription: str, podcast_title: str, episode_title: str) -> str:
        """
        Save the transcription to a file.

        :param transcription: The transcribed text.
        :type transcription: str
        :param podcast_title: Title of the podcast.
        :type podcast_title: str
        :param episode_title: Title of the episode.
        :type episode_title: str
        :return: Path to the saved transcription file.
        :rtype: str
        """
        transcription_dir = f"./transcripts/{podcast_title}"
        os.makedirs(transcription_dir, exist_ok=True)
        transcription_file = f"{transcription_dir}/{episode_title}.txt"
        with open(transcription_file, "w") as f:
            f.write(transcription)
        logging.info(f"Saved transcription to: {transcription_file}")
        return transcription_file

    def transcribe_audio(self, audio_file: str) -> str:
        """
        Transcribe a single audio file using Groq's API.

        :param audio_file: Path to the audio file.
        :type audio_file: str
        :return: The transcribed text.
        :rtype: str
        """
        with open(audio_file, "rb") as file:
            transcription = self.client.audio.transcriptions.create(
                file=(audio_file, file.read()),
                model=self.model,
            )
        return transcription.text

    def transcribe_long_audio(self, audio_file: str, chunk_length_ms: int = 10 * 60 * 1000) -> str:
        """
        Transcribe a long audio file by splitting it into chunks and processing them in parallel.

        :param audio_file: Path to the audio file.
        :type audio_file: str
        :param chunk_length_ms: Length of each chunk in milliseconds.
        :type chunk_length_ms: int
        :return: The complete transcribed text.
        :rtype: str
        """
        audio = AudioSegment.from_file(audio_file)
        chunks = self._split_audio(audio, chunk_length_ms)

        with ThreadPoolExecutor(max_workers=min(len(chunks), 10)) as executor:
            future_to_chunk = {executor.submit(self._transcribe_chunk, chunk, i): i for i, chunk in enumerate(chunks)}
            transcriptions = [None] * len(chunks)

            for future in as_completed(future_to_chunk):
                chunk_index = future_to_chunk[future]
                try:
                    transcriptions[chunk_index] = future.result()
                except Exception as exc:
                    logging.error(f'Chunk {chunk_index} generated an exception: {exc}')

        return " ".join(transcriptions)

    def _transcribe_chunk(self, chunk: AudioSegment, chunk_index: int) -> str:
        """
        Transcribe a single chunk of audio.

        :param chunk: The audio chunk to transcribe.
        :type chunk: AudioSegment
        :param chunk_index: The index of the chunk.
        :type chunk_index: int
        :return: The transcribed text for the chunk.
        :rtype: str
        """
        logging.info(f"Transcribing chunk {chunk_index + 1}...")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            chunk.export(temp_file.name, format="mp3")
            transcription = self.transcribe_audio(temp_file.name)
        os.unlink(temp_file.name)
        return transcription

    def _split_audio(self, audio: AudioSegment, chunk_length_ms: int) -> list:
        """
        Split the audio into chunks.

        :param audio: The full audio to split.
        :type audio: AudioSegment
        :param chunk_length_ms: Length of each chunk in milliseconds.
        :type chunk_length_ms: int
        :return: List of audio chunks.
        :rtype: list
        """
        chunks = []
        for i in range(0, len(audio), chunk_length_ms):
            chunks.append(audio[i:i+chunk_length_ms])
        return chunks
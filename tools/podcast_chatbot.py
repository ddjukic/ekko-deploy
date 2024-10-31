import os
import time
import json
import streamlit as st
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler


class ChatBotInterface:
    def __init__(self, transcript_path, model='gpt-4o'):
        """
        Initializes the chat bot interface with necessary paths and model.

        :param transcript_path: str
            Path to the text file containing the transcripts.
        :param model: str, optional
            The model identifier for the OpenAI API (default is 'gpt-3.5-turbo-0125').
        """
        self.transcript_path = transcript_path
        self.model = ChatOpenAI(
            model_name=model, 
            temperature=0,
            openai_api_key=st.secrets["openai"]["api_key"]
        )
        self.vectordb = self.setup_vector_db()
        self.qa_chain = self.setup_qa_chain()

    def load_and_split_transcript(self):
        """
        Loads and splits the transcript into manageable chunks.

        :return: list
            List of text chunks.
        """
        transcript = TextLoader(self.transcript_path).load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
        return text_splitter.split_documents(transcript)

    # TODO:
    # see how to check the documents present in the db and not load if already present
    def setup_vector_db(self):
        """
        Creates and returns a Chroma vector database from the split transcripts if not already loaded.

        :return: Chroma
            An instance of Chroma vector database.
        """
        persist_directory = './chroma/'

        # Only create vector DB if it does not already exist
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)

        documents = self.load_and_split_transcript()
        embeddings = OpenAIEmbeddings(openai_api_key=st.secrets["openai"]["api_key"])
        vectordb = Chroma.from_documents(documents=documents, embedding=embeddings, persist_directory=persist_directory)
        
        return vectordb

    def setup_qa_chain(self):
        """
        Sets up the retrieval-based Q&A chain.

        :return: RetrievalQA
            An instance of the RetrievalQA chain.
        """
        template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. Use three sentences maximum. Keep the answer as concise as possible.
            {context}
            Question: {question}
            Helpful Answer:"""
        qa_chain_prompt = PromptTemplate.from_template(template)

        return RetrievalQA.from_chain_type(
            self.model,
            retriever=self.vectordb.as_retriever(),
            return_source_documents=False,
            chain_type_kwargs={"prompt": qa_chain_prompt}
        )
    
    def reply_generator(self, query):
        """
        Generates a reply to the user query using the QA chain.

        :param query: str
            The user query.
        :return: str
            The reply generated by the QA chain.
        """
        reply = self.qa_chain({"query": query})['result']

        for word in reply.split():
            
            yield word + ' '
            time.sleep(0.01)

    # TODO:
    # debug the chat prompt window showing up at the -2 location instead of -1
    # - this is for sure again a re-running issue; it doesnt move after the reply comes in
    # because it cannot rerun fully (fragment rerun); might have to manually take care of it
    def chat(self, episode_title):
        """
        Runs the chat interface using Streamlit.
        """
        episode_title_friendly = '_'.join(episode_title.split())
        messages_key = f'messages_{episode_title_friendly}'
        if messages_key not in st.session_state:
            st.session_state[messages_key] = []

        # Display each message in the chat interface
        for message in st.session_state[messages_key]:
            with st.chat_message(message['role']):
                st.markdown(message['content'])

        # Get user input
        if prompt := st.chat_input("Chat with the episode:"):
            st.session_state[messages_key].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):    
            
                reply = st.write_stream(self.reply_generator(prompt))

            st.session_state[messages_key].append({"role": "assistant", "content": reply})

# if __name__ == "__main__":
#     credentials_path = '../creds/openai_credentials.json'
#     transcript_path = './transcripts/WSJ Minute Briefing.txt'
#     chat_bot = ChatBotInterface(credentials_path, transcript_path)
#     chat_bot.chat()

# credentials_path = '../creds/openai_credentials.json'
# transcript_path = './transcripts/WSJ Minute Briefing.txt'
# chat_bot = ChatBotInterface(credentials_path=credentials_path, transcript_path=transcript_path)
# chat_bot.chat()

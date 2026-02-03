"""
Note generation module that interfaces with Ollama API.
Handles the generation of structured meeting notes from transcripts.
"""

import requests
import json
from typing import List, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class NoteGenerationError(Exception):
    """Custom exception for note generation-related errors."""
    pass


class NoteGenerator:
    """Interfaces with Ollama API to generate structured meeting notes."""
    
    def __init__(self, ollama_host: str = "http://localhost:11434"):
        """
        Initialize the note generator with Ollama host.
        
        Args:
            ollama_host: URL of the Ollama API endpoint
        """
        self.ollama_host = ollama_host
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        # Define retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_available_models(self) -> List[str]:
        """
        Get a list of available Ollama models.
        
        Returns:
            List of model names available in Ollama
        """
        try:
            response = self.session.get(f"{self.ollama_host}/api/tags")
            response.raise_for_status()
            models_data = response.json()
            
            if "models" not in models_data:
                raise NoteGenerationError("Invalid response format from Ollama API")
                
            models = [model["name"] for model in models_data["models"]]
            return models
            
        except requests.exceptions.ConnectionError:
            raise NoteGenerationError("ERROR: Cannot connect to Ollama. Please ensure Ollama is installed and running (run 'ollama serve' in terminal). Visit https://ollama.ai to download and install Ollama.")
        except requests.exceptions.HTTPError as e:
            raise NoteGenerationError(f"ERROR: HTTP error from Ollama API: {e}")
        except requests.exceptions.RequestException as e:
            raise NoteGenerationError(f"ERROR: Request error when getting Ollama models: {e}")
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise NoteGenerationError(f"ERROR: Error parsing Ollama response: {e}")
    
    def generate_notes(self, transcript: str, system_prompt: str, model: str) -> str:
        """
        Generate structured meeting notes from a transcript.
        
        Args:
            transcript: The meeting transcript to process
            system_prompt: System prompt to guide the AI
            model: Ollama model to use for generation
            
        Returns:
            Generated meeting notes
        """
        try:
            payload = {
                "model": model,
                "prompt": transcript,
                "system": system_prompt,
                "stream": False
            }
            
            response = self.session.post(
                f"{self.ollama_host}/api/generate", 
                json=payload,
                timeout=300  # 5 minute timeout for long processing
            )
            response.raise_for_status()
            
            # Parse the response
            lines = response.text.strip().split('\n')
            final_response = json.loads(lines[-1])
            
            return final_response.get("response", "No response from model.")
            
        except requests.exceptions.ConnectionError:
            raise NoteGenerationError("Cannot connect to Ollama. Is it running?")
        except requests.exceptions.Timeout:
            raise NoteGenerationError("Request to Ollama timed out. The processing might be taking too long.")
        except requests.exceptions.HTTPError as e:
            raise NoteGenerationError(f"HTTP error from Ollama API: {e}")
        except requests.exceptions.RequestException as e:
            raise NoteGenerationError(f"Request error during note generation: {e}")
        except (json.JSONDecodeError, IndexError) as e:
            raise NoteGenerationError(f"Error decoding Ollama response: {e}")
        except KeyError as e:
            raise NoteGenerationError(f"Missing expected key in Ollama response: {e}")


if __name__ == '__main__':
    # This is for testing purposes.
    # You would need to have Ollama running.
    try:
        note_generator = NoteGenerator()
        models = note_generator.get_available_models()
        print("Available Ollama models:", models)

        if models:
            # This is a dummy transcript and system prompt for testing
            dummy_transcript = "Alice said hello. Bob said goodbye."
            dummy_system_prompt = "You are a meeting note-taking assistant. Summarize the conversation."
            notes = note_generator.generate_notes(dummy_transcript, dummy_system_prompt, models[0])
            print("\nGenerated Notes:")
            print(notes)

    except NoteGenerationError as e:
        print(f"Note generation error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
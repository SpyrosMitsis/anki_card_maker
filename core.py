"""
Core processing logic for Anki flashcard generation.
Refactored for better error handling, state management, and callback support.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, List, Dict
import json
import os
import re
import shutil
from pathlib import Path
from time import sleep
from datetime import datetime

from tts import generate as tts_generate
from gemini import generate as g_generate
from py_ankiconnect import PyAnkiconnect
from google.genai.errors import ClientError


class ProcessingState(Enum):
    """Current state of the processing pipeline."""
    IDLE = "idle"
    READING_WORDS = "reading_words"
    GENERATING_CONTENT = "generating_content"
    GENERATING_AUDIO = "generating_audio"
    COPYING_AUDIO = "copying_audio"
    SENDING_TO_ANKI = "sending_to_anki"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessingStats:
    """Statistics about the current processing run."""
    total_words: int = 0
    processed_words: int = 0
    failed_words: int = 0
    skipped_words: int = 0
    current_word: Optional[str] = None
    estimated_time_remaining: Optional[float] = None
    start_time: Optional[datetime] = None


@dataclass
class GeneratorConfig:
    """Configuration for the flashcard generator."""
    words_file: str = "./words.txt"
    deck_name: str = "Danish vocab"
    model_name: str = "Danish"
    reverse_model_name: str = "Danish Reverse"
    audio_dir: str = "./audio"
    audio_cache_dir: str = "./audio_cache"
    checkpoint_file: str = "./checkpoint.json"
    tts_delay: float = 6.5  # seconds between TTS requests
    skip_existing_audio: bool = False
    test_mode: bool = False
    generate_reverse_cards: bool = False


@dataclass
class FlashcardData:
    """Data for a single flashcard."""
    word: str
    translation: str
    example_sentence_da: str
    example_sentence_en: str
    audio_word_file: Optional[str] = None
    audio_sentence_file: Optional[str] = None
    error: Optional[str] = None


class AnkiFlashcardGenerator:
    """Main generator class with improved error handling and state management."""
    
    GEMINI_PROMPT = """
You are a helpful Danish language assistant.
Your task is to take a Danish word and:
1. Create a simple, natural example sentence in Danish using that word.
2. Provide the English translation of the word.
3. Provide the English translation of the example sentence.
4. The word must include the article and the plural form.

Return your output in strict JSON format, following exactly this structure (use double quotes and proper JSON syntax):
{{
  "word": "<the Danish word with the article and the plural form>",
  "translation": "<English translation of the word>",
  "example_sentence_da": "<Danish example sentence>",
  "example_sentence_en": "<English translation of the example sentence>"
}}

Important:
- Do NOT include any text before or after the JSON.
- Make the the target word in the example sentence BOLD using <b></b> tag. 
- Make the the target word in the translation sentence BOLD using <b></b> tag. 
- Do not using any markup apart from the <b></b> tag already mentioned above.
- Do NOT write ```json before the JSON.

Input word: {word}
"""
    
    def __init__(
        self, 
        config: GeneratorConfig,
        callback: Optional[Callable[[ProcessingState, ProcessingStats, str], None]] = None
    ):
        """
        Initialize the generator.
        
        Args:
            config: Generator configuration
            callback: Optional callback function for progress updates
                      Signature: (state, stats, message) -> None
        """
        self.config = config
        self.callback = callback
        self.stats = ProcessingStats()
        self.state = ProcessingState.IDLE
        self.cancelled = False
        
        # Ensure directories exist
        os.makedirs(self.config.audio_dir, exist_ok=True)
        os.makedirs(self.config.audio_cache_dir, exist_ok=True)
        
        # Load checkpoint if exists
        self.checkpoint: Dict[str, FlashcardData] = {}
        self.load_checkpoint()
        
        # Load audio cache metadata
        self.audio_cache_metadata = self.load_audio_cache_metadata()
    
    def load_audio_cache_metadata(self) -> dict:
        """Load audio cache metadata (maps audio hash to filename)."""
        metadata_file = os.path.join(self.config.audio_cache_dir, "cache_metadata.json")
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self._log(f"⚠️ Could not load audio cache metadata: {e}")
        return {}
    
    def save_audio_cache_metadata(self):
        """Save audio cache metadata."""
        metadata_file = os.path.join(self.config.audio_cache_dir, "cache_metadata.json")
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.audio_cache_metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log(f"⚠️ Could not save audio cache metadata: {e}")
    
    def get_audio_cache_key(self, text: str) -> str:
        """Generate a cache key for audio based on text content."""
        import hashlib
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def get_cached_audio(self, text: str) -> Optional[str]:
        """Check if audio for this text exists in cache."""
        cache_key = self.get_audio_cache_key(text)
        if cache_key in self.audio_cache_metadata:
            cached_file = self.audio_cache_metadata[cache_key]
            cached_path = os.path.join(self.config.audio_cache_dir, cached_file)
            if os.path.exists(cached_path):
                return cached_file
        return None
    
    def cache_audio(self, text: str, source_filename: str):
        """Cache an audio file with its text content."""
        cache_key = self.get_audio_cache_key(text)
        source_path = os.path.join(self.config.audio_dir, source_filename)
        
        # Generate cache filename
        cache_filename = f"{cache_key}.wav"
        cache_path = os.path.join(self.config.audio_cache_dir, cache_filename)
        
        # Copy to cache if source exists
        if os.path.exists(source_path):
            shutil.copy2(source_path, cache_path)
            self.audio_cache_metadata[cache_key] = cache_filename
            self.save_audio_cache_metadata()
            return cache_filename
        
        # Check for .wav.wav extension issue
        source_alt = source_path + ".wav"
        if os.path.exists(source_alt):
            shutil.copy2(source_alt, cache_path)
            self.audio_cache_metadata[cache_key] = cache_filename
            self.save_audio_cache_metadata()
            return cache_filename
        
        return None
    
    def _update_state(self, state: ProcessingState, message: str = ""):
        """Update state and notify callback."""
        self.state = state
        if self.callback:
            self.callback(state, self.stats, message)
    
    def _log(self, message: str):
        """Log a message via callback."""
        if self.callback:
            self.callback(self.state, self.stats, message)
    
    def cancel(self):
        """Request cancellation of processing."""
        self.cancelled = True
        self._update_state(ProcessingState.CANCELLED, "⏹️ Cancelling...")
    
    def load_checkpoint(self):
        """Load checkpoint from file if exists."""
        if os.path.exists(self.config.checkpoint_file):
            try:
                with open(self.config.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    # Convert dict to FlashcardData objects
                    self.checkpoint = {
                        k: FlashcardData(**v) for k, v in data.items()
                    }
                self._log(f"📂 Loaded checkpoint with {len(self.checkpoint)} completed words")
            except Exception as e:
                self._log(f"⚠️ Could not load checkpoint: {e}")
    
    def save_checkpoint(self):
        """Save current progress to checkpoint file."""
        try:
            # Convert FlashcardData objects to dicts
            data = {
                k: {
                    'word': v.word,
                    'translation': v.translation,
                    'example_sentence_da': v.example_sentence_da,
                    'example_sentence_en': v.example_sentence_en,
                    'audio_word_file': v.audio_word_file,
                    'audio_sentence_file': v.audio_sentence_file,
                    'error': v.error
                }
                for k, v in self.checkpoint.items()
            }
            
            with open(self.config.checkpoint_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self._log(f"⚠️ Could not save checkpoint: {e}")
    
    def read_words(self) -> List[str]:
        """Read words from file."""
        self._update_state(ProcessingState.READING_WORDS, "📖 Reading words from file...")
        
        if not os.path.exists(self.config.words_file):
            raise FileNotFoundError(f"Words file not found: {self.config.words_file}")
        
        words = []
        with open(self.config.words_file, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith('#'):
                    words.append(word)
        
        self._log(f"✅ Loaded {len(words)} words from {self.config.words_file}")
        return words
    
    @staticmethod
    def normalize_filename(text: str) -> str:
        """Normalize text to safe filename."""
        text = re.sub(r"<.*?>", "", text)
        text = re.sub(r"\s+", "_", text)
        text = re.sub(r"[^a-zA-Z0-9_-]", "", text)
        return text
    
    def generate_content_for_word(self, word: str) -> Optional[FlashcardData]:
        """Generate flashcard content for a single word using Gemini."""
        # Check if already in checkpoint
        if word in self.checkpoint:
            self._log(f"⏭️ Skipping {word} (already processed)")
            return self.checkpoint[word]
        
        self.stats.current_word = word
        self._update_state(ProcessingState.GENERATING_CONTENT, f"🤖 Generating content for: {word}")
        
        try:
            prompt = self.GEMINI_PROMPT.format(word=word)
            response = g_generate(prompt)
            
            # Parse JSON response
            data = json.loads(response)
            
            flashcard = FlashcardData(
                word=data['word'],
                translation=data['translation'],
                example_sentence_da=data['example_sentence_da'],
                example_sentence_en=data['example_sentence_en']
            )
            
            self._log(f"✅ Generated content for: {word}")
            return flashcard
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON for {word}"
            self._log(f"❌ {error_msg}")
            return FlashcardData(
                word=word,
                translation="",
                example_sentence_da="",
                example_sentence_en="",
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Error generating content for {word}: {str(e)}"
            self._log(f"❌ {error_msg}")
            return FlashcardData(
                word=word,
                translation="",
                example_sentence_da="",
                example_sentence_en="",
                error=error_msg
            )
    
    def generate_audio_for_flashcard(self, flashcard: FlashcardData) -> bool:
        """Generate TTS audio for a flashcard, using cache when possible."""
        if self.cancelled:
            return False
        
        if flashcard.error:
            return False
        
        word_file = self.normalize_filename(flashcard.word)
        sentence_file = self.normalize_filename(flashcard.word) + "_sentence"
        
        word_path = os.path.join(self.config.audio_dir, f"{word_file}.wav")
        sentence_path = os.path.join(self.config.audio_dir, f"{sentence_file}.wav")
        
        # Generate word audio
        word_cached = self.get_cached_audio(flashcard.word)
        if word_cached:
            # Copy from cache to audio directory
            cache_path = os.path.join(self.config.audio_cache_dir, word_cached)
            shutil.copy2(cache_path, word_path)
            flashcard.audio_word_file = f"{word_file}.wav"
            self._log(f"📦 Using cached audio for word: {flashcard.word}")
        else:
            # Generate new audio
            self._update_state(
                ProcessingState.GENERATING_AUDIO,
                f"🎤 Generating audio for word: {flashcard.word}"
            )
            
            try:
                tts_generate(flashcard.word, filename=word_file)
                flashcard.audio_word_file = f"{word_file}.wav"
                
                # Cache the audio
                self.cache_audio(flashcard.word, f"{word_file}.wav")
                
                self._log(f"🔊 Generated audio for word: {flashcard.word}")
                
                if not self.cancelled:
                    sleep(self.config.tts_delay)
                
            except ClientError as e:
                if e.status_code == 429:
                    self._log(f"⚠️ Rate limit hit, retrying in 20s...")
                    sleep(20)
                    try:
                        tts_generate(flashcard.word, filename=word_file)
                        flashcard.audio_word_file = f"{word_file}.wav"
                        self.cache_audio(flashcard.word, f"{word_file}.wav")
                        sleep(self.config.tts_delay)
                    except Exception as retry_error:
                        flashcard.error = f"Failed to generate word audio: {retry_error}"
                        return False
                else:
                    flashcard.error = f"TTS error: {e}"
                    return False
            except Exception as e:
                flashcard.error = f"Error generating word audio: {e}"
                return False
        
        if self.cancelled:
            return False
        
        # Generate sentence audio - ALWAYS generate fresh (don't cache sentences)
        # because the same word can have different sentences
        self._update_state(
            ProcessingState.GENERATING_AUDIO,
            f"🎤 Generating audio for sentence: {flashcard.word}"
        )
        
        try:
            tts_generate(flashcard.example_sentence_da, filename=sentence_file)
            flashcard.audio_sentence_file = f"{sentence_file}.wav"
            self._log(f"🔊 Generated audio for sentence: {flashcard.word}")
            
            if not self.cancelled:
                sleep(self.config.tts_delay)
            
        except ClientError as e:
            if e.status_code == 429:
                self._log(f"⚠️ Rate limit hit, retrying in 20s...")
                sleep(20)
                try:
                    tts_generate(flashcard.example_sentence_da, filename=sentence_file)
                    flashcard.audio_sentence_file = f"{sentence_file}.wav"
                    sleep(self.config.tts_delay)
                except Exception as retry_error:
                    flashcard.error = f"Failed to generate sentence audio: {retry_error}"
                    return False
            else:
                flashcard.error = f"TTS error: {e}"
                return False
        except Exception as e:
            flashcard.error = f"Error generating sentence audio: {e}"
            return False
        
        return True
    
    def get_anki_media_dir(self) -> str:
        """Get Anki's media directory path."""
        akc = PyAnkiconnect()
        try:
            return akc(action="getMediaDirPath")
        except Exception as e:
            self._log(f"⚠️ Could not get Anki media directory: {e}")
            # Fallback to common locations
            import platform
            system = platform.system()
            home = os.path.expanduser("~")
            
            if system == "Windows":
                return os.path.join(home, "AppData", "Roaming", "Anki2", "User 1", "collection.media")
            elif system == "Darwin":
                return os.path.join(home, "Library", "Application Support", "Anki2", "User 1", "collection.media")
            else:
                return os.path.join(home, ".local", "share", "Anki2", "User 1", "collection.media")
    
    def copy_audio_to_anki(self, flashcards: List[FlashcardData]) -> bool:
        """Copy audio files to Anki's media directory."""
        self._update_state(ProcessingState.COPYING_AUDIO, "📁 Copying audio to Anki...")
        
        anki_media_dir = self.get_anki_media_dir()
        
        if not os.path.exists(anki_media_dir):
            self._log(f"❌ Anki media directory not found: {anki_media_dir}")
            return False
        
        self._log(f"📂 Anki media directory: {anki_media_dir}")
        
        for flashcard in flashcards:
            if flashcard.error or self.cancelled:
                continue
            
            if flashcard.audio_word_file:
                source = os.path.join(self.config.audio_dir, flashcard.audio_word_file)
                dest = os.path.join(anki_media_dir, flashcard.audio_word_file)
                
                # Handle .wav.wav extension issue
                if not os.path.exists(source):
                    source_alt = source + ".wav"
                    if os.path.exists(source_alt):
                        source = source_alt
                
                if os.path.exists(source):
                    shutil.copy2(source, dest)
                    self._log(f"✓ Copied {os.path.basename(source)}")
            
            if flashcard.audio_sentence_file:
                source = os.path.join(self.config.audio_dir, flashcard.audio_sentence_file)
                dest = os.path.join(anki_media_dir, flashcard.audio_sentence_file)
                
                # Handle .wav.wav extension issue
                if not os.path.exists(source):
                    source_alt = source + ".wav"
                    if os.path.exists(source_alt):
                        source = source_alt
                
                if os.path.exists(source):
                    shutil.copy2(source, dest)
                    self._log(f"✓ Copied {os.path.basename(source)}")
        
        return True
    
    def send_to_anki(self, flashcards: List[FlashcardData]):
        """Send flashcards to Anki, including reverse cards if configured."""
        self._update_state(ProcessingState.SENDING_TO_ANKI, "📤 Sending cards to Anki...")
        
        akc = PyAnkiconnect()
        
        for flashcard in flashcards:
            if flashcard.error or self.cancelled:
                continue
            
            # Create forward card
            note = {
                "deckName": self.config.deck_name,
                "modelName": self.config.model_name,
                "fields": {
                    "Word": f"<b>{flashcard.word}</b>",
                    "Danish Sentence": flashcard.example_sentence_da,
                    "Word Translation": f"<b>{flashcard.translation}</b>",
                    "Sentence Translation": flashcard.example_sentence_en,
                    "Audio": f"[sound:{flashcard.audio_word_file}]" if flashcard.audio_word_file else "",
                    "Sentence Audio": f"[sound:{flashcard.audio_sentence_file}]" if flashcard.audio_sentence_file else ""
                },
                "options": {
                    "allowDuplicate": False
                }
            }
            
            try:
                response = akc(action="addNote", note=note)
                self._log(f"✅ Added forward card for: {flashcard.word}")
            except Exception as e:
                self._log(f"❌ Failed to add forward card for {flashcard.word}: {e}")
                flashcard.error = str(e)
                continue
            
            # Create reverse card if enabled
            if self.config.generate_reverse_cards:
                reverse_note = {
                    "deckName": self.config.deck_name,
                    "modelName": self.config.reverse_model_name,
                    "fields": {
                        "English": f"<b>{flashcard.translation}</b>",
                        "English Sentence": flashcard.example_sentence_en,
                        "Danish Word": f"<b>{flashcard.word}</b>",
                        "Danish Sentence": flashcard.example_sentence_da,
                        "Audio": f"[sound:{flashcard.audio_word_file}]" if flashcard.audio_word_file else "",
                        "Sentence Audio": f"[sound:{flashcard.audio_sentence_file}]" if flashcard.audio_sentence_file else ""
                    },
                    "options": {
                        "allowDuplicate": False
                    }
                }
                
                try:
                    response = akc(action="addNote", note=reverse_note)
                    self._log(f"✅ Added reverse card for: {flashcard.word}")
                except Exception as e:
                    self._log(f"⚠️ Failed to add reverse card for {flashcard.word}: {e}")
    
    def run(self):
        """Main execution flow."""
        self.stats.start_time = datetime.now()
        
        try:
            # Read words
            words = self.read_words()
            self.stats.total_words = len(words)
            
            if not words:
                raise ValueError("No words to process")
            
            flashcards: List[FlashcardData] = []
            
            # Generate content
            for i, word in enumerate(words, 1):
                if self.cancelled:
                    break
                
                self._log(f"[{i}/{len(words)}] Processing: {word}")
                
                flashcard = self.generate_content_for_word(word)
                if flashcard:
                    flashcards.append(flashcard)
                    if not flashcard.error:
                        self.checkpoint[word] = flashcard
                        self.save_checkpoint()
                    else:
                        self.stats.failed_words += 1
                else:
                    self.stats.failed_words += 1
                
                self.stats.processed_words = i
            
            if self.cancelled:
                return
            
            # Generate audio (unless in test mode)
            if not self.config.test_mode:
                for i, flashcard in enumerate(flashcards, 1):
                    if self.cancelled:
                        break
                    
                    if flashcard.error:
                        continue
                    
                    # Update time estimate
                    remaining_audio = (len(flashcards) - i) * 2  # 2 audio files per card
                    self.stats.estimated_time_remaining = remaining_audio * self.config.tts_delay
                    
                    success = self.generate_audio_for_flashcard(flashcard)
                    if not success:
                        self.stats.failed_words += 1
            
            if self.cancelled:
                return
            
            # Copy audio and send to Anki
            if self.copy_audio_to_anki(flashcards):
                self.send_to_anki(flashcards)
            
            # Final statistics
            successful = len([f for f in flashcards if not f.error])
            self._update_state(
                ProcessingState.COMPLETED,
                f"🎉 Completed! {successful}/{len(flashcards)} cards successfully created."
            )
            
            # Clean up checkpoint on success
            if os.path.exists(self.config.checkpoint_file):
                os.remove(self.config.checkpoint_file)
            
        except Exception as e:
            self._update_state(ProcessingState.FAILED, f"❌ Error: {str(e)}")
            raise

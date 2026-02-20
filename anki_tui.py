"""
Anki Danish Vocabulary Generator - TUI Application
A beautiful text-based interface for generating Anki flashcards with audio.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header, Footer, Button, Static, Label, 
    Input, ProgressBar, Log, Switch
)
from textual.binding import Binding
from textual.reactive import reactive
from textual import work
from textual.worker import Worker, WorkerState

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import asyncio

from core import (
    AnkiFlashcardGenerator,
    GeneratorConfig,
    ProcessingState,
    ProcessingStats
)


class StatusPanel(Static):
    """Display current processing status and statistics."""
    
    stats: reactive[Optional[ProcessingStats]] = reactive(None)
    state: reactive[ProcessingState] = reactive(ProcessingState.IDLE)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Status"
    
    def render(self) -> str:
        if not self.stats:
            return "[dim]Waiting to start...[/dim]"
        
        status_emoji = {
            ProcessingState.IDLE: "⏸️",
            ProcessingState.READING_WORDS: "📖",
            ProcessingState.GENERATING_CONTENT: "🤖",
            ProcessingState.GENERATING_AUDIO: "🎤",
            ProcessingState.COPYING_AUDIO: "📁",
            ProcessingState.SENDING_TO_ANKI: "📤",
            ProcessingState.COMPLETED: "✅",
            ProcessingState.FAILED: "❌",
            ProcessingState.CANCELLED: "⏹️"
        }
        
        emoji = status_emoji.get(self.state, "⏳")
        state_text = self.state.value.replace("_", " ").title()
        
        lines = [
            f"{emoji} [bold]{state_text}[/bold]",
            "",
            f"Total Words: [cyan]{self.stats.total_words}[/cyan]",
            f"Processed: [green]{self.stats.processed_words}[/green]",
            f"Failed: [red]{self.stats.failed_words}[/red]",
            f"Skipped: [yellow]{self.stats.skipped_words}[/yellow]",
            "",
        ]
        
        if self.stats.current_word:
            lines.append(f"Current: [bold]{self.stats.current_word}[/bold]")
        
        if self.stats.estimated_time_remaining and self.state == ProcessingState.GENERATING_AUDIO:
            mins = int(self.stats.estimated_time_remaining / 60)
            secs = int(self.stats.estimated_time_remaining % 60)
            lines.append(f"Est. Time: [dim]{mins}m {secs}s[/dim]")
        
        return "\n".join(lines)


class ConfigPanel(Vertical):
    """Configuration panel for user inputs."""
    
    def compose(self) -> ComposeResult:
        yield Static("📝 Configuration", classes="panel-title")
        
        with Container(classes="config-section"):
            yield Label("Words File:")
            yield Input(
                placeholder="./words.txt",
                value="./words.txt",
                id="words_file"
            )
            yield Button("Browse...", id="browse_words", variant="default")
        
        with Container(classes="config-section"):
            yield Label("Anki Deck:")
            yield Input(
                placeholder="Danish vocab",
                value="Danish vocab",
                id="deck_name"
            )
        
        with Container(classes="config-section"):
            yield Label("Card Model:")
            yield Input(
                placeholder="Danish",
                value="Danish",
                id="model_name"
            )
        
        with Container(classes="config-section"):
            yield Label("Reverse Card Model:")
            yield Input(
                placeholder="Danish Reverse",
                value="Danish Reverse",
                id="reverse_model_name"
            )
        
        with Container(classes="config-section"):
            yield Label("Audio Directory:")
            yield Input(
                placeholder="./audio",
                value="./audio",
                id="audio_dir"
            )
        
        with Container(classes="config-section"):
            yield Label("Audio Cache Directory:")
            yield Input(
                placeholder="./audio_cache",
                value="./audio_cache",
                id="audio_cache_dir"
            )
        
        with Horizontal(classes="config-section"):
            yield Label("Generate Reverse Cards:")
            yield Switch(value=False, id="generate_reverse")
        
        with Horizontal(classes="config-section"):
            yield Label("Skip Existing Audio:")
            yield Switch(value=False, id="skip_existing")
        
        with Horizontal(classes="config-section"):
            yield Label("Test Mode (use existing audio):")
            yield Switch(value=False, id="test_mode")


class LogPanel(VerticalScroll):
    """Scrollable log panel for detailed output."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Activity Log"
        self.log_widget = Log(highlight=True)
    
    def compose(self) -> ComposeResult:
        yield self.log_widget
    
    def write(self, message: str):
        """Write a message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_widget.write_line(f"[dim]{timestamp}[/dim] {message}")


class ProgressPanel(Vertical):
    """Progress bars for overall and current operation."""
    
    total_progress: reactive[float] = reactive(0.0)
    operation_progress: reactive[float] = reactive(0.0)
    
    def compose(self) -> ComposeResult:
        yield Static("Overall Progress", classes="progress-label")
        yield ProgressBar(total=100, show_eta=False, id="total_progress")
        
        yield Static("Current Operation", classes="progress-label")
        yield ProgressBar(total=100, show_eta=False, id="operation_progress")
    
    def watch_total_progress(self, progress: float) -> None:
        """Update total progress bar."""
        bar = self.query_one("#total_progress", ProgressBar)
        bar.update(progress=progress)
    
    def watch_operation_progress(self, progress: float) -> None:
        """Update operation progress bar."""
        bar = self.query_one("#operation_progress", ProgressBar)
        bar.update(progress=progress)


class AnkiGeneratorApp(App):
    """Main TUI application for Anki flashcard generation."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .panel-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .config-section {
        height: auto;
        margin: 1 0;
    }
    
    ConfigPanel {
        width: 40;
        height: 100%;
        border: solid $primary;
        padding: 1 2;
        overflow-y: auto;
    }
    
    #main_content {
        height: 100%;
    }
    
    #right_panel {
        width: 1fr;
        height: 100%;
    }
    
    StatusPanel {
        height: 15;
        border: solid $accent;
        padding: 1 2;
        margin-bottom: 1;
    }
    
    ProgressPanel {
        height: 10;
        border: solid $primary;
        padding: 1 2;
        margin-bottom: 1;
    }
    
    .progress-label {
        color: $text-muted;
        margin-top: 1;
    }
    
    LogPanel {
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
    }
    
    #controls {
        height: auto;
        width: 100%;
        align: center middle;
        padding: 1 0;
    }
    
    #controls Button {
        margin: 0 1;
    }
    
    Input {
        width: 100%;
        margin-bottom: 1;
    }
    
    Switch {
        margin-left: 2;
    }
    
    Label {
        width: auto;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("s", "start", "Start", show=True),
        Binding("c", "cancel", "Cancel", show=False),
    ]
    
    TITLE = "Anki Danish Vocabulary Generator"
    
    def __init__(self):
        super().__init__()
        self.generator: Optional[AnkiFlashcardGenerator] = None
        self.current_worker: Optional[Worker] = None
        self.is_processing = False
        
        # Load saved theme
        self.load_theme()
    
    def load_theme(self):
        """Load saved theme from settings file."""
        settings_file = Path("app_settings.json")
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    saved_theme = settings.get("theme")
                    if saved_theme:
                        self.theme = saved_theme
            except Exception:
                pass  # Use default theme if loading fails
    
    def save_theme(self, theme_name: str):
        """Save current theme to settings file."""
        settings_file = Path("app_settings.json")
        settings = {}
        
        # Load existing settings
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            except Exception:
                pass
        
        # Update theme
        settings["theme"] = theme_name
        
        # Save
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.write_log(f"⚠️ Could not save theme: {e}")
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal(id="main_content"):
            yield ConfigPanel(id="config_panel")
            
            with Vertical(id="right_panel"):
                yield StatusPanel(id="status_panel")
                yield ProgressPanel(id="progress_panel")
                yield LogPanel(id="log_panel")
                
                with Horizontal(id="controls"):
                    yield Button("🚀 Start Processing", id="start_btn", variant="success")
                    yield Button("⏹️ Cancel", id="cancel_btn", variant="error", disabled=True)
                    yield Button("📋 Load Config", id="load_config_btn", variant="default")
                    yield Button("💾 Save Config", id="save_config_btn", variant="default")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        self.write_log("Welcome to Anki Danish Vocabulary Generator! 🎉")
        self.write_log("Configure your settings on the left and click Start Processing.")
        self.write_log("💡 Tip: Press Ctrl+P for themes and commands")
        
        # Load config if exists
        if Path("config.json").exists():
            self.load_config_from_file()
    
    def watch_theme(self, theme: str) -> None:
        """Watch for theme changes and save them."""
        self.save_theme(theme)
    
    def write_log(self, message: str):
        """Write a message to the log panel."""
        log_panel = self.query_one("#log_panel", LogPanel)
        log_panel.write(message)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id
        
        if button_id == "start_btn":
            self.action_start()
        elif button_id == "cancel_btn":
            self.action_cancel()
        elif button_id == "browse_words":
            self.browse_words_file()
        elif button_id == "load_config_btn":
            self.load_config_from_file()
        elif button_id == "save_config_btn":
            self.save_config_to_file()
    
    def browse_words_file(self):
        """Browse for words file (simulated - shows available .txt files)."""
        txt_files = list(Path(".").glob("*.txt"))
        if txt_files:
            self.write_log(f"Found .txt files: {', '.join([f.name for f in txt_files])}")
            self.write_log("Update the 'Words File' field with your chosen file.")
        else:
            self.write_log("No .txt files found in current directory.")
    
    def get_config(self) -> GeneratorConfig:
        """Get configuration from input fields."""
        words_file = self.query_one("#words_file", Input).value or "./words.txt"
        deck_name = self.query_one("#deck_name", Input).value or "Danish vocab"
        model_name = self.query_one("#model_name", Input).value or "Danish"
        reverse_model_name = self.query_one("#reverse_model_name", Input).value or "Danish Reverse"
        audio_dir = self.query_one("#audio_dir", Input).value or "./audio"
        audio_cache_dir = self.query_one("#audio_cache_dir", Input).value or "./audio_cache"
        skip_existing = self.query_one("#skip_existing", Switch).value
        test_mode = self.query_one("#test_mode", Switch).value
        generate_reverse = self.query_one("#generate_reverse", Switch).value
        
        return GeneratorConfig(
            words_file=words_file,
            deck_name=deck_name,
            model_name=model_name,
            reverse_model_name=reverse_model_name,
            audio_dir=audio_dir,
            audio_cache_dir=audio_cache_dir,
            skip_existing_audio=skip_existing,
            test_mode=test_mode,
            generate_reverse_cards=generate_reverse
        )
    
    def save_config_to_file(self):
        """Save current configuration to config.json."""
        config = self.get_config()
        
        config_data = {
            "words_file": config.words_file,
            "deck_name": config.deck_name,
            "model_name": config.model_name,
            "reverse_model_name": config.reverse_model_name,
            "audio_dir": config.audio_dir,
            "audio_cache_dir": config.audio_cache_dir,
            "skip_existing_audio": config.skip_existing_audio,
            "test_mode": config.test_mode,
            "generate_reverse_cards": config.generate_reverse_cards
        }
        
        with open("config.json", "w") as f:
            json.dump(config_data, f, indent=2)
        
        self.write_log("✅ Configuration saved to config.json")
    
    def load_config_from_file(self):
        """Load configuration from config.json."""
        try:
            with open("config.json", "r") as f:
                config_data = json.load(f)
            
            self.query_one("#words_file", Input).value = config_data.get("words_file", "./words.txt")
            self.query_one("#deck_name", Input).value = config_data.get("deck_name", "Danish vocab")
            self.query_one("#model_name", Input).value = config_data.get("model_name", "Danish")
            self.query_one("#reverse_model_name", Input).value = config_data.get("reverse_model_name", "Danish Reverse")
            self.query_one("#audio_dir", Input).value = config_data.get("audio_dir", "./audio")
            self.query_one("#audio_cache_dir", Input).value = config_data.get("audio_cache_dir", "./audio_cache")
            self.query_one("#skip_existing", Switch).value = config_data.get("skip_existing_audio", False)
            self.query_one("#test_mode", Switch).value = config_data.get("test_mode", False)
            self.query_one("#generate_reverse", Switch).value = config_data.get("generate_reverse_cards", False)
            
            self.write_log("✅ Configuration loaded from config.json")
        except FileNotFoundError:
            self.write_log("⚠️ No config.json found")
        except Exception as e:
            self.write_log(f"❌ Error loading config: {e}")
    
    def action_start(self) -> None:
        """Start processing flashcards."""
        if self.is_processing:
            self.write_log("⚠️ Already processing!")
            return
        
        self.is_processing = True
        self.query_one("#start_btn", Button).disabled = True
        self.query_one("#cancel_btn", Button).disabled = False
        
        self.write_log("🚀 Starting flashcard generation...")
        
        # Start the worker
        self.run_generator()
    
    @work(exclusive=True, thread=True)
    def run_generator(self):
        """Run the generator in a background thread."""
        config = self.get_config()
        
        try:
            self.generator = AnkiFlashcardGenerator(config, callback=self.update_progress)
            self.generator.run()
            
            # Update final state
            self.call_from_thread(self.on_generation_complete, success=True)
            
        except Exception as e:
            self.call_from_thread(self.write_log, f"❌ Error: {str(e)}")
            self.call_from_thread(self.on_generation_complete, success=False)
    
    def update_progress(self, state: ProcessingState, stats: ProcessingStats, message: str):
        """Callback for progress updates from generator."""
        # Update status panel
        status_panel = self.query_one("#status_panel", StatusPanel)
        status_panel.stats = stats
        status_panel.state = state
        
        # Update progress bars
        progress_panel = self.query_one("#progress_panel", ProgressPanel)
        if stats.total_words > 0:
            total_pct = (stats.processed_words / stats.total_words) * 100
            progress_panel.total_progress = total_pct
        
        # Update log
        if message:
            self.write_log(message)
    
    def on_generation_complete(self, success: bool):
        """Called when generation completes."""
        self.is_processing = False
        self.query_one("#start_btn", Button).disabled = False
        self.query_one("#cancel_btn", Button).disabled = True
        
        if success:
            self.write_log("🎉 All done! Flashcards have been added to Anki.")
        else:
            self.write_log("⚠️ Processing ended with errors. Check the log for details.")
    
    def action_cancel(self) -> None:
        """Cancel processing."""
        if self.generator:
            self.generator.cancel()
            self.write_log("⏹️ Cancellation requested...")
    
    def action_quit(self) -> None:
        """Quit the application."""
        if self.is_processing:
            self.write_log("⚠️ Processing in progress. Cancel first or force quit with Ctrl+C")
            return
        self.exit()


def main():
    """Run the TUI application."""
    app = AnkiGeneratorApp()
    app.run()


if __name__ == "__main__":
    main()

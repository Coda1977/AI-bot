"""
Configuration Management for Manager AI Assistant
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AIConfig(BaseModel):
    """AI Provider configuration"""
    provider: str = Field(default="anthropic", description="AI provider: anthropic, openai, or gemini")
    api_key: Optional[str] = Field(default=None, description="API key for the AI provider")
    model: Optional[str] = Field(default=None, description="Specific model name")

    def get_default_model(self) -> str:
        """Get default model for the provider"""
        defaults = {
            'anthropic': 'claude-3-haiku-20240307',
            'openai': 'gpt-4o',
            'gemini': 'gemini-1.5-pro'
        }
        return self.model or defaults.get(self.provider, 'claude-3-5-sonnet-20240620')

class IngestionConfig(BaseModel):
    """Smart ingestion configuration"""
    chunk_size_min: int = Field(default=300, description="Minimum words per chunk")
    chunk_size_max: int = Field(default=500, description="Maximum words per chunk")
    max_chunks_per_doc: int = Field(default=20, description="Maximum chunks per document")
    output_formats: list = Field(default=['chromadb', 'custom_gpt'], description="Output formats")

class SlackConfig(BaseModel):
    """Slack bot configuration"""
    bot_token: Optional[str] = Field(default=None, description="Slack bot token")
    signing_secret: Optional[str] = Field(default=None, description="Slack signing secret")
    app_token: Optional[str] = Field(default=None, description="Slack app token for Socket Mode")

class AppConfig(BaseModel):
    """Main application configuration"""
    ai: AIConfig = Field(default_factory=AIConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)

    # Directories
    materials_dir: Path = Field(default=Path("materials"), description="Materials source directory")
    output_dir: Path = Field(default=Path("output"), description="Output directory")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load configuration from environment variables"""
        return cls(
            ai=AIConfig(
                provider=os.getenv('AI_PROVIDER', 'anthropic'),
                api_key=os.getenv('ANTHROPIC_API_KEY') or os.getenv('OPENAI_API_KEY') or os.getenv('GOOGLE_API_KEY'),
                model=os.getenv('AI_MODEL')
            ),
            slack=SlackConfig(
                bot_token=os.getenv('SLACK_BOT_TOKEN'),
                signing_secret=os.getenv('SLACK_SIGNING_SECRET'),
                app_token=os.getenv('SLACK_APP_TOKEN')
            ),
            materials_dir=Path(os.getenv('MATERIALS_DIR', 'materials')),
            output_dir=Path(os.getenv('OUTPUT_DIR', 'output')),
            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )
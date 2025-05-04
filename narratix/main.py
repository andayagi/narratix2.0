#!/usr/bin/env python3
"""
Narratix: A tool for analyzing text and generating audio narratives.
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path

from narratix.utils import setup_logging, settings
from narratix.core import TextAnalyzer, VoiceGenerator, AudioGenerator

async def analyze_text(text: str, force_reanalysis: bool = False):
    """Analyze text using the TextAnalyzer."""
    analyzer = TextAnalyzer()
    logging.info(f"Analyzing text of length {len(text)}")
    result = await analyzer.analyze_text(text, force_reanalysis)
    logging.info(f"Analysis complete. Found {len(result.get('roles', []))} characters.")
    return result

async def generate_audio(analysis_result, story_id=None):
    """Generate audio based on text analysis."""
    voice_generator = VoiceGenerator()
    audio_generator = AudioGenerator()
    
    narrative_elements = analysis_result.get('narrative_elements', [])
    if not narrative_elements:
        logging.warning("No narrative elements found in analysis result")
        return None
    
    # Generate voices for characters
    roles = analysis_result.get('roles', [])
    character_names = [role.get('name') for role in roles if role.get('name')]
    voice_mapping = await voice_generator.ensure_voices_exist(character_names, roles)
    logging.info(f"Created/found voices for {len(voice_mapping)} characters")
    
    # Generate audio for each segment
    audio_segments = await audio_generator.generate_audio_segments(narrative_elements, story_id)
    logging.info(f"Generated {len(audio_segments)} audio segments")
    
    # Combine all segments
    if audio_segments:
        output_path = await audio_generator.combine_audio_segments(
            audio_segments, 
            f"story_{story_id or 'unknown'}"
        )
        logging.info(f"Combined audio segments into {output_path}")
        return output_path
    
    return None

async def main_async():
    """Async entry point for the application."""
    parser = argparse.ArgumentParser(description="Narratix text-to-audio narrative tool")
    parser.add_argument(
        "--input", 
        help="Input text file path (if omitted, reads from stdin)"
    )
    parser.add_argument(
        "--output",
        help="Output audio file prefix (will add appropriate extension)"
    )
    parser.add_argument(
        "--story-id",
        help="Unique identifier for the story"
    )
    parser.add_argument(
        "--force-reanalysis",
        action="store_true",
        help="Force reanalysis even if cached results exist"
    )
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # Read input text
    if args.input:
        with open(args.input, 'r') as f:
            text = f.read()
    else:
        logging.info("Reading text from stdin...")
        text = sys.stdin.read()
    
    if not text.strip():
        logging.error("No input text provided")
        return 1
    
    # Process the text
    analysis_result = await analyze_text(text, args.force_reanalysis)
    output_path = await generate_audio(analysis_result, args.story_id or args.output)
    
    if output_path:
        logging.info(f"Audio narrative saved to: {output_path}")
        print(f"Audio saved to: {output_path}")
        return 0
    else:
        logging.error("Failed to generate audio")
        return 1

def main():
    """Entry point for the application."""
    return asyncio.run(main_async())

if __name__ == "__main__":
    sys.exit(main())

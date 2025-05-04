from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class VoiceGenerator:
    def __init__(self):
        self.voices: Dict[str, Dict[str, Any]] = {}  # In-memory store for voices
        
    async def create_voice(self, character_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            name = character_info.get('name')
            if not name:
                return None
                
            voice_info = {
                'name': name,
                'description': character_info.get('description', ''),
                'sample_text': character_info.get('text', ''),
                'status': 'available',
                'voice_id': f"voice_{name.lower().replace(' ', '_')}"
            }
            
            self.voices[name] = voice_info
            return voice_info
        except Exception as e:
            logger.error(f"Failed to create voice: {str(e)}")
            return None

    async def get_voice(self, name: Optional[str] = None, 
                       voice_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            if name and name in self.voices:
                return self.voices[name]
            elif voice_id:
                for voice in self.voices.values():
                    if voice.get('voice_id') == voice_id:
                        return voice
            return None
        except Exception as e:
            logger.error(f"Failed to get voice: {str(e)}")
            return None

    async def list_voices(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            if status:
                return [v for v in self.voices.values() if v.get('status') == status]
            return list(self.voices.values())
        except Exception as e:
            logger.error(f"Failed to list voices: {str(e)}")
            return []

    async def ensure_voices_exist(self, character_names: List[str],
                                character_data: List[Dict[str, Any]]) -> Dict[str, str]:
        try:
            result = {}
            for name, data in zip(character_names, character_data):
                if name not in self.voices:
                    voice_info = await self.create_voice(data)
                    if voice_info:
                        result[name] = voice_info['voice_id']
                else:
                    result[name] = self.voices[name]['voice_id']
            return result
        except Exception as e:
            logger.error(f"Failed to ensure voices exist: {str(e)}")
            return {}

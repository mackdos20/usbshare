import json
import os
import logging

logger = logging.getLogger('Translator')

class Translator:
    def __init__(self, lang='ar'):
        self.lang = lang
        translations_path = os.path.join(os.path.dirname(__file__), 'translations.json')
        try:
            with open(translations_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except Exception:
            self.translations = {}
        
    def _load_translations(self):
        try:
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Construct path to translations file
            translations_file = os.path.join(current_dir, 'translations.json')
            
            with open(translations_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
                
            logger.info(f"Loaded translations for language: {self.lang}")
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
            self.translations = {}
            
    def translate(self, key):
        if self.lang in self.translations and key in self.translations[self.lang]:
            return self.translations[self.lang][key]
        elif 'en' in self.translations and key in self.translations['en']:
            return self.translations['en'][key]
        return key
            
    def set_language(self, language: str):
        """Set the current language"""
        if language != self.lang:
            self.lang = language
            self._load_translations()
            
    def get_available_languages(self) -> list:
        """Get list of available languages"""
        return list(self.translations.keys()) 
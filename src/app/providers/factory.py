from app.config import settings
from app.providers.demo import DemoDiarizationProvider, DemoSpeechToTextProvider, DemoTextToSpeechProvider, DemoTranslationProvider


def get_diarization_provider():
    if settings.provider_diarization != "demo": raise ValueError("Only DEMO diarization provider is implemented")
    return DemoDiarizationProvider()


def get_speech_to_text_provider():
    if settings.provider_speech_to_text != "demo": raise ValueError("Only DEMO speech-to-text provider is implemented")
    return DemoSpeechToTextProvider()


def get_translation_provider():
    if settings.provider_translation != "demo": raise ValueError("Only DEMO translation provider is implemented")
    return DemoTranslationProvider()


def get_text_to_speech_provider():
    if settings.provider_text_to_speech != "demo": raise ValueError("Only DEMO text-to-speech provider is implemented")
    return DemoTextToSpeechProvider()

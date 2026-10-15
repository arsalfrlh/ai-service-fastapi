from faster_whisper import WhisperModel
from app.core.config import WHISPER_DEVICE, WHISPER_MODEL_SIZE, WHISPER_COMPUTE_TYPE, CPU_THREADS
import threading

class WhisperService:
    def __init__(self):
        self.whisper_model: WhisperModel | None = None
        self.transcription_lock = threading.Lock()

    def load_model(self):
        if self.whisper_model is not None:
            return
        print("Load the model...")
        self.whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
            cpu_threads=CPU_THREADS,
            num_workers=1
        )
        print("Load model success")

    def transcribe_audio(self, file_path: str, language: str | None, include_words: bool) -> dict:
        if self.whisper_model is None:
            self.load_model()
        with self.transcription_lock:
            segments_generator, info = self.whisper_model.transcribe(
                file_path,
                task="transcribe",
                language=language,
                beam_size=5,
                temperature=0.0,
                word_timestamps=include_words,
                vad_filter=False,
                condition_on_previous_text=False
            )

            segments = [] 
            transcript_parts = []
            for segment in segments_generator:
                segment_text = segment.text.strip()
                transcript_parts.append(segment.text)
                words = []
                if include_words and segment.words:
                    for word in segment.words:
                        words.append({
                            "start_ms": self.second_to_ms(word.start),
                            "end_ms": self.second_to_ms(word.end),
                            "text": word.word.strip(),
                            "probability": (
                                round(float(word.probability), 4)
                                if word.probability is not None
                                else None
                            )
                        })
                segments.append({
                    "id": len(segments),
                    "start_ms": self.second_to_ms(segment.start),
                    "end_ms": self.second_to_ms(segment.end),
                    "text": segment_text,
                    "words": words
                })
            full_text = "".join(transcript_parts).strip()
            segment_duration_ms = max(
                (item["end_ms"] or 0 for item in segments),
                default=0,
            )
            audio_duration_ms = self.second_to_ms(getattr(info, "duration", None)) or 0
            return {
                "text": full_text,
                "language": info.language,
                "language_probability": round(
                    float(info.language_probability), 4
                ),
                "duration_ms": max(
                    audio_duration_ms,
                    segment_duration_ms,
                ),
                "segments": segments,
            }

    def second_to_ms(self, seconds: float | None) -> int | None:
        if seconds is None:
            return None
        return max(0, int(round(float(seconds) * 1000)))

whisper_service = WhisperService()
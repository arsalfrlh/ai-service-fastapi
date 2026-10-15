
import logging
import os
import tempfile
import threading
import time

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool
from faster_whisper import WhisperModel


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "Lyrics AI Service"

MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

DEFAULT_CPU_THREADS = max(1, (os.cpu_count() or 4) - 1)
CPU_THREADS = int(
    os.getenv("WHISPER_CPU_THREADS", str(DEFAULT_CPU_THREADS))
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(APP_NAME)

whisper_model: WhisperModel | None = None

# Hindari beberapa request menjalankan model yang sama
# secara bersamaan pada service dengan RAM terbatas.
transcription_lock = threading.Lock()


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global whisper_model

    logger.info("Loading Faster-Whisper model: %s", MODEL_SIZE)
    logger.info(
        "Device=%s, Compute Type=%s",
        DEVICE,
        COMPUTE_TYPE,
    )

    whisper_model = WhisperModel(
        MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        cpu_threads=CPU_THREADS if DEVICE == "cpu" else 0,
        num_workers=1,
    )

    logger.info("Faster-Whisper model loaded successfully.")

    yield

    whisper_model = None
    logger.info("Lyrics AI Service stopped.")


app = FastAPI(
    title=APP_NAME,
    description=(
        "Local AI service for converting MP3 music "
        "into timestamped text and word-level timestamps."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# TIMESTAMP UTILITIES
# ============================================================

def seconds_to_ms(seconds: float | None) -> int | None:
    """
    Convert seconds into integer milliseconds.

    Example:
        1.25 seconds -> 1250 milliseconds
    """
    if seconds is None:
        return None

    return max(0, int(round(float(seconds) * 1000)))


# ============================================================
# TRANSCRIPTION ENGINE
# ============================================================

def transcribe_audio(
    audio_path: str,
    language: str | None,
    include_words: bool,
) -> dict:
    """
    Transcribe an audio file using Faster-Whisper.

    This function runs in a worker thread so that the
    FastAPI event loop is not blocked by model inference.
    """

    if whisper_model is None:
        raise RuntimeError("Whisper model has not been loaded.")

    # Keep the lock while generating and consuming the segments.
    with transcription_lock:
        segments_generator, info = whisper_model.transcribe(
            audio_path,
            task="transcribe",
            language=language,
            beam_size=5,
            temperature=0.0,
            word_timestamps=include_words,

            # Do not apply VAD to music by default, because
            # quiet vocals can potentially be removed.
            vad_filter=False,

            # Helps avoid some repetitive-context problems
            # sometimes encountered with music.
            condition_on_previous_text=False,
        )

        segments = []
        transcript_parts = []

        # Faster-Whisper returns a generator.
        # Transcription is executed as we iterate over it.
        for segment in segments_generator:
            segment_text = segment.text.strip()

            transcript_parts.append(segment.text)

            words = []

            if include_words and segment.words:
                for word in segment.words:
                    words.append(
                        {
                            "start_ms": seconds_to_ms(word.start),
                            "end_ms": seconds_to_ms(word.end),
                            "text": word.word.strip(),
                            "probability": (
                                round(float(word.probability), 4)
                                if word.probability is not None
                                else None
                            ),
                        }
                    )

            segments.append(
                {
                    "id": len(segments),
                    "start_ms": seconds_to_ms(segment.start),
                    "end_ms": seconds_to_ms(segment.end),
                    "text": segment_text,
                    "words": words,
                }
            )

        full_text = "".join(transcript_parts).strip()

        segment_duration_ms = max(
            (item["end_ms"] or 0 for item in segments),
            default=0,
        )

        audio_duration_ms = seconds_to_ms(
            getattr(info, "duration", None)
        ) or 0

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


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {
        "success": True,
        "service": APP_NAME,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {
        "success": True,
        "status": "ok",
        "model_loaded": whisper_model is not None,
        "model": MODEL_SIZE,
        "device": DEVICE,
    }


# ============================================================
# UPLOAD MP3 AND TRANSCRIBE
# ============================================================

@app.post("/api/transcribe")
async def transcribe_endpoint(
    file: UploadFile = File(
        ...,
        description="MP3 file to transcribe",
    ),
    language: str | None = Query(
        default=None,
        description=(
            "Language code, such as id or en. "
            "Leave empty for automatic language detection."
        ),
    ),
    include_words: bool = Query(
        default=True,
        description=(
            "Return timestamps for individual words."
        ),
    ),
):
    temp_path: str | None = None

    try:
        # ----------------------------------------------------
        # 1. Validate uploaded file
        # ----------------------------------------------------

        filename = file.filename or ""

        if Path(filename).suffix.lower() != ".mp3":
            raise HTTPException(
                status_code=400,
                detail="Only MP3 files are supported.",
            )

        # ----------------------------------------------------
        # 2. Save upload to a temporary file
        # ----------------------------------------------------

        total_bytes = 0

        with tempfile.NamedTemporaryFile(
            prefix="lyrics_",
            suffix=".mp3",
            delete=False,
        ) as temp_audio:

            temp_path = temp_audio.name

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File exceeds the maximum size "
                            f"of {MAX_UPLOAD_MB} MB."
                        ),
                    )

                temp_audio.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded MP3 file is empty.",
            )

        logger.info(
            "Received file=%s size=%s bytes",
            filename,
            total_bytes,
        )

        # ----------------------------------------------------
        # 3. Normalize language parameter
        # ----------------------------------------------------

        normalized_language = (
            language.strip().lower()
            if language
            else None
        )

        if normalized_language == "auto":
            normalized_language = None

        # ----------------------------------------------------
        # 4. Run AI transcription
        # ----------------------------------------------------

        start_time = time.perf_counter()

        result = await run_in_threadpool(
            transcribe_audio,
            temp_path,
            normalized_language,
            include_words,
        )

        processing_time_ms = int(
            round(
                (time.perf_counter() - start_time) * 1000
            )
        )

        logger.info(
            "Transcription completed in %s ms",
            processing_time_ms,
        )

        # ----------------------------------------------------
        # 5. Return JSON response
        # ----------------------------------------------------

        return {
            "success": True,
            "filename": Path(filename).name,
            "model": MODEL_SIZE,
            "file_size_bytes": total_bytes,
            "language": result["language"],
            "language_probability": (
                result["language_probability"]
            ),
            "duration_ms": result["duration_ms"],
            "processing_time_ms": processing_time_ms,
            "text": result["text"],
            "segments": result["segments"],
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Audio transcription failed")

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to transcribe audio. "
                "Check the server logs and ensure that "
                "the uploaded file is a valid MP3."
            ),
        ) from exc

    finally:
        await file.close()

        # Remove temporary audio after processing,
        # including when processing fails.
        if temp_path:
            try:
                os.remove(temp_path)
            except FileNotFoundError:
                pass
            except OSError:
                logger.warning(
                    "Could not remove temporary file: %s",
                    temp_path,
                )

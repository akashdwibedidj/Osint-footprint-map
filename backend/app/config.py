from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_url: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    sherlock_cmd: str = "sherlock"
    maigret_cmd: str = "maigret"

    # --- audio_analysis ---
    upload_dir: str = "uploads"
    whisper_model_size: str = "small"       # tiny/base/small/medium/large-v3/distil-large-v3
                                             # "small" is the CPU-friendly default so this repo
                                             # runs out of the box on any machine, no CUDA setup
                                             # required. If you have a working GPU/CUDA
                                             # environment (e.g. WSL), override in .env:
                                             #   WHISPER_MODEL_SIZE=medium
                                             #   WHISPER_DEVICE=cuda
                                             #   WHISPER_COMPUTE_TYPE=float16
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"      # faster-whisper's recommended CPU quantization -
                                             # meaningfully faster than default float32 on CPU

    class Config:
        env_file = ".env"


settings = Settings()
import asyncio
import logging
from mouthfull.backend.stt.whisper_stt import WhisperSTT
from mouthfull.configs.config import STTConfig

logging.basicConfig(level=logging.INFO)

async def test():
    config = STTConfig(engine="faster_whisper", model_size="tiny", device="cpu", compute_type="int8")
    engine = WhisperSTT(config)
    print("Testing loader...")
    await engine.load_model()
    print("Loader succeeded.")

asyncio.run(test())

from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import aiofiles


async def load_prompt(prompt_path: str) -> str:
    """Asynchronously load a .md or .txt prompt as a plain string"""
    try:
        path = Path(prompt_path).resolve()
        logger.info(f"Attempting to load prompt from absolute path: {path}")
        if not path.exists():
            logger.error(f"File does not exist: {path}")
            return ""
        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            prompt = (await f.read()).strip()
        logger.info(f"Successfully loaded prompt from: {path}")
        return prompt
    except Exception as e:
        logger.error(f"Error loading prompt from {prompt_path}: {e}")
        return ""

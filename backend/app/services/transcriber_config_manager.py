import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


CLOUD_TRANSCRIBER_IDS = ["groq", "volcengine"]


class TranscriberConfigManager:
    """管理转写器配置，存储在 JSON 文件中，支持前端动态修改。"""

    def __init__(self, filepath: str = "config/transcriber.json"):
        self.path = Path(filepath)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write(self, data: Dict[str, Any]):
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_config(self) -> Dict[str, Any]:
        """获取当前转写器配置，fallback 到环境变量默认值。"""
        data = self._read()
        return {
            "transcriber_type": data.get(
                "transcriber_type",
                os.getenv("TRANSCRIBER_TYPE", "fast-whisper"),
            ),
            "whisper_model_size": data.get(
                "whisper_model_size",
                os.getenv("WHISPER_MODEL_SIZE", "medium"),
            ),
            "api_keys": data.get("api_keys", {}),
        }

    def update_config(
        self,
        transcriber_type: str,
        whisper_model_size: Optional[str] = None,
        api_keys: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """更新转写器配置并持久化。"""
        data = self._read()
        data["transcriber_type"] = transcriber_type
        if whisper_model_size is not None:
            data["whisper_model_size"] = whisper_model_size
        if api_keys is not None:
            existing = data.get("api_keys", {})
            # Only update keys for known cloud transcribers, mask non-edited keys
            for k in CLOUD_TRANSCRIBER_IDS:
                if k in api_keys:
                    existing[k] = api_keys[k]
            data["api_keys"] = existing
        self._write(data)
        return self.get_config()

    def get_api_key(self, transcriber_id: str) -> Optional[str]:
        """获取指定转写器的 API Key，优先从配置读取。"""
        data = self._read()
        return data.get("api_keys", {}).get(transcriber_id)

    def get_transcriber_type(self) -> str:
        return self.get_config()["transcriber_type"]

    def get_whisper_model_size(self) -> str:
        return self.get_config()["whisper_model_size"]

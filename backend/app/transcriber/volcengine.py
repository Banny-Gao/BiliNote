import json
import os
import tempfile
import uuid

import ffmpeg
import requests

from app.decorators.timeit import timeit
from app.models.transcriber_model import TranscriptResult, TranscriptSegment
from app.transcriber.base import Transcriber, get_transcriber_api_key
from app.utils.logger import get_logger

logger = get_logger(__name__)

RESOURCE_ID = "volc.bigasr.auc_turbo"
ENDPOINT = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
MAX_FILE_MB = 20
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024


def compress_audio(input_path: str, target_bitrate="64k") -> str:
    output_fd, output_path = tempfile.mkstemp(suffix=".mp3")
    os.close(output_fd)
    ffmpeg.input(input_path).output(output_path, audio_bitrate=target_bitrate).run(
        quiet=True, overwrite_output=True
    )
    return output_path


class VolcengineTranscriber(Transcriber):
    @timeit
    def transcript(self, file_path: str) -> TranscriptResult:
        api_key = get_transcriber_api_key("volcengine")

        # Compress if too large
        if os.path.getsize(file_path) > MAX_FILE_BYTES:
            logger.info(
                f"文件超过 {MAX_FILE_MB}MB（当前 {round(os.path.getsize(file_path) / 1024 / 1024, 2)}MB），压缩中..."
            )
            file_path = compress_audio(file_path)

        # Read and base64-encode audio
        with open(file_path, "rb") as f:
            import base64
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        request_id = str(uuid.uuid4())
        headers = {
            "X-Api-Key": api_key,
            "X-Api-Resource-Id": RESOURCE_ID,
            "X-Api-Request-Id": request_id,
            "X-Api-Sequence": "-1",
            "Content-Type": "application/json",
        }

        body = {
            "user": {"uid": api_key},
            "audio": {"data": audio_b64},
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
            },
        }

        logger.info(f"发送火山引擎语音识别请求 (request_id={request_id})")
        resp = requests.post(ENDPOINT, json=body, headers=headers, timeout=300)

        status_code = resp.headers.get("X-Api-Status-Code", "")
        if status_code != "20000000":
            msg = resp.headers.get("X-Api-Message", "未知错误")
            raise Exception(f"火山引擎识别失败 [{status_code}]: {msg}")

        data = resp.json()
        result = data.get("result", {})
        full_text = result.get("text", "").strip()

        utterances = result.get("utterances", [])
        segments = []
        for utt in utterances:
            start = utt.get("start_time", 0) / 1000.0
            end = utt.get("end_time", 0) / 1000.0
            text = utt.get("text", "").strip()
            if text:
                segments.append(TranscriptSegment(start=start, end=end, text=text))

        return TranscriptResult(
            language="zh",
            full_text=full_text,
            segments=segments,
            raw=data,
        )

import os
import json
import logging
import re
import ssl
import urllib.request
from abc import ABC
from typing import Union, Optional, List

from app.downloaders.base import Downloader, DownloadQuality
from app.downloaders.bilibili_downloader import BilibiliDownloader
from app.models.notes_model import AudioDownloadResult
from app.models.transcriber_model import TranscriptResult
from app.utils.path_helper import get_data_dir
from app.utils.url_parser import extract_video_id

logger = logging.getLogger(__name__)


class BilibiliCheeseDownloader(BilibiliDownloader, ABC):
    """B站付费课程 (cheese) 下载器，使用 pugv API 直接下载音频流"""

    CHEESE_URL_PATTERN = re.compile(r'/(?:cheese|pugv)/(?:play|ep)/(?:ep(\d+)|ss(\d+))')

    def __init__(self):
        super().__init__()
        self._ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    @classmethod
    def is_cheese_url(cls, video_url: str) -> bool:
        return bool(cls.CHEESE_URL_PATTERN.search(video_url))

    def _parse_cheese_url(self, video_url: str) -> tuple:
        """Parse cheese URL, returns (ep_id, season_id)"""
        m = self.CHEESE_URL_PATTERN.search(video_url)
        if m:
            return m.group(1), m.group(2)
        return None, None

    def _api_request(self, url: str) -> dict:
        """Make authenticated API request to B站（每次重新读取 cookie）"""
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url)
        req.add_header('User-Agent', self._ua)
        req.add_header('Referer', 'https://www.bilibili.com/cheese/')
        cookie = self._cookie_mgr.get('bilibili')
        if cookie:
            req.add_header('Cookie', cookie)
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        return json.loads(resp.read().decode())

    def _get_episode_info(self, ep_id: str) -> dict:
        """Get episode info from pugv API"""
        url = f'https://api.bilibili.com/pugv/view/web/season?ep_id={ep_id}'
        data = self._api_request(url)
        season_data = data.get('data', {})
        episodes = season_data.get('episodes', [])
        for ep in episodes:
            if str(ep.get('id')) == str(ep_id):
                return {
                    'aid': ep.get('aid'),
                    'cid': ep.get('cid'),
                    'title': ep.get('title'),
                    'duration': ep.get('duration', 0),
                    'season_title': season_data.get('title', ''),
                    'cover_url': season_data.get('cover', ''),
                }
        return None

    def _get_play_url(self, avid: str, cid: str, ep_id: str) -> dict:
        """Get play URL from pugv API"""
        url = (f'https://api.bilibili.com/pugv/player/web/playurl'
               f'?avid={avid}&cid={cid}&qn=0&fnver=0&fnval=16&fourk=1&ep_id={ep_id}')
        return self._api_request(url)

    def _download_audio_stream(self, stream_url: str, output_path: str) -> bool:
        """Download audio stream to file"""
        ctx = ssl.create_default_context()
        req = urllib.request.Request(stream_url)
        req.add_header('User-Agent', self._ua)
        req.add_header('Referer', 'https://www.bilibili.com/cheese/')
        req.add_header('Origin', 'https://www.bilibili.com')
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=120)
            with open(output_path, 'wb') as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            return os.path.getsize(output_path) > 10000
        except Exception as e:
            logger.error(f'下载音频流失败: {e}')
            return False

    def _extract_audio_to_mp3(self, input_path: str, output_path: str) -> bool:
        """Use FFmpeg to extract audio to MP3"""
        import subprocess
        ffmpeg = os.environ.get('FFMPEG_BIN_PATH', 'ffmpeg')
        cmd = [ffmpeg, '-i', input_path, '-vn', '-acodec', 'libmp3lame',
               '-q:a', '2', '-y', output_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.error(f'FFmpeg error: {result.stderr[-300:]}')
            return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
        except Exception as e:
            logger.error(f'FFmpeg 转换失败: {e}')
            return False

    def download(
        self,
        video_url: str,
        output_dir: Union[str, None] = None,
        quality: DownloadQuality = "fast",
        need_video: Optional[bool] = False
    ) -> AudioDownloadResult:
        if output_dir is None:
            output_dir = get_data_dir()
        if not output_dir:
            output_dir = self.cache_data
        os.makedirs(output_dir, exist_ok=True)

        ep_id, season_id = self._parse_cheese_url(video_url)
        if not ep_id and not season_id:
            return super().download(video_url, output_dir, quality, need_video)

        if season_id and not ep_id:
            ep_info = self._get_first_episode(season_id)
            if not ep_info:
                raise ValueError(f'无法获取课程 {season_id} 的剧集信息')
            ep_id = ep_info.get('id')

        ep_info = self._get_episode_info(ep_id)
        if not ep_info:
            raise ValueError(f'无法获取剧集 {ep_id} 的信息')

        logger.info(f'Cheese course: {ep_info["season_title"]}, Episode: {ep_info["title"]}')

        play_data = self._get_play_url(ep_info['aid'], ep_info['cid'], ep_id)
        dash = play_data.get('data', {}).get('dash', {})
        audio_streams = dash.get('audio', [])

        if not audio_streams:
            raise ValueError('未找到可下载的音频流（可能受 DRM 保护）')

        # Get best quality audio
        best_audio = max(audio_streams, key=lambda x: x.get('bandwidth', 0))
        stream_url = best_audio['base_url']
        codecs = best_audio.get('codecs', 'unknown')

        logger.info(f'Downloading audio: {codecs} @ {best_audio.get("bandwidth")} bps')

        temp_audio = os.path.join(output_dir, f'{ep_id}_temp.m4s')
        audio_path = os.path.join(output_dir, f'{ep_id}.mp3')

        if not self._download_audio_stream(stream_url, temp_audio):
            raise RuntimeError('音频下载失败')

        if not self._extract_audio_to_mp3(temp_audio, audio_path):
            raise RuntimeError('音频转码失败')

        # Clean up temp file
        try:
            os.remove(temp_audio)
        except Exception:
            pass

        title = f'{ep_info["season_title"]} - {ep_info["title"]}'

        return AudioDownloadResult(
            file_path=audio_path,
            title=title,
            duration=ep_info.get('duration', 0),
            cover_url=ep_info.get('cover_url'),
            platform="bilibili",
            video_id=str(ep_id),
            raw_info={'ep_id': ep_id, 'aid': ep_info['aid'], 'cid': ep_info['cid']},
            video_path=None
        )

    def _get_first_episode(self, season_id: str) -> Optional[dict]:
        """Get first episode of a season"""
        episodes_url = f'https://api.bilibili.com/pugv/view/web/season?season_id={season_id}'
        data = self._api_request(episodes_url)
        episodes = data.get('data', {}).get('episodes', [])
        return episodes[0] if episodes else None

    def download_video(
        self,
        video_url: str,
        output_dir: Union[str, None] = None,
    ) -> str:
        if output_dir is None:
            output_dir = get_data_dir()
        os.makedirs(output_dir, exist_ok=True)

        ep_id, season_id = self._parse_cheese_url(video_url)
        if not ep_id:
            return super().download_video(video_url, output_dir)

        ep_info = self._get_episode_info(ep_id)
        play_data = self._get_play_url(ep_info['aid'], ep_info['cid'], ep_id)
        dash = play_data.get('data', {}).get('dash', {})

        # Download best video + audio and mux
        video_streams = dash.get('video', [])
        audio_streams = dash.get('audio', [])
        if not video_streams:
            return super().download_video(video_url, output_dir)

        best_video = max(video_streams, key=lambda x: x.get('bandwidth', 0))
        best_audio = max(audio_streams, key=lambda x: x.get('bandwidth', 0))

        temp_video = os.path.join(output_dir, f'{ep_id}_temp_video.m4s')
        temp_audio = os.path.join(output_dir, f'{ep_id}_temp_audio.m4s')
        video_path = os.path.join(output_dir, f'{ep_id}.mp4')

        import subprocess
        if not self._download_audio_stream(best_video['base_url'], temp_video):
            raise RuntimeError('视频流下载失败')
        if not self._download_audio_stream(best_audio['base_url'], temp_audio):
            raise RuntimeError('音频流下载失败')

        ffmpeg = os.environ.get('FFMPEG_BIN_PATH', 'ffmpeg')
        cmd = [ffmpeg, '-i', temp_video, '-i', temp_audio,
               '-c:v', 'copy', '-c:a', 'aac', '-y', video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f'视频合并失败: {result.stderr[-300:]}')

        for f in [temp_video, temp_audio]:
            try:
                os.remove(f)
            except Exception:
                pass

        return video_path

    def download_subtitles(self, video_url: str, output_dir: str = None,
                           langs: List[str] = None) -> Optional[TranscriptResult]:
        ep_id, _ = self._parse_cheese_url(video_url)
        if not ep_id:
            return super().download_subtitles(video_url, output_dir, langs)
        # Cheese courses don't typically have subtitles via the API
        logger.info('Cheese 课程暂不支持字幕获取')
        return None

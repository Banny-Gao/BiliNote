from abc import ABC, abstractmethod

from app.models.transcriber_model import TranscriptResult


def get_transcriber_api_key(transcriber_id: str) -> str:
    """获取转写器的 API Key，优先从转写配置读取，fallback 到模型供应商配置。"""
    from app.services.transcriber_config_manager import TranscriberConfigManager
    from app.services.provider import ProviderService

    key = TranscriberConfigManager().get_api_key(transcriber_id)
    if key:
        return key
    provider = ProviderService.get_provider_by_id(transcriber_id)
    if provider and provider.get("api_key"):
        return provider["api_key"]
    raise Exception(
        f"{transcriber_id} API Key 未配置，请在「音频转写配置」中设置。"
    )


class Transcriber(ABC):
    @abstractmethod
    def transcript(self,file_path:str)->TranscriptResult:
        '''

        :param file_path:音频路径
        :return: 返回一个 TranscriptResult 类
        '''
        pass

    def on_finish(self,video_path:str,result: TranscriptResult)->None:
        '''
        当音频转录完成时调用
        :param video_path: 视频路径
        :param result: 识别结果
        :return:
        '''
        pass
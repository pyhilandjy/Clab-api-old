import requests  # naver CLOVA Speech API
import json  # naver CLOVA Speech API
from app.config import settings


class ClovaApiClient:
    invoke_url = settings.clova_invoke_url
    secret = settings.clova_secret

    def request_stt(
        self,
        file_path,
        completion="sync",
        callback=None,
        userdata=None,
        forbiddens=None,
        boostings=None,
        wordAlignment=True,
        fullText=True,
        diarization=None,
    ):
        request_body = {
            "language": "ko-KR",
            "completion": completion,
            "callback": callback,
            "userdata": userdata,
            "wordAlignment": wordAlignment,
            "fullText": fullText,
            "forbiddens": forbiddens,
            "boostings": boostings,
            "diarization": diarization,
        }
        headers = {
            "Accept": "application/json;UTF-8",
            "X-CLOVASPEECH-API-KEY": self.secret,
        }
        print(json.dumps(request_body, ensure_ascii=False).encode("UTF-8"))
        files = {
            "media": open(file_path, "rb"),
            "params": (
                None,
                json.dumps(request_body, ensure_ascii=False).encode("UTF-8"),
                "application/json",
            ),
        }
        response = requests.post(
            headers=headers, url=self.invoke_url + "/recognizer/upload", files=files
        )
        return response

import os
import io
from collections import Counter
from datetime import date
from PIL import Image

import matplotlib.pyplot as plt
import mecab_ko as MeCab
import numpy as np
import pandas as pd
import seaborn as sns
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from matplotlib import font_manager, rc
from wordcloud import WordCloud
from fastapi import HTTPException


from app.database.query import INSERT_IMAGE_FILES_META_DATA
from app.database.worker import execute_insert_update_query_single
from app.config import settings

FONT_PATH = os.path.abspath("./NanumFontSetup_TTF_GOTHIC/NanumGothic.ttf")
font_prop = font_manager.FontProperties(fname=FONT_PATH)

# 폰트 추가 및 기본 폰트 목록에 추가
font_manager.fontManager.addfont(FONT_PATH)
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False


session = boto3.Session(
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
)

bucket_name = settings.bucket_name

s3 = session.client("s3")


POS_TAG_TO_KOREAN = {
    "NNP": "고유명사",
    "NNG": "명사",
    "NP": "대명사",
    "VV": "동사",
    "VA": "형용사",
    "MAG": "부사",
}


def parse_text(text):
    """텍스트에 형태소분석 결과를 반환"""
    mecab = MeCab.Tagger()
    return mecab.parse(text)


def classify_words_by_pos(parsed_text):
    """파싱된 텍스트에서 품사별로 단어를 분류"""
    pos_lists = {korean: [] for korean in POS_TAG_TO_KOREAN.values()}
    pos_unique_lists = {korean: set() for korean in POS_TAG_TO_KOREAN.values()}

    for line in parsed_text.split("\n"):
        if "\t" not in line:
            continue
        word, tag_info = line.split("\t")
        tag = tag_info.split(",")[0]
        if tag in POS_TAG_TO_KOREAN:
            korean_pos = POS_TAG_TO_KOREAN[tag]
            pos_lists[korean_pos].append(word)
            pos_unique_lists[korean_pos].add(word)

    return pos_lists, pos_unique_lists


def build_pos_summary(
    pos_lists,
    pos_unique_lists,
):
    """품사별 단어 리스트와 고유 단어 세트에서 요약 정보를 구성하여 반환"""
    total_words = sum(len(words) for words in pos_lists.values())
    total_unique_words = sum(
        len(unique_words) for unique_words in pos_unique_lists.values()
    )
    summary = {
        pos: f"{len(words)} 개, {round(len(words) / total_words * 100, 1)}%"
        for pos, words in pos_lists.items()
    }
    summary["총단어 수"] = total_words
    return summary


def analyze_text_with_mecab(text):
    """품사별로 단어를 분류"""
    parsed_text = parse_text(text)
    pos_lists, pos_unique_lists = classify_words_by_pos(parsed_text)
    return build_pos_summary(pos_lists, pos_unique_lists)


def extract_speaker_data(data):
    """발화자별로 텍스트를 추출하여 하나의 문자열로 결합"""
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)
    speaker_data = (
        data.groupby("speaker_label")["text_edited"]
        .apply(lambda texts: " ".join(texts.astype(str)))
        .to_dict()
    )
    return speaker_data


def analyze_speech_data(morphs_data):
    """형태소분석"""
    speaker_data = extract_speaker_data(morphs_data)
    a = {
        speaker: analyze_text_with_mecab(text) for speaker, text in speaker_data.items()
    }
    return a


#################형태소분석#################


# Create a circle mask
def create_circle_mask():
    """mask 생성"""
    x, y = np.ogrid[:600, :600]  # adjust to desired dimensions
    center_x, center_y = 300, 300  # adjust to be the center of the circle
    radius = 300  # adjust to be the radius of the circle

    circle = (x - center_x) ** 2 + (y - center_y) ** 2 <= radius**2
    mask = 255 * np.ones((600, 600), dtype=np.uint8)
    mask[circle] = 0
    return mask


def extract_nouns_with_mecab(text):
    """형태소분석 명사 추출"""
    mecab = MeCab.Tagger()
    nouns = []
    for line in mecab.parse(text).split("\n"):
        if "\t" in line:
            word, tag_info = line.split("\t")
            tag = tag_info.split(",")[0]
            if tag in ["NNG", "NNP"]:  # 일반명사와 고유명사
                nouns.append(word)
    return nouns


def count_words(nouns):
    """한 글자 명사 제거"""
    words = [word for word in nouns if len(word) > 1]
    return Counter(words)


def generate_wordcloud(word_counts, font_path, mask):
    """워드클라우드 기본 생성"""
    wc = WordCloud(
        font_path=font_path,
        background_color="white",
        width=800,
        height=800,
        max_words=200,
        max_font_size=100,
        colormap="viridis",  # 색상 맵 변경
        mask=mask,
    )
    wc.generate_from_frequencies(word_counts)
    return wc


def save_wordcloud(wordcloud, s3_image_path, local_image_path, speaker, font_prop):
    """워드클라우드를 S3 및 로컬에 저장"""
    try:
        # 메모리에 워드클라우드 이미지 저장
        img_data = io.BytesIO()
        plt.figure(figsize=(10, 10))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.text(
            0.05,
            0,
            speaker,
            fontsize=24,
            fontproperties=font_prop,
            ha="left",
            va="top",
            transform=plt.gca().transAxes,
            bbox=dict(facecolor="white", alpha=0.5),
        )

        plt.savefig(img_data, format="PNG", bbox_inches="tight")
        plt.savefig(local_image_path, format="PNG", bbox_inches="tight")
        plt.close()
        img_data.seek(0)

        bucket_name = "connectslab"
        # S3에 업로드
        s3.upload_fileobj(img_data, bucket_name, s3_image_path)

        return {
            "message": "Wordcloud uploaded successfully",
            "s3_file_path": s3_image_path,
            "local_file_path": local_image_path,
        }
    except NoCredentialsError:
        return {"error": "Credentials not available"}
    except ClientError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def create_wordcloud(stt_wordcloud, font_path, type, user_id, start_date, end_date):
    """워드클라우드 생성 및 파일로 저장"""
    if not isinstance(stt_wordcloud, pd.DataFrame):
        stt_wordcloud = pd.DataFrame(stt_wordcloud)

    f_start_date = start_date.strftime("%Y-%m-%d")
    f_end_date = end_date.strftime("%Y-%m-%d")
    local_paths = []

    for speaker in stt_wordcloud["speaker_label"].unique():
        speaker_data = stt_wordcloud[stt_wordcloud["speaker_label"] == speaker]
        text = " ".join(speaker_data["text_edited"].astype(str))
        nouns = extract_nouns_with_mecab(text)
        word_counts = count_words(nouns)
        mask = create_circle_mask()
        wordcloud = generate_wordcloud(word_counts, font_path, mask)

        image_id = gen_image_file_id(user_id, speaker, f_start_date, f_end_date, type)

        # 파일 경로 생성
        s3_image_path = gen_image_file_path(image_id)
        local_image_path = gen_image_local_file_path(image_id)

        metadata = create_image_metadata(
            image_id=image_id,
            user_id=user_id,
            speaker=speaker,
            start_date=start_date,
            end_date=end_date,
            type=type,
            image_path=s3_image_path,
        )
        insert_image_file_metadata(metadata)
        # 워드클라우드 저장
        response = save_wordcloud(
            wordcloud,
            s3_image_path,
            local_image_path,
            speaker,
            font_prop,
        )
        local_paths.append(local_image_path)
    return response, local_paths


# image file data
def gen_image_file_id(
    user_id: str, speaker: str, start_date: date, end_date: date, type: str
) -> str:
    """이미지 파일 아이디 생성"""
    return f"{user_id}_{speaker}_{start_date}_{end_date}_{type}.png"


def gen_image_file_path(image_id):
    """이미지 파일경로 생성"""
    directory = "image"
    return f"{directory}/{image_id}"


def gen_image_local_file_path(image_id):
    """이미지 파일경로 생성"""
    return f"./app/image/{image_id}"


def create_image_metadata(
    image_id: str,
    speaker: str,
    user_id: str,
    start_date: date,
    end_date: date,
    type: str,
    image_path: str,
):
    return {
        "image_id": image_id,
        "speaker": speaker,
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date,
        "type": type,
        "image_path": image_path,
    }


def insert_image_file_metadata(metadata: dict):
    execute_insert_update_query_single(
        query=INSERT_IMAGE_FILES_META_DATA, params=metadata
    )


#################워드클라우드#################


def violin_chart(stt_violin_chart, user_id, start_date, end_date, type, font_path):
    if not isinstance(stt_violin_chart, pd.DataFrame):
        stt_violin_chart = pd.DataFrame(stt_violin_chart)
    stt_violin_chart["char"] = stt_violin_chart["text_edited"].apply(len)
    f_start_date = start_date.strftime("%Y-%m-%d")
    f_end_date = end_date.strftime("%Y-%m-%d")
    speaker = stt_violin_chart["speaker_label"].unique()
    speaker = ",".join(speaker)

    image_id = gen_image_file_id(user_id, speaker, f_start_date, f_end_date, type)

    s3_image_path = gen_image_file_path(image_id)
    local_image_path = gen_image_local_file_path(image_id)

    metadata = create_image_metadata(
        image_id=image_id,
        user_id=user_id,
        speaker=speaker,
        start_date=start_date,
        end_date=end_date,
        type=type,
        image_path=s3_image_path,
    )
    insert_image_file_metadata(metadata)
    sns.set_theme(
        style="whitegrid", font="NanumGothic", rc={"axes.unicode_minus": False}
    )
    sns.set_palette(sns.color_palette("Set2", 2))
    save_violin_plot(stt_violin_chart, s3_image_path, font_prop, local_image_path)
    return local_image_path


def save_violin_plot(stt_violin_chart, s3_image_path, font_prop, local_image_path):
    """바이올린 플롯을 S3에 저장"""
    try:
        # 메모리에 바이올린 플롯 이미지 저장
        img_data = io.BytesIO()
        plt.figure(figsize=(6, 6))
        plt.title("발화자별 문장 길이 분포", fontproperties=font_prop)
        plt.xlabel("speaker_label", fontproperties=font_prop)
        plt.ylabel("문장 길이", fontproperties=font_prop)

        sns.violinplot(
            data=stt_violin_chart,
            x="speaker_label",
            y="char",
            hue="speaker_label",
            split=True,
            inner="quart",
            palette=sns.color_palette("Set2"),
        )

        plt.tight_layout()
        plt.savefig(img_data, format="PNG")
        plt.savefig(local_image_path, format="PNG")
        plt.close()
        img_data.seek(0)
        bucket_name = "connectslab"

        # S3에 업로드
        s3.upload_fileobj(img_data, bucket_name, local_image_path)

        return {
            "message": "violinplot uploaded successfully",
            "s3_file_path": s3_image_path,
            "local_file_path": local_image_path,
        }
    except NoCredentialsError:
        return {"error": "Credentials not available"}
    except ClientError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def fetch_image_from_s3(bucket_name, object_key):
    try:
        # 객체 존재 여부 확인
        s3.head_object(Bucket=bucket_name, Key=object_key)

        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        image_data = response["Body"].read()
        return image_data
    except s3.exceptions.NoSuchKey:
        print(
            f"Error: The specified key '{object_key}' does not exist in the bucket '{bucket_name}'."
        )
        raise HTTPException(status_code=404, detail="Image not found in S3")
    except Exception as e:
        print(
            f"Error fetching image from S3. Bucket: '{bucket_name}', Key: '{object_key}'"
        )
        print(f"Exception: {e}")
        raise HTTPException(status_code=500, detail="Error fetching image from S3")

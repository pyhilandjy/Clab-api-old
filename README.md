# [Frontend](https://github.com/pyhilandjy/clab-admin-page)

# Backend

## FastAPI

### 라우터 설명

#### 1. 유저 관리(users.py)
- 유저의 목록 반환: /users/ (POST)
- 로그인 하기 위한 정보 처리: /users/login/ (POST)
- 로그인한 사용자의 정보를 반환: /users/me/ (GET)

#### 2. 파일 관리(files.py)
- user_id별 file_id 반환: /files/ (POST)

#### 3. 오디오 처리(audio.py)
- 오디오 파일 업로드 및 처리: /audio/uploadfile/ (POST)
  - 녹음된 오디오 파일을 업로드 후 처리하는 로직
    - file_id, 로컬 file_path, S3 file_path 생성, S3, 로컬에 저장
    - 파일 확장자 변환 (webm to m4a)
    - 음성파일 naver clova에 전송
    - 메타데이터 supabase 적재

#### 4. STT 결과값 처리(stt.py)
- STT 결과값 후처리 tag:[update_results]
  - 파일별 오타를 한번에 처리: /stt/results/update_text/ (POST)
  - 파일별 발화자를 한번에 처리: /stt/results/update_speaker/ (POST)
  - 파일별 행의 오타를 처리: /stt/results/update_text_edit/ (POST)
  - 파일별 선택한 행의 데이터를 복사하여 다음 행에 추가: /stt/results/posts/index_add_data/ (POST)
  - 파일별 선택한 행의 데이터를 삭제: /stt/results/index_delete_data/ (POST)
  
- STT 결과값 워드클라우드, 바이올린플롯 처리: [image]
  - 지정 기간 stt 데이터의 워드 클라우드 생성: /stt/create/wordcloud/ (POST)
  - 지정 기간 stt 데이터의 바이올린 플롯 생성: /stt/create/violinplot/ (POST)
  - 이미지 반환: /stt/images/{image_path} (GET)
    
- 리포트에 사용되는 데이터 반환 tag:[report]
  - 지정 기간 stt 데이터의 가장 긴 문장, 평균 문장길이, 녹음시간 반환: /stt/report/ (POST)
  - 지정 기간 stt 데이터의 발화자별 품사 비율 반환: /stt/report/morps/ (POST)
  - 지정 기간 stt 데이터의 발화자별 화행 카운트: /stt/report/act_count/ (POST)
    
- STT 결과값 화행 처리: [speech_act]
  - speech act의 목록 반환: /stt/get/speech_act/ (GET)
  - act_id를 act_name으로 반환: /stt/results/speech_act/ (POST)
  - 파일별 선택한 행의 act_name 수정: /stt/update/act_id/ (POST)

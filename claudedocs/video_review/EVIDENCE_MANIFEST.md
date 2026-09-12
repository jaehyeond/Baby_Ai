# Evidence manifest — `u98cx_ZtPoY`

기록 시각: 2026-09-11 14:00 KST 전후
작업 위치: `E:\A2A\our-a2a-project\.worktrees\video-brain-20260911`
쓰기 범위: `claudedocs\video_review\**`만 사용

## 원천

- Shorts: `https://www.youtube.com/shorts/u98cx_ZtPoY`
- 표준 watch URL: `https://www.youtube.com/watch?v=u98cx_ZtPoY`
- 외부 과학 교차확인:
  - `https://www.ncbi.nlm.nih.gov/books/NBK20367/`
  - `https://www.ninds.nih.gov/sites/default/files/2025-05/know-your-brain-brian-basics.pdf`
  - `https://qbi.uq.edu.au/memory/how-are-memories-formed`
  - `https://www.brainfacts.org/brain-anatomy-and-function/cells-and-circuits/2020/making-and-breaking-connections-in-the-brain-111820`

YouTube가 제공한 자동/수동 자막은 요청 언어 `ko,en` 모두 없었다. 메타데이터의 게시자 설명에도 원 현미경 영상, 논문, 연구실 또는 실험 식별자가 없다.

## 검색·취득 절차

초기 sandbox 실행은 프록시 `127.0.0.1:9` 연결 거부로 실패했다. 승인된 외부 네트워크 실행에서 아래와 같은 명령으로 공개 자료를 취득했다. 서명된 임시 미디어 URL은 만료되므로 manifest에 복제하지 않았다.

```powershell
yt-dlp --no-cache-dir --skip-download --write-auto-subs --sub-langs 'ko,en' --sub-format vtt --write-info-json --write-thumbnail --convert-thumbnails jpg -o 'claudedocs\video_review\evidence\u98cx_ZtPoY.%(ext)s' 'https://www.youtube.com/watch?v=u98cx_ZtPoY'

yt-dlp --no-cache-dir -f '616+251' --merge-output-format mp4 -o 'claudedocs\video_review\evidence\u98cx_ZtPoY_full.%(ext)s' 'https://www.youtube.com/watch?v=u98cx_ZtPoY'
```

사용 도구: `yt-dlp 2026.08.19`, `ffmpeg/ffprobe 8.0.1`.

## 검사한 modality

| modality | 검사 내용 | 결과 |
|---|---|---|
| 메타데이터 | `info.json`의 ID, 제목, 채널, 게시일, 설명, duration | 식별 완료 |
| 영상 컨테이너 | `ffprobe` format/stream 계측 | 19.521초, 1080×1920, 30 fps, VP9 |
| 화면 | 1초 간격 20칸 contact sheet와 2초 간격 원해상도 프레임 10개 | 화면 자막 전체 순서, 장면 전환과 서로 다른 현미경 클립 확인 |
| 음성 컨테이너 | 원본 Opus stream과 파생 16 kHz mono MP3 | 음성 트랙 존재 확인 |
| 음성 내용 | 기존 로컬 Whisper `large-v3-turbo`로 자동 전사 | **품질 검증 실패, 증거에서 제외** |
| YouTube 자막 | `ko,en` 수동/자동 자막 요청 | 없음 |

## Whisper 사용과 C: 용량 경계

- 실행 파일은 이미 설치된 `C:\Users\SOGANG\AppData\Local\Programs\Python\Python312\Scripts\whisper.exe`를 사용했다.
- 모델은 이미 존재한 `C:\Users\SOGANG\.cache\whisper\large-v3-turbo.pt`를 읽었다.
- 기존 모델 크기: `1,617,941,637 bytes`; 기존 파일 수정 시각: 2026-09-03 02:06:08 KST.
- `--model_dir C:\Users\SOGANG\.cache\whisper`를 명시했다. **새 모델 다운로드와 새 설치는 0건**이다.
- 새 영상, 오디오, 프레임, 전사 산출물은 전부 E:의 전용 worktree 아래에만 저장했다.

실행 명령:

```powershell
whisper 'claudedocs\video_review\evidence\audio_16k.mp3' --model large-v3-turbo --model_dir 'C:\Users\SOGANG\.cache\whisper' --device cuda --language ko --task transcribe --output_dir 'claudedocs\video_review\evidence' --output_format all --verbose False
```

전사는 실제 19.521초 파일보다 긴 `00:00:00–00:00:29.980` 단일 구간과 일반적인 종료 문구 하나만 반환했다. 화면 자막 흐름과 대응하지 않고 종료 시각도 파일 길이를 넘으므로 hallucination으로 판정했다. `audio_16k.{json,srt,tsv,txt,vtt}`는 실패 증거로 보존했지만 보고서의 내용 근거로 사용하지 않았다. 음성 발화의 정확한 내용은 **확인 안 됨**이다.

## 주요 파일과 SHA-256

| 상대 경로 | bytes | SHA-256 | 용도 |
|---|---:|---|---|
| `evidence/u98cx_ZtPoY_full.mp4` | 3,657,557 | `F1A2F4B5543C05352582A55832622DC62D8C1D4B3E58A050325F86137D4CA940` | 실제 공개 영상 |
| `evidence/u98cx_ZtPoY.info.json` | 112,752 | `38E7CCAD59B3AC35C870BA16B16DB0C5A0D0A00A963CAD1D724E4DDDE6DACE10` | 메타데이터 |
| `evidence/contact_sheet_1s.jpg` | 179,278 | `299B061E8B8968270C2D2857CB2CBF11235C590E7ED01146A364C9A2D6C2FC1E` | 전 구간 1초 샘플 20개 |
| `evidence/audio_16k.mp3` | 157,391 | `30AED6EF1A9DEF13A38B45849805A21A0B2762576A3A16152863A3595DA10AE6` | 로컬 ASR 입력 |
| `evidence/frames/frame_01.jpg` … `frame_10.jpg` | 개별 파일 | 개별 해시는 생략 | 2초 간격 원해상도 화면 증거 |

## 한계

- 프레임 전체를 시간 순서로 검사했지만 음성 내용은 신뢰 가능한 전사를 얻지 못했다.
- 현미경 영상의 원 출처·촬영 조건·생물 종·조직·배율·표지법·실제 시간축을 확인할 자료가 없다.
- 화면은 장면 전환이 있는 몽타주다. 동일 표본의 학습 전후 연속 영상으로 해석할 수 없다.
- 채널 메타데이터와 조회·좋아요 수 같은 동적 값은 2026-09-11의 시점 자료다. 보고서에는 변하기 쉬운 조회 지표를 근거로 사용하지 않았다.
- 외부 과학 자료는 영상의 일반론을 교차확인할 뿐, 이 영상의 현미경 클립을 인증하지 않는다.

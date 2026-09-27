# 납품 기록 — 진공 압축팩 15초 광고 (영상형 v1)

- 본편: https://d2ol7oe51mr4n9.cloudfront.net/user_3Ak2xk3c9sdDOp6qbeSVoReMzNp/6df08a91-c476-4459-9cca-a147dd29166a.mp4
- 규격: 15.0초, 1080×1920, H.264/AAC 48kHz, -14.4 LUFS
- 편집: 72 BPM 박자(0.833초) 위 11컷, 음악 드롭 5.83초(노즐 컷)
- 레퍼런스: @nb_runyourway 브랜드 필름 (컷 평균 1.06초, 컷의 71%가 146.5 BPM 박자 위) — 수치만 참고, 영상·음원 미사용
- 영상: Seedance 2.5 × 8 (컷1 1080p, 나머지 720p, 컷 3·4·5·8은 상품 사진 참조 omni_reference)
- 상품 참조: 사용자 제공 사진, 판매자 로고 부분 잘라냄 (Higgsfield media 573ea88b…)
- 나레이션: ElevenLabs Harrison (여성 Chloe는 "환절기" 오인식으로 탈락)
- 음악·효과음: sound.py (trap 72 BPM, click/pop/boom/swoosh/suck, 사운드 로고) — 직접 합성
- 크레딧: 영상 244 + 음성 0.4 ≈ 245

## 게시 전 확인
- [ ] 상품 페이지(쿠팡 7597682456)와 사진 속 상품이 같은지 (사진에 PLAIN AND SIMPLE 로고)
- [ ] 청소기는 구성품이 아님 — 영상·자막에서 청소기를 언급하지 않음
- [ ] 쿠팡 파트너스 링크 → 링크 페이지 1번
- [ ] 플랫폼 AI 생성 표시 켜기

## v2 — 음악·효과음을 AI 생성으로 교체
- 본편: https://d2ol7oe51mr4n9.cloudfront.net/user_3Ak2xk3c9sdDOp6qbeSVoReMzNp/13ca16d3-0f34-47c8-8e24-ccadb1cb4018.mp4
- 규격: 15.0초, 1080×1920, AAC 48kHz, -14.0 LUFS
- 화면: v1과 동일(재편집 없음). 끝 자막을 한 줄 "프로필 링크 1번"으로 줄임
- 음악·효과음: v1 무음 영상 → Seedance 2.5 video_edit + generate_audio (113 크레딧, job db65fdeb…)
  - 프롬프트로 "대사 없음"을 요청했는데도 AI가 화면 자막을 읽는 목소리를 넣음 (Whisper 확인: "공간은 조리고고" 등)
  - demucs htdemucs로 목소리를 분리하고 반주(no_vocals)만 사용 (media 5a871a9e…)
  - AI 오디오 14.709초 → 15초로 늘림(atempo 0.9806), -18 LUFS로 맞추고 music_gain -5, 내레이션 아래에서 자동으로 소리를 줄임(덕킹)
- 유지: ElevenLabs Harrison 내레이션, sound.py 사운드 로고(12.5초)
- 구성: `script_v2.json`
- 알려진 점: 13.6초 이후 AI 반주가 거의 끝나 마지막 1.4초가 조용함(-37.5 dB)

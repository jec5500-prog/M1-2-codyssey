# 서울 일별 평균기온

- 출처: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), ERA5 재분석 데이터.
- 서울 대표 좌표: 위도 37.5665, 경도 126.9780. 개인 위치 정보가 아니다.
- 요청 기간: 2026-06-01~2026-09-30, Asia/Seoul, 122일.
- 지표: temperature_2m_mean, 일별 2m 평균기온, ℃.
- 수집일: 2026-10-25. API 응답의 격자 좌표는 요청 좌표와 다를 수 있다.
- 라이선스: [CC BY 4.0](https://open-meteo.com/en/licence), 비상업 교육용 무료 API 사용. 출처 표기: Weather data by Open-Meteo, ERA5 reanalysis.
- 원본: source-open-meteo.json. 요청 인자: source-request.json. 날짜/value/memo로 정리한 파일: seoul-temperature.csv.
- 결측/중복: 이번 응답 122건 전부 유효, 날짜 중복/결측 없음. 보간하거나 임의 값을 생성하지 않았다.
- 기상 관측소의 직접 관측값이 아니라 재분석 모델의 격자 데이터다. 증가/감소는 기온 변화이며 좋음/나쁨 판정이 아니다.
- 기온의 합계는 추가 계산 지표이며 누적 온도량의 과학적 정의로 사용하지 않는다.

검증만: `backend/.venv/Scripts/python.exe scripts/import_data.py`.
적재: `backend/.venv/Scripts/python.exe scripts/import_data.py --apply`.
대상 프로젝트는 m1-2-cody로 검사한다. 이미 있는 결정적 ID는 건너뛰며 사용자 데이터나 수정을 덮어쓰지 않는다.

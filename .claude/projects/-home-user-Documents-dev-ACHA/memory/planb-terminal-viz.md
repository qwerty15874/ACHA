---
name: planb-terminal-viz
description: ACHA Plan B는 LED 대신 터미널 그래픽으로 수막 표시 — HTML/Firebase 대신 가벼운 TUI 선택
metadata:
  type: project
---

물리 WS2812B LED가 3.3V 레벨/긴 데이터선 문제로 불안정해서(=docs/LED_문제_정리.md), 타일 수막 상태를 화면에 보여주는 Plan B를 만듦.

선택: **터미널 TUI** (`planB/terminal_view.py`). HTML+Canvas+Firebase 대시보드 안도 제안했으나, 사용자가 "가볍고 빠르게"를 우선해 터미널 쪽 채택.

**Why:** Plan B의 목적은 적은 부품으로 지금 당장 Pi에서 SSH로 동작. 브라우저/Firebase 스택은 무겁고 끊길 데가 많음.
**How to apply:** 추가 시각화/대시보드 작업은 외부 의존성 0(순수 표준 라이브러리 ANSI 트루컬러) + 기존 src/sensor.py·classifier.py 재사용 원칙 유지. HTML 대시보드는 발표·시연용으로만 고려. terminal_view.py는 하드웨어 없으면 자동 데모 폴백, threshold는 config/settings.py에서 읽음.

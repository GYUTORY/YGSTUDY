---
title: 멀티모달 입력 파이프라인 — 이미지·PDF·음성을 API로 처리하기
tags: [ai, llm, api, backend]
updated: 2026-09-24
---

# 멀티모달 입력 파이프라인

Claude와 Gemini 모두 텍스트 이외의 입력을 받는다. 그런데 "지원한다"와 "실제로 쓸 수 있다"는 다른 이야기다. 파일 크기 제한, base64 인코딩 비용, 페이지 단위 토큰 계산, 음성 포맷별 호환성 — 이 중 하나라도 모르고 붙으면 API 에러나 예상보다 10배 높은 청구서가 나온다.

이미지·PDF·음성 각각에 대해 실제 구현 시 마주치는 문제들을 중심으로 다룬다.

## API별 지원 범위

먼저 각 API가 뭘 받는지 확인해야 한다. 지원하지 않는 타입에 요청을 보내면 즉시 에러다.

| 입력 타입 | Claude (3.5 Sonnet+) | Gemini (1.5 Flash/Pro) |
|---|---|---|
| 이미지 (JPEG/PNG/GIF/WebP) | O | O |
| PDF | O (Files API, 베타) | O |
| 음성 | X | O (MP3/WAV/FLAC 등) |
| 영상 | X | O |

Claude는 음성·영상 입력을 지원하지 않는다. 음성 처리가 필요하면 Gemini를 쓰거나, Whisper로 텍스트로 변환 후 Claude에 보내야 한다. 두 방법은 비용과 정확도 면에서 차이가 있으니 용도에 따라 결정한다.

## base64 인코딩 — 언제, 어떻게

이미지를 API로 보내는 방법은 두 가지다. 공개 URL을 그대로 넘기거나, 바이트를 base64로 인코딩해서 보내거나.

URL 방식은 API 서버가 직접 이미지를 내려받는다. 내부 네트워크에 있거나 인증이 필요한 이미지라면 안 된다. 외부에서 접근 가능한 URL일 때만 쓸 수 있다. 내부 S3 버킷이나 사내 서버의 이미지는 pre-signed URL을 만들거나, 아예 base64로 보내야 한다.

```python
import anthropic
import base64
from pathlib import Path

client = anthropic.Anthropic()

# URL 방식 — 공개 접근 가능할 때만
def ask_with_url(image_url: str, question: str) -> str:
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "url", "url": image_url}},
                {"type": "text", "text": question}
            ]
        }]
    )
    return response.content[0].text

# base64 방식 — 로컬 파일, 인증 필요한 이미지
def ask_with_base64(image_path: str, question: str) -> str:
    path = Path(image_path)
    media_type_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
    }
    media_type = media_type_map.get(path.suffix.lower())
    if not media_type:
        raise ValueError(f"지원하지 않는 포맷: {path.suffix}")

    image_data = base64.standard_b64encode(path.read_bytes()).decode()

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    }
                },
                {"type": "text", "text": question}
            ]
        }]
    )
    return response.content[0].text
```

base64는 원본보다 약 33% 크다. 5MB 이미지라면 base64 문자열이 6.7MB가 된다. Claude의 이미지 크기 제한은 **원본 바이트 기준 5MB**다. 그러나 네트워크로 보내는 실제 페이로드는 base64 크기이므로 요청 바디가 예상보다 크다. 많은 이미지를 동시에 보내는 배치 파이프라인에서 네트워크 비용을 계산할 때 이 점을 빠뜨리면 안 된다.

## 파일 크기 제한 대응

| API | 방식 | 한도 |
|---|---|---|
| Claude | base64 인라인 | 이미지 5MB, PDF 32MB |
| Claude | Files API | PDF 32MB |
| Gemini | base64 인라인 | 20MB |
| Gemini | Files API | 2GB |

크기가 제한을 넘을 때 선택지는 두 가지다. 리사이즈하거나, Files API로 올리거나.

**리사이즈**

AI 분석 목적이라면 원본 해상도가 필요한 경우는 드물다. Claude는 내부적으로 이미지를 최대 1568px로 줄여서 처리한다. 그것보다 큰 이미지를 보내도 어차피 내부에서 리사이즈된다. 미리 줄여 보내면 base64 인코딩 크기와 네트워크 전송 비용 모두 줄어든다.

```python
from PIL import Image
import io

def resize_for_claude(image_bytes: bytes, max_size_mb: float = 4.5) -> bytes:
    max_bytes = int(max_size_mb * 1024 * 1024)
    if len(image_bytes) <= max_bytes:
        return image_bytes

    img = Image.open(io.BytesIO(image_bytes))

    # 긴 변 기준 1568px 이하로
    max_dim = 1568
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # 여전히 크면 JPEG 품질을 낮춘다
    buf = io.BytesIO()
    quality = 85
    while quality >= 40:
        buf.seek(0)
        buf.truncate()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= max_bytes:
            break
        quality -= 10

    return buf.getvalue()
```

리사이즈할 때 주의해야 할 점 하나가 있다. 원본보다 크게 만드는 실수다. 640px짜리 이미지를 "최대 1568px까지 허용"이라는 이유로 확대하면 품질만 나빠진다. `resize` 전에 현재 크기가 목표보다 큰지 확인해야 한다.

**Files API 재활용**

같은 이미지나 문서를 여러 요청에서 쓴다면 Files API로 한 번만 올리고 file_id를 재활용한다. Claude의 Files API는 베타이므로 헤더에 `anthropic-beta: files-api-2025-04-14`를 붙여야 한다. 업로드된 파일은 30일간 유지된다.

```python
def upload_to_files_api(client: anthropic.Anthropic, file_path: str, mime_type: str) -> str:
    with open(file_path, "rb") as f:
        response = client.beta.files.upload(
            file=(Path(file_path).name, f, mime_type),
        )
    return response.id

def ask_with_file_id(client: anthropic.Anthropic, file_id: str, question: str) -> str:
    response = client.beta.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "file", "file_id": file_id}},
                {"type": "text", "text": question}
            ]
        }],
        betas=["files-api-2025-04-14"],
    )
    return response.content[0].text
```

자주 참조하는 매뉴얼·약관·스펙 문서라면 file_id를 DB에 저장해두고 쓰는 게 맞다. 30일이 지나 만료되면 재업로드하는 로직도 필요하다.

## PDF 처리 — 페이지 단위 청킹

PDF는 Claude가 직접 받을 수 있다. 그러나 PDF가 크면 두 가지 문제가 생긴다.

첫째, 크기 제한. Claude의 PDF 한도는 32MB다. 스캔본처럼 이미지 기반 PDF는 100페이지가 넘어가면 이미 이 한도를 넘기 쉽다.

둘째, 토큰 폭발. PDF의 각 페이지는 내부적으로 이미지로 변환된다. 150페이지 PDF라면 페이지당 평균 1,500~2,000 토큰으로 계산했을 때 입력 토큰이 225,000~300,000이다. claude-opus-4-7 기준으로 입력 토큰만 $3.4~4.5가 된다.

목적에 따라 PDF 전체를 한꺼번에 보낼 필요가 없는 경우가 많다. 특정 내용을 찾는 거라면 관련 페이지만 잘라서 보내는 편이 낫다.

```python
import fitz  # PyMuPDF
import base64
import io

def split_pdf_by_pages(pdf_path: str, pages_per_chunk: int = 20) -> list[bytes]:
    doc = fitz.open(pdf_path)
    chunks = []

    for start in range(0, len(doc), pages_per_chunk):
        end = min(start + pages_per_chunk, len(doc))
        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(doc, from_page=start, to_page=end - 1)

        buf = io.BytesIO()
        chunk_doc.save(buf)
        chunks.append(buf.getvalue())
        chunk_doc.close()

    doc.close()
    return chunks

def process_pdf_in_chunks(
    client: anthropic.Anthropic,
    pdf_path: str,
    question: str,
    pages_per_chunk: int = 20
) -> list[str]:
    chunks = split_pdf_by_pages(pdf_path, pages_per_chunk)
    results = []

    for i, chunk_bytes in enumerate(chunks):
        pdf_data = base64.standard_b64encode(chunk_bytes).decode()
        response = client.beta.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_data,
                        }
                    },
                    {"type": "text", "text": f"(PDF 섹션 {i+1}/{len(chunks)}) {question}"}
                ]
            }],
            betas=["pdfs-2024-09-25"],
        )
        results.append(response.content[0].text)

    return results
```

페이지 수 기준으로 청킹하면 문단이 잘리는 문제가 생긴다. 텍스트 추출이 목적이라면 PyMuPDF로 텍스트를 먼저 뽑아 일반 텍스트로 처리하는 게 낫다. 이미지·표 분석이 필요할 때만 PDF 자체를 보내는 게 비용 면에서 합리적이다.

텍스트 레이어가 있는 PDF와 스캔본 PDF는 전혀 다르게 동작한다. 텍스트 레이어가 있으면 `page.get_text()`로 바로 뽑을 수 있고, 스캔본은 OCR이 필요하다. Claude가 PDF를 이미지로 변환해서 읽기 때문에 스캔본도 처리할 수 있지만, 텍스트 레이어가 있는 PDF를 굳이 이미지로 처리하면 토큰만 낭비한다.

## 음성 입력 처리 — Gemini

Claude는 음성 입력을 지원하지 않는다. Gemini 1.5 Flash/Pro는 MP3, WAV, FLAC, AAC, OGG, Opus 등 주요 포맷을 받는다.

음성 파일이 20MB 이하면 base64 인라인으로 보내고, 그 이상이면 Files API로 올린다.

```python
import google.generativeai as genai
from pathlib import Path

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel("gemini-1.5-flash")

AUDIO_MIME_TYPES = {
    ".mp3": "audio/mp3", ".wav": "audio/wav",
    ".flac": "audio/flac", ".aac": "audio/aac",
    ".ogg": "audio/ogg", ".opus": "audio/opus", ".m4a": "audio/m4a",
}

def transcribe_audio(audio_path: str) -> str:
    path = Path(audio_path)
    size_mb = path.stat().st_size / (1024 * 1024)
    mime_type = AUDIO_MIME_TYPES.get(path.suffix.lower(), "audio/mp3")

    if size_mb <= 20:
        audio_data = base64.standard_b64encode(path.read_bytes()).decode()
        response = model.generate_content([
            {"mime_type": mime_type, "data": audio_data},
            "이 음성을 한국어로 전사해줘. 발화자가 여럿이면 구분해서 표시해줘."
        ])
    else:
        audio_file = genai.upload_file(audio_path)
        response = model.generate_content([
            audio_file,
            "이 음성을 한국어로 전사해줘."
        ])

    return response.text
```

긴 음성 파일을 청킹할 때는 문장 경계에서 자르는 게 이상적이지만 실제로는 시간 기준으로 자를 수밖에 없다. 경계에서 단어가 잘리는 건 피할 수 없다. 청크 간 5~10초 오버랩을 두면 경계 문제가 줄어들지만 처리량이 늘어난다.

```python
def transcribe_long_audio(audio_path: str, chunk_minutes: int = 10) -> str:
    from pydub import AudioSegment

    audio = AudioSegment.from_file(audio_path)
    chunk_ms = chunk_minutes * 60 * 1000
    overlap_ms = 10 * 1000  # 10초 오버랩

    transcripts = []
    start_ms = 0

    while start_ms < len(audio):
        end_ms = min(start_ms + chunk_ms, len(audio))
        chunk = audio[start_ms:end_ms]

        buf = io.BytesIO()
        chunk.export(buf, format="mp3")
        buf.seek(0)

        audio_data = base64.standard_b64encode(buf.read()).decode()
        response = model.generate_content([
            {"mime_type": "audio/mp3", "data": audio_data},
            "음성 전사. 경계에서 잘린 문장은 자연스럽게 마무리해."
        ])
        transcripts.append(response.text)

        start_ms += chunk_ms - overlap_ms

    return "\n\n".join(transcripts)
```

Gemini의 음성 처리는 언어 감지가 자동으로 된다. 한국어와 영어가 섞인 음성도 어느 정도 처리한다. 그러나 강한 사투리나 전문 용어가 많은 경우 Whisper가 더 정확한 경우도 있다. 용도별로 두 가지를 비교해보는 게 낫다.

## 비용 계산

멀티모달 입력의 비용은 텍스트와 다른 방식으로 계산된다. 모르면 청구서 보고 당황한다.

**Claude 이미지 토큰 계산**

Claude는 이미지를 내부적으로 1568px 기준으로 리사이즈하고, 85×85px 타일로 나눠서 토큰을 계산한다. 타일당 750토큰, 기본 오버헤드 1334토큰이다.

```python
def estimate_claude_image_tokens(width: int, height: int) -> int:
    max_dim = 1568
    if max(width, height) > max_dim:
        ratio = max_dim / max(width, height)
        width = int(width * ratio)
        height = int(height * ratio)

    tile_size = 85
    tiles_x = (width + tile_size - 1) // tile_size
    tiles_y = (height + tile_size - 1) // tile_size

    return 1334 + 750 * (tiles_x * tiles_y)

# 1200×800 이미지 → 약 9,284토큰
# claude-opus-4-7 입력 $15/M 기준 → 이미지 1장당 약 $0.14
```

API 응답의 `usage.input_tokens`에 이미지 토큰이 포함되어 나온다. 예상치와 대조하면 계산이 맞는지 확인할 수 있다.

**PDF 비용**

PDF는 페이지를 이미지로 변환한 뒤 처리한다. 페이지당 1,500~2,500토큰으로 보는 게 현실적이다. 문자가 촘촘한 페이지일수록 이미지 해상도가 높아 토큰이 늘어난다.

50페이지 PDF를 claude-opus-4-7에 보내면 입력 토큰만 약 100,000개, $1.5다. 같은 PDF를 텍스트 추출 후 보내면 보통 절반 이하로 떨어진다. OCR이나 레이아웃 분석이 필요한 게 아니라면 텍스트 추출이 낫다.

**누적 추적**

```python
from dataclasses import dataclass

@dataclass
class CostTracker:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    PRICING = {
        "claude-opus-4-7":           {"input": 15.0,  "output": 75.0},
        "claude-sonnet-4-6":         {"input": 3.0,   "output": 15.0},
        "claude-haiku-4-5-20251001": {"input": 0.8,   "output": 4.0},
    }

    def add(self, usage) -> None:
        self.input_tokens  += usage.input_tokens
        self.output_tokens += usage.output_tokens

    def cost(self) -> float:
        p = self.PRICING.get(self.model, {"input": 0.0, "output": 0.0})
        return (self.input_tokens * p["input"] + self.output_tokens * p["output"]) / 1_000_000

    def report(self) -> str:
        return (
            f"입력 {self.input_tokens:,} + 출력 {self.output_tokens:,} 토큰 = ${self.cost():.4f}"
        )
```

## 실패 케이스 처리

멀티모달 파이프라인에서 자주 만나는 실패는 텍스트 전용과 다르다.

**파일 검증 — API 호출 전에**

포맷이 맞지 않거나 파일이 깨진 상태로 API를 호출하면, 에러를 받기까지 네트워크 왕복이 낭비된다. 호출 전에 로컬에서 먼저 거른다.

```python
import imghdr
from PIL import Image

def validate_image(file_bytes: bytes) -> tuple[bool, str]:
    fmt = imghdr.what(None, h=file_bytes)
    supported = {"jpeg", "png", "gif", "webp"}
    if fmt not in supported:
        return False, f"지원하지 않는 포맷: {fmt}"

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()  # 헤더만 멀쩡하고 내용이 깨진 경우 잡아낸다
    except Exception as e:
        return False, f"손상된 이미지: {e}"

    if len(file_bytes) > 5 * 1024 * 1024:
        return False, f"크기 초과: {len(file_bytes) / 1024 / 1024:.1f}MB"

    return True, ""
```

**에러 유형별 재시도**

```python
import time

def call_with_retry(request_fn, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return request_fn()

        except anthropic.BadRequestError as e:
            # 재시도해도 안 된다. 파일 자체의 문제다.
            msg = str(e)
            if "Could not process image" in msg:
                raise ValueError(f"API가 이미지를 처리하지 못함: {msg}") from e
            if "image too large" in msg.lower():
                raise ValueError("이미지 크기 초과. 리사이즈 후 재시도") from e
            raise

        except anthropic.RateLimitError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

        except anthropic.APIStatusError as e:
            if e.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise

        except anthropic.APIConnectionError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

**실제로 겪은 문제들**

*한글 스크린샷 OCR 정확도.* 이미지가 텍스트를 포함한 UI 스크린샷일 때 Claude가 한글 폰트를 틀리게 읽는 경우가 간헐적으로 생긴다. 렌더링된 텍스트를 이미지로 보내는 게 아니라 DOM이나 앱 텍스트 레이어에서 직접 추출해서 보내는 편이 낫다. 이미지로 보낼 필요가 없는 텍스트를 굳이 이미지로 보내는 구조 자체를 재검토해야 한다.

*NSFW 콘텐츠 거부.* Claude는 특정 이미지를 처리하지 않는다. `stop_reason`이 `end_turn`이더라도 응답 텍스트에 거부 의사가 담길 수 있다. 파이프라인에서 이 케이스를 조용히 통과시키면 하위 로직에서 빈 결과로 실패가 전파된다. 응답 텍스트의 첫 문장을 확인하거나, 응답 길이가 비정상적으로 짧은 경우를 따로 처리해야 한다.

*PDF 암호화.* 암호가 걸린 PDF는 API에 보내기 전에 해제해야 한다. PyMuPDF는 `fitz.open(path, password="...")` 로 열 수 있다. 비밀번호 없이 API에 보내면 `BadRequestError`가 나온다. 에러 메시지에 명확히 명시되므로 그 케이스를 별도로 처리하면 된다.

*응답 중단.* `max_tokens`를 넉넉히 잡지 않으면 응답이 도중에 잘린다. `stop_reason == "max_tokens"`면 잘린 것이다. 긴 PDF 요약처럼 출력이 클 수 있는 경우에는 `max_tokens`를 충분히 잡거나, 출력이 잘렸을 때 이어서 요청하는 로직을 붙여야 한다.

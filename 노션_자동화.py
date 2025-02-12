import requests
import json
import google.generativeai as genai
import langdetect  # 언어 감지 패키지 (설치: pip install langdetect)

# Notion & Google Gemini API 키 설정
NOTION_API_KEY = "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"
DATABASE_ID = "198e844c672180afa2fce14539f4760c"
GEMINI_API_KEY = "AIzaSyCt_u7EiEPqhkb1ByL7uIMgRV7WXQaoQFQ"

# Google Gemini API 키 설정
genai.configure(api_key=GEMINI_API_KEY)

# Notion API에서 데이터 가져오기 (Abstract 컬럼 포함)
def get_notion_content():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28"
    }

    response = requests.post(url, headers=headers)
    data = response.json()

    contents = []
    for item in data["results"]:
        title_key = "Aa Title"
        url_key = "URL"
        abstract_key = "Abstract"
        tag_key = "Tag"

        title = item["properties"].get(title_key, {}).get("title", [{}])[0].get("text", {}).get("content", "제목 없음")
        url = item["properties"].get(url_key, {}).get("url", "URL 없음")

        # Abstract 컬럼에서 데이터 가져오기
        abstract_data = item["properties"].get(abstract_key, {}).get("rich_text", [])
        original_text = abstract_data[0]["text"]["content"] if abstract_data else "원문 없음"

        tags = [tag["name"] for tag in item["properties"].get(tag_key, {}).get("multi_select", [])]
        page_id = item["id"]

        contents.append({
            "title": title,
            "url": url,
            "original_text": original_text,
            "tags": tags,
            "page_id": page_id
        })

    return contents

# 본문의 언어를 감지하고 해당 언어로 요약하는 함수
def detect_language(text):
    try:
        lang = langdetect.detect(text)
        return lang
    except:
        return "en"  # 기본값 영어

# Google Gemini API를 사용한 언어 감지 기반 요약 함수
def summarize_content_gemini(title, original_text, url):
    lang = detect_language(original_text)  # 원문의 언어 감지

    # 원문이 비어있다면 기본 텍스트 설정
    if not original_text or original_text == "원문 없음":
        original_text = "현재 원문이 제공되지 않았습니다. 제목과 관련된 내용을 요약합니다."

    prompt = f"""
아래 내용을 {'영어' if lang == 'en' else '한국어'}로 요약해줘.
원문을 유지하면서 요약을 추가해야 해.
핵심 개념, 주요 내용, 실전 적용 방법을 포함해서 정리해줘.

제목: {title}
원문: {original_text}
관련 링크: {url}

요약 (Summary):
핵심 개념:
- (이 글에서 설명하는 가장 중요한 개념을 요약)

상세 설명:
- (주요 내용을 7~8 문장으로 설명)

실전 적용 방법:
- (이 내용을 적용해서 어떤 결론이 나고 적용할 수 있는지 설명)

관련 링크:
- {url}
"""

    model = genai.GenerativeModel("gemini-2.0-flash-lite-preview-02-05")
    response = model.generate_content(prompt)

    return response.text.strip()

# Notion의 "Abstract" 컬럼에 원문 + 요약 저장
def update_notion_summary(page_id, original_text, summary):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    combined_text = f"""
원문 (Original Content):
{original_text if original_text != '원문 없음' else '현재 원문이 제공되지 않았습니다.'}

---

요약 (Summary):
{summary}
"""

    data = {
        "properties": {
            "Abstract": {"rich_text": [{"text": {"content": combined_text}}]}
        }
    }

    response = requests.patch(url, headers=headers, data=json.dumps(data))
    return response.status_code

# 실행: Notion 콘텐츠 가져오기 → Google Gemini로 요약 → Notion 업데이트
notion_contents = get_notion_content()

for content in notion_contents:
    summary = summarize_content_gemini(content["title"], content["original_text"], content["url"])
    update_notion_summary(content["page_id"], content["original_text"], summary)
    print(f"'{content['title']}' 요약 완료 & Notion 업데이트!")

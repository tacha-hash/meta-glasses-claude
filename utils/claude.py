import os
import json
import base64
import subprocess
import tempfile
from datetime import datetime

import requests

CLAUDE_CLI = os.getenv('CLAUDE_CLI', 'claude')
MODEL = os.getenv('CLAUDE_MODEL', 'claude-opus-4-7')
CWD = os.getenv('CLAUDE_CWD', '/tmp')

retrieve_message_type_from_message_description = '''
Based on the message type, execute some different requests to APIs or other tools.
- calendar: types are related to anything with scheduling, events, reminders, etc.
- image: types are related to anything with images, pictures, what's the user looking at, what's in front of the user, etc.
- notion: anything related to storing a note, save an idea, notion, etc.
- search: types are related to anything with searching, finding, looking for, and it's about a recent event, or news etc.
- other: types are related to anything else.

Make sure to always return the message type, or default to `other` even if it doesn't match any of the types.
'''.strip()


def _run(prompt: str, system: str = None, timeout: int = 120) -> str:
    cmd = [CLAUDE_CLI, '-p', '--model', MODEL, '--output-format', 'json']
    if system:
        cmd += ['--append-system-prompt', system]
    cmd.append(prompt)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=CWD)
    if result.returncode != 0:
        raise RuntimeError(f'claude CLI failed (rc={result.returncode}): {result.stderr[:500]}')
    try:
        data = json.loads(result.stdout)
        return (data.get('result') or '').strip()
    except json.JSONDecodeError:
        return result.stdout.strip()


def _run_json(prompt: str, system: str = None, timeout: int = 120) -> dict:
    text = _run(prompt, system=system, timeout=timeout)
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1] if lines[-1].startswith('```') else lines[1:])
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print('Failed to parse JSON from Claude:', text[:300])
        return {}


def simple_prompt_request(message: str) -> str:
    return _run(message)


def generate_google_search_query(user_input: str) -> str:
    return _run(
        f'''You are a Google Search Expert. You task is to convert unstructured user inputs to optimized Google search queries. Example: USER INPUT: 'Best places to visit in Colombia?' OPTIMIZED Google Search Query: 'Top 10 Colombia tourist destinations'.
Convert the following user query into a optimized Google Search query: "{user_input}"
Reply with ONLY the query, no quotes, no explanation.'''
    )


def retrieve_scraped_data_short_answer(news_content: str, user_query: str) -> str:
    return _run(
        f'''You are a helpful assistant. Take the user query and the text from scraped data of articles/news/pages, and return a short condensed answer to the user query based on the scraped data, use 10 to 15 words.
Context: {news_content}
User Query: {user_query}'''
    )


def analyze_image(img_url: str, prompt: str) -> str:
    os.makedirs('media', exist_ok=True)
    image_path = 'media/' + img_url.split('/')[-1]
    download_image = requests.get(img_url)
    print('Downloaded image', download_image.status_code, image_path)
    with open(image_path, 'wb') as f:
        f.write(download_image.content)

    abs_path = os.path.abspath(image_path)
    full_prompt = f'{prompt}\n\nThe image is at this absolute path: {abs_path}\nUse the Read tool to view it, then answer.'
    return _run(full_prompt, timeout=180)


def retrieve_message_type_from_message(message: str) -> str:
    print('retrieve_message_type_from_message', message)
    if not message:
        return ''
    system = retrieve_message_type_from_message_description
    prompt = f'''User message: "{message}"

Classify the user's intent. Reply with a single JSON object: {{"message_type": "<one of: calendar, image, notion, search, other>"}}
No markdown fences, no extra text — only the JSON object.'''
    args = _run_json(prompt, system=system)
    mtype = args.get('message_type', 'other')
    if mtype not in ('calendar', 'image', 'notion', 'search', 'other'):
        mtype = 'other'
    print('retrieve_message_type_from_message response:', mtype)
    return mtype


def determine_calendar_event_inputs(message: str) -> dict:
    today = datetime.now().strftime('%Y-%m-%d')
    system = f'''Based on the message, create a Google Calendar event.
Today is {today}, so if the user says "tomorrow", "next week", etc., calculate the correct date.'''
    prompt = f'''User message: "{message}"

Reply with a single JSON object matching this schema (no markdown fences, no extra text):
{{
  "title": "<event title>",
  "description": "<description or empty string>",
  "date": "<YYYY-MM-DD>",
  "time": "<HH:MM 24-hour>",
  "duration": <hours as number, default 1; if type is reminder default 0.5>,
  "type": "<one of: reminder, event, time-block; default event>"
}}'''
    args = _run_json(prompt, system=system)
    return {
        'title': args.get('title', ''),
        'description': args.get('description', ''),
        'date': args.get('date', today),
        'time': args.get('time', '09:00'),
        'duration': args.get('duration', 1),
        'type': args.get('type', 'event'),
    }


def determine_notion_page_inputs(message: str) -> dict:
    system = '''Based on the message, create a new Notion page.
Category rules:
- `Idea` for business idea, entrepreneurship, making money
- `Work` for work or project
- `Personal` for personal stuff, relationships, personal finance
- `Note` for anything else'''
    prompt = f'''User message: "{message}"

Reply with a single JSON object matching this schema (no markdown fences, no extra text):
{{
  "title": "<page title>",
  "category": "<one of: Note, Idea, Work, Personal>",
  "content": "<the content in the user's own words>"
}}'''
    args = _run_json(prompt, system=system)
    return {
        'title': args.get('title', ''),
        'category': args.get('category', 'Note'),
        'content': args.get('content', message),
    }

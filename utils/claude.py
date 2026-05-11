import os
import base64
from datetime import datetime

import requests
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

MODEL = os.getenv('CLAUDE_MODEL', 'claude-opus-4-7')

retrieve_message_type_from_message_description = '''
Based on the message type, execute some different requests to APIs or other tools.
- calendar: types are related to anything with scheduling, events, reminders, etc.
- image: types are related to anything with images, pictures, what's the user looking at, what's in front of the user, etc.
- notion: anything related to storing a note, save an idea, notion, etc.
- search: types are related to anything with searching, finding, looking for, and it's about a recent event, or news etc.
- other: types are related to anything else.

Make sure to always return the message type, or default to `other` even if it doesn't match any of the types.
'''.replace('    ', '')

determine_calendar_event_inputs_description = lambda: f'''Based on the message, create an event using the Google Calendar API.
- title: The title of the event
- description: The description of the event, if any, if not return an empty string
- date: The date of the event in the format `YYYY-MM-DD`. Today is {datetime.now().strftime('%Y-%m-%d')}, so if the user says "tomorrow", or in 1 week, etc, make sure to calculate the correct date.
- time: The time of the event in the format `HH:MM`
- duration: The duration of the event in hours
- type: The type of message the user sent, default to `event`

Make sure to return all the required inputs for the event creation.'''

determine_notion_page_inputs_description = '''Based on the message, create a new page in your Notion database.
- title: The title of the page
- category: The category of the page, default to `Note`
- content: The content of the message in the user words (without more detail, just in user words)

Make sure to return all the required inputs for the page creation.'''


def _call(messages, max_tokens=400, system=None, tools=None, tool_choice=None):
    kwargs = dict(model=MODEL, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs['system'] = system
    if tools:
        kwargs['tools'] = tools
    if tool_choice:
        kwargs['tool_choice'] = tool_choice
    return client.messages.create(**kwargs)


def simple_prompt_request(message: str):
    resp = _call([{'role': 'user', 'content': message}], max_tokens=300)
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            return block.text.strip()
    return ''


def generate_google_search_query(user_input: str):
    return simple_prompt_request(
        f'''You are a Google Search Expert. You task is to convert unstructured user inputs to optimized Google search queries. Example: USER INPUT: 'Best places to visit in Colombia?' OPTIMIZED Google Search Query: 'Top 10 Colombia tourist destinations'.
Convert the following user query into a optimized Google Search query: "{user_input}"'''
    )


def retrieve_scraped_data_short_answer(news_content: str, user_query: str):
    return simple_prompt_request(
        f'''You are a helpful assistant, You take the user query and the text from scraped data of articles/news/pages, and return a short condenseated answer to the user query based on the scraped data, use 10 to 15 words.
Context: {news_content}
User Query: {user_query}'''
    )


def analyze_image(img_url: str, prompt: str):
    image_path = 'media/' + img_url.split('/')[-1]
    download_image = requests.get(img_url)
    print('Downloaded image', download_image.status_code, image_path)
    with open(image_path, 'wb') as f:
        f.write(download_image.content)

    with open(image_path, 'rb') as f:
        data = base64.standard_b64encode(f.read()).decode('utf-8')

    ext = image_path.rsplit('.', 1)[-1].lower()
    media_type = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}.get(ext, 'image/jpeg')

    resp = _call([{
        'role': 'user',
        'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': data}},
            {'type': 'text', 'text': prompt},
        ],
    }], max_tokens=400)
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            return block.text.strip()
    return ''


def _extract_tool_use(resp, tool_name):
    for block in resp.content:
        if getattr(block, 'type', None) == 'tool_use' and block.name == tool_name:
            return block.input
    return None


def retrieve_message_type_from_message(message: str):
    print('retrieve_message_type_from_message', message)
    if not message:
        return ''

    tool_name = 'execute_based_on_message_type'
    tools = [{
        'name': tool_name,
        'description': retrieve_message_type_from_message_description,
        'input_schema': {
            'type': 'object',
            'properties': {
                'message_type': {
                    'type': 'string',
                    'enum': ['calendar', 'image', 'notion', 'search', 'other'],
                    'description': 'The type of message the user sent',
                }
            },
            'required': ['message_type'],
        },
    }]
    resp = _call(
        [{'role': 'user', 'content': message}],
        tools=tools,
        tool_choice={'type': 'tool', 'name': tool_name},
        max_tokens=200,
    )
    args = _extract_tool_use(resp, tool_name) or {}
    mtype = args.get('message_type', 'other')
    print('retrieve_message_type_from_message response:', mtype)
    return mtype


def determine_calendar_event_inputs(message: str):
    tool_name = 'determine_calendar_event_inputs'
    tools = [{
        'name': tool_name,
        'description': determine_calendar_event_inputs_description(),
        'input_schema': {
            'type': 'object',
            'properties': {
                'title': {'type': 'string', 'description': 'The title of the event'},
                'description': {'type': 'string', 'description': 'The description of the event, if any, if not return an empty string'},
                'date': {'type': 'string', 'description': 'The date of the event in the format YYYY-MM-DD'},
                'time': {'type': 'string', 'description': 'The time of the event in the format HH:MM'},
                'duration': {'type': 'number', 'description': 'The duration of the event in hours, default is 1 hour, but if type is `reminder`, default to 0.5 hours.'},
                'type': {'type': 'string', 'enum': ['reminder', 'event', 'time-block'], 'description': 'The type of message the user sent, default to `event`'},
            },
            'required': ['title', 'date', 'time'],
        },
    }]
    resp = _call(
        [{'role': 'user', 'content': message}],
        tools=tools,
        tool_choice={'type': 'tool', 'name': tool_name},
        max_tokens=400,
    )
    args = _extract_tool_use(resp, tool_name) or {}
    return {
        'title': args.get('title', ''),
        'description': args.get('description', ''),
        'date': args.get('date', datetime.now().strftime('%Y-%m-%d')),
        'time': args.get('time', '09:00'),
        'duration': args.get('duration', 1),
        'type': args.get('type', 'event'),
    }


def determine_notion_page_inputs(message: str):
    tool_name = 'determine_notion_page_inputs'
    tools = [{
        'name': tool_name,
        'description': determine_notion_page_inputs_description,
        'input_schema': {
            'type': 'object',
            'properties': {
                'title': {'type': 'string', 'description': 'The title of the page'},
                'category': {
                    'type': 'string',
                    'enum': ['Note', 'Idea', 'Work', 'Personal'],
                    'description': 'The category of the page, default to `Note`. If it is a business idea, or something about entrepreneurship, or about making money, use `Idea`. If it is about work, or a project, use `Work`. If it is about personal stuff, use `Personal`. Else, use `Note`.',
                },
                'content': {'type': 'string', 'description': 'The content of the message in the user words'},
            },
            'required': ['title', 'category', 'content'],
        },
    }]
    resp = _call(
        [{'role': 'user', 'content': message}],
        tools=tools,
        tool_choice={'type': 'tool', 'name': tool_name},
        max_tokens=400,
    )
    args = _extract_tool_use(resp, tool_name) or {}
    return {
        'title': args.get('title', ''),
        'category': args.get('category', 'Note'),
        'content': args.get('content', message),
    }

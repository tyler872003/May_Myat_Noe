import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .context import build_facts
from .free_answers import answer_without_ai
from .llm import ask_llm, llm_enabled, provider

logger = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 500
DAILY_LIMIT = 30          # questions per user per day (protects your free quota)
HISTORY_MESSAGES = 6      # how many past messages the AI sees


@login_required
def chat(request):
    return render(request, 'assistant/chat.html', {
        'ai_enabled': llm_enabled(),
        'provider': provider(),
        'history': request.session.get('chat', []),
    })


@login_required
@require_POST
def ask(request):
    try:
        question = (json.loads(request.body).get('question') or '').strip()
    except (ValueError, AttributeError):
        return JsonResponse({'error': 'Invalid request.'}, status=400)
    if not question:
        return JsonResponse({'error': 'Please type a question.'}, status=400)
    if len(question) > MAX_QUESTION_CHARS:
        return JsonResponse({'error': f'Please keep questions under {MAX_QUESTION_CHARS} characters.'}, status=400)

    today = timezone.localdate()
    key = f'assistant:{request.user.pk}:{today.isoformat()}'
    used = cache.get(key, 0)
    if used >= DAILY_LIMIT:
        return JsonResponse({'error': 'Daily question limit reached. Please try again tomorrow.'}, status=429)
    cache.set(key, used + 1, 60 * 60 * 26)

    facts = build_facts(request.user, today)
    chat_history = request.session.get('chat', [])

    if llm_enabled():
        try:
            answer = ask_llm(question, chat_history[-HISTORY_MESSAGES:], request.user, today)
            chat_history = chat_history + [{'role': 'user', 'content': question},
                                        {'role': 'assistant', 'content': answer}]
            request.session['chat'] = chat_history[-12:]       # only save real AI answers
        except Exception as exc:
            logger.exception('AI request failed')
            facts = build_facts(request.user, today)
            answer = answer_without_ai(question, facts) + '\n\n' + _fallback_note(exc)
    else:
        facts = build_facts(request.user, today)
        answer = answer_without_ai(question, facts)
    return JsonResponse({'answer': answer})


@login_required
@require_POST
def clear(request):
    request.session['chat'] = []
    return JsonResponse({'ok': True})

def _fallback_note(exc):
    text = str(exc)
    code = getattr(exc, 'code', None)
    if 'location is not supported' in text:
        return '(Gemini is not available from your location, so this answer comes from built-in rules.)'
    if code == 429:
        return '(The free Gemini quota is used up for now, so this answer comes from built-in rules.)'
    if code in (500, 503):
        return "(Google's AI is busy right now, so this answer comes from built-in rules.)"
    if code in (400, 401, 403, 404):
        return '(The AI settings need fixing: check the API key and model name. This answer comes from built-in rules.)'
    return '(The AI could not be reached, so this answer comes from built-in rules.)'

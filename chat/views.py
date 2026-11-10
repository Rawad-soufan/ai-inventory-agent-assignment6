import logging

from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .agent import run_agent


def chat_view(request):
    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if user_message:
            history = request.session.get("history", [])
            interaction_id = request.session.get("interaction_id")

            history.append({"role": "user", "text": user_message})

            try:
                answer, new_id = run_agent(user_message, interaction_id)
                request.session["interaction_id"] = new_id
            except Exception:
                logging.getLogger(__name__).exception("Inventory agent request failed")
                answer = "The agent is unavailable. Check the server configuration and try again."

            history.append({"role": "agent", "text": answer})
            request.session["history"] = history

        return redirect("chat")

    return render(request, "chat.html", {
        "history": request.session.get("history", []),
    })


def reset_view(request):
    request.session.flush()
    return redirect("chat")


def health_view(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})

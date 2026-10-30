"""Whole-message context selection without additional inference calls."""
import re

MAX_NOTE = 2000


def select_history(history, prompt, budget):
    """Keep a recent tail and retrieve relevant old user/assistant groups.

    Original text is preserved, in chronological order. No generated summary or
    trusted system instructions are constructed from user/assistant text.
    """
    valid = [m for m in history if m.get("role") in ("user", "assistant")
             and isinstance(m.get("content"), str)]
    groups = []
    for message in valid:
        if message["role"] == "assistant" and not groups:
            continue
        if message["role"] == "user":
            groups.append([])
        groups[-1].append({"role": message["role"], "content": message["content"]})
    selected, used = set(), 0
    costs = [sum(len(m["content"]) for m in group) for group in groups]
    # First reserve up to 65% for complete recent turns; always try the latest.
    for index in reversed(range(len(groups))):
        cost = costs[index]
        if used + cost <= budget and (not selected or used + cost <= budget * .65):
            selected.add(index)
            used += cost
        else:
            break
    terms = set(re.findall(r"\w{3,}", prompt.casefold()))
    ranked = sorted((i for i in range(len(groups)) if i not in selected),
                    key=lambda i: (-sum(t in " ".join(m["content"] for m in groups[i]).casefold() for t in terms), -i))
    for index in ranked:
        if used + costs[index] <= budget:
            selected.add(index)
            used += costs[index]
    messages = [m for i in sorted(selected) for m in groups[i]]
    return messages, len(valid) - len(messages)

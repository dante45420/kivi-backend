import unicodedata


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return ' '.join(s.split())


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(
                curr[-1] + 1,        # insertion
                prev[j] + 1,          # deletion
                prev[j - 1] + cost,   # substitution
            ))
        prev = curr
    return prev[-1]


def similarity_score(query: str, target: str) -> int:
    qa = normalize_text(query)
    ta = normalize_text(target)
    if not qa or not ta:
        return 0
    if qa == ta:
        return 100
    if qa in ta:
        return 90 if len(qa) >= 3 else 80
    # Token-based overlap with simple plural handling (es/ s) and exceptions
    def singularize_token(tok: str) -> str:
        if not tok or len(tok) < 3:
            return tok
        exceptions = {"hass"}
        if tok in exceptions:
            return tok
        if tok.endswith("es") and len(tok) > 4:
            return tok[:-2]
        if tok.endswith("s") and len(tok) > 3:
            return tok[:-1]
        return tok

    q_tokens = [singularize_token(t) for t in qa.split()]
    t_tokens = [singularize_token(t) for t in ta.split()]
    qs = set(q_tokens)
    ts = set(t_tokens)
    if qs and ts:
        inter = len(qs & ts)
        union = len(qs | ts) or 1
        jacc = inter / union
        # Strong token overlap -> high similarity
        if jacc >= 0.66 or qs.issubset(ts) or ts.issubset(qs):
            return 85
        if jacc >= 0.4:
            return 75
    dist = levenshtein(qa, ta)
    max_len = max(len(qa), len(ta)) or 1
    sim = int(100 * (1 - dist / max_len))
    return sim


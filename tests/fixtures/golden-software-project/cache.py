def cache_policy(load: int, threshold: int = 8) -> str:
    return "bypass" if load >= threshold else "reuse"

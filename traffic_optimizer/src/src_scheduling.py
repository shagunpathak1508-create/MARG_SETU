def generate_schedule(vehicles, batch_size=20):
    """
    Split `vehicles` into fixed-size batches of `batch_size`.
    Returns a list of dicts with token_start, token_end, and time_slot.
    """
    schedule = []
    batch_num = 1
    token = 1

    while token <= vehicles:
        token_end = min(token + batch_size - 1, vehicles)
        schedule.append({
            "batch":       batch_num,
            "token_start": token,
            "token_end":   token_end,
            "vehicles":    token_end - token + 1,
            "time_slot":   f"{(batch_num - 1) * 2}-{batch_num * 2} minutes",
        })
        token += batch_size
        batch_num += 1

    return schedule
from adapters.cell_slots_qa import verify as _verify

def verify(*args, **kwargs):
    return _verify(*args, platform='figma', **kwargs)

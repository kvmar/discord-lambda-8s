def set_default(obj):
  if isinstance(obj, set):
    return list(obj)
  raise TypeError
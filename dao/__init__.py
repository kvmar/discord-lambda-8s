import decimal
import json


class DecimalEncoder(json.JSONEncoder):
  def default(self, o):
    if isinstance(o, decimal.Decimal):
      return str(o)
    return super().default(o)
def set_default(obj):
  if isinstance(obj, set):
    return list(obj)
  raise TypeError
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
  if isinstance(obj, decimal.Decimal):
    # DynamoDB returns all numbers as Decimal; convert to int when lossless, else float
    return int(obj) if obj == int(obj) else float(obj)
  raise TypeError
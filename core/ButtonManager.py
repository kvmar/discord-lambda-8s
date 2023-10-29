from core import QueueManager


def button_flow_tree(custom_id: str):
  if custom_id == QueueManager.join_queue_custom_id:
    join_queue_button()


def join_queue_button():
  print("Join queue button clicked")
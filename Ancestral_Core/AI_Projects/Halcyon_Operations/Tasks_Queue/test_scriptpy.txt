from task_manager import TaskManager

def test_function():
    print("Test task executed!")

manager = TaskManager()
manager.add_task("Test Task", test_function, priority=1)

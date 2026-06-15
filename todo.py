#!/usr/bin/env python3
"""
A command-line To-Do app with JSON file storage.
Features: add, list, done, delete, clear-done, priority, due date, edit
Usage: python todo.py [command] [arguments]
"""

import json
import os
import sys
from datetime import datetime

TODO_FILE = "todos.json"

PRIORITIES = {"high": "🔴", "medium": "🟡", "low": "🟢"}
PRIORITY_ORDER = {"high": 1, "medium": 2, "low": 3}


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_todos():
    if not os.path.exists(TODO_FILE):
        return []
    with open(TODO_FILE, "r") as f:
        return json.load(f)


def save_todos(todos):
    with open(TODO_FILE, "w") as f:
        json.dump(todos, f, indent=2)


def next_id(todos):
    return max((t["id"] for t in todos), default=0) + 1


def parse_flags(args):
    """Extract --priority and --due from args. Returns (remaining_args, priority, due)."""
    priority = "medium"
    due = None
    remaining = []
    i = 0
    while i < len(args):
        if args[i] == "--priority" and i + 1 < len(args):
            p = args[i + 1].lower()
            if p not in PRIORITIES:
                print(f"⚠️  Invalid priority '{p}'. Choose: high, medium, low")
                sys.exit(1)
            priority = p
            i += 2
        elif args[i] == "--due" and i + 1 < len(args):
            due = args[i + 1]
            # Validate date format
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                print(f"⚠️  Invalid date '{due}'. Use format: YYYY-MM-DD (e.g. 2025-12-31)")
                sys.exit(1)
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return remaining, priority, due


def format_due(due_str):
    """Return colored due date string based on urgency."""
    if not due_str:
        return ""
    today = datetime.today().date()
    due_date = datetime.strptime(due_str, "%Y-%m-%d").date()
    diff = (due_date - today).days
    if diff < 0:
        return f" \033[91m[OVERDUE: {due_str}]\033[0m"
    elif diff == 0:
        return f" \033[93m[Due TODAY]\033[0m"
    elif diff <= 3:
        return f" \033[93m[Due: {due_str}]\033[0m"
    else:
        return f" \033[2m[Due: {due_str}]\033[0m"


# ── Commands ──────────────────────────────────────────────────────────────────

def add_task(args):
    """Add a new task. Args include title words and optional --priority / --due flags."""
    remaining, priority, due = parse_flags(args)
    if not remaining:
        print("⚠️  Please provide a task title. E.g.: python todo.py add Buy milk --priority high --due 2025-12-31")
        return
    title = " ".join(remaining)
    todos = load_todos()
    task = {
        "id": next_id(todos),
        "title": title,
        "done": False,
        "priority": priority,
        "due": due,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    todos.append(task)
    save_todos(todos)
    due_info = f"  Due: {due}" if due else ""
    print(f"✅ Added [{task['id']}]: {title}  |  Priority: {priority}{due_info}")


def list_tasks(show_all=False):
    """List tasks sorted by priority then due date."""
    todos = load_todos()
    if not todos:
        print("📭 No tasks yet. Add one with: python todo.py add <task>")
        return

    filtered = todos if show_all else [t for t in todos if not t["done"]]
    if not filtered:
        print("🎉 All tasks are done! Use --all to see completed tasks.")
        return

    # Sort: pending by priority + due date, done tasks at bottom
    def sort_key(t):
        p = PRIORITY_ORDER.get(t.get("priority", "medium"), 2)
        d = t.get("due") or "9999-99-99"
        done = 1 if t["done"] else 0
        return (done, p, d)

    filtered.sort(key=sort_key)

    label = "All" if show_all else "Pending"
    print(f"\n{'─'*55}")
    print(f"  {label} Tasks")
    print(f"{'─'*55}")
    for t in filtered:
        status  = "✔" if t["done"] else "○"
        pri_icon = PRIORITIES.get(t.get("priority", "medium"), "🟡")
        due_str  = format_due(t.get("due"))
        if t["done"]:
            title_str = f"\033[9m{t['title']}\033[0m"
        else:
            title_str = t["title"]
        created = f"\033[2m({t['created_at']})\033[0m"
        print(f"  [{t['id']:>3}] {status} {pri_icon}  {title_str}{due_str}  {created}")
    print(f"{'─'*55}\n")


def complete_task(task_id):
    todos = load_todos()
    for task in todos:
        if task["id"] == task_id:
            if task["done"]:
                print(f"ℹ️  Task [{task_id}] is already done.")
            else:
                task["done"] = True
                save_todos(todos)
                print(f"✔️  Completed task [{task_id}]: {task['title']}")
            return
    print(f"❌ No task found with ID {task_id}.")


def delete_task(task_id):
    todos = load_todos()
    new_todos = [t for t in todos if t["id"] != task_id]
    if len(new_todos) == len(todos):
        print(f"❌ No task found with ID {task_id}.")
    else:
        save_todos(new_todos)
        print(f"🗑️  Deleted task [{task_id}].")


def clear_done():
    todos = load_todos()
    pending = [t for t in todos if not t["done"]]
    removed = len(todos) - len(pending)
    save_todos(pending)
    print(f"🧹 Removed {removed} completed task(s).")


def edit_task(args):
    """
    Edit a task's title, priority, and/or due date.
    Usage: python todo.py edit <id> [new title words] [--priority <p>] [--due <date>]
    At least one of title / --priority / --due must be provided.
    """
    if not args or not args[0].isdigit():
        print("⚠️  Please provide a valid task ID. E.g.: python todo.py edit 3 New title --priority high")
        return

    task_id = int(args[0])
    remaining, priority, due = parse_flags(args[1:])

    todos = load_todos()
    for task in todos:
        if task["id"] == task_id:
            changes = []

            # Update title only if words were provided after the ID
            if remaining:
                new_title = " ".join(remaining)
                task["title"] = new_title
                changes.append(f"title → \"{new_title}\"")

            # Update priority only if explicitly passed
            if "--priority" in sys.argv:
                task["priority"] = priority
                changes.append(f"priority → {priority}")

            # Update due only if explicitly passed
            if "--due" in sys.argv:
                task["due"] = due
                changes.append(f"due → {due if due else 'removed'}")

            if not changes:
                print("⚠️  Nothing to update. Provide a new title, --priority, or --due.")
                return

            save_todos(todos)
            print(f"✏️  Updated task [{task_id}]: {', '.join(changes)}")
            return

    print(f"❌ No task found with ID {task_id}.")


# ── CLI entry point ───────────────────────────────────────────────────────────

HELP = """
Usage: python todo.py <command> [args]

Commands:
  add <title> [--priority high|medium|low] [--due YYYY-MM-DD]
                     Add a new task
  list               List pending tasks (sorted by priority & due date)
  list --all         List all tasks including completed
  done <id>          Mark a task as complete
  delete <id>        Delete a task
  clear-done         Remove all completed tasks
  edit <id> [new title] [--priority high|medium|low] [--due YYYY-MM-DD]
                     Edit a task's title, priority, or due date
  help               Show this help message

Examples:
  python todo.py add Buy groceries --priority high --due 2025-07-01
  python todo.py edit 2 Read a book --priority low
  python todo.py edit 3 --due 2025-08-15
  python todo.py list --all
"""


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        print(HELP)

    elif args[0] == "add":
        add_task(args[1:])

    elif args[0] == "list":
        show_all = "--all" in args
        list_tasks(show_all)

    elif args[0] == "done":
        if len(args) < 2 or not args[1].isdigit():
            print("⚠️  Please provide a valid task ID. E.g.: python todo.py done 3")
        else:
            complete_task(int(args[1]))

    elif args[0] == "delete":
        if len(args) < 2 or not args[1].isdigit():
            print("⚠️  Please provide a valid task ID. E.g.: python todo.py delete 3")
        else:
            delete_task(int(args[1]))

    elif args[0] == "clear-done":
        clear_done()

    elif args[0] == "edit":
        edit_task(args[1:])

    else:
        print(f"❓ Unknown command: '{args[0]}'. Run 'python todo.py help' for usage.")


if __name__ == "__main__":
    main()
import curses
import random
import string
import argparse
import json

from dataclasses import dataclass

NAVIGATION_TEXT = "[s] Save [q] Quit [r] Remove label [n] Next"
QUIT_NAVIGATION_TEXT = "Do you want to save before quitting? [y] Yes [n] No"
# TODO: add number of tasks in labeling job and other meta information to status window to the right
# TODO: remove quit dialog when saved and there are no changes


@dataclass
class COLOR:
    GREY: int = 235


class Job:
    def __init__(self, path: str):
        self.path = path
        self.last_random_index = -1

    def load(self):
        with open(self.path) as f:
            job_json: dict = json.load(f)
        self.name = job_json["name"]
        self.type = job_json["type"]
        self.labels = job_json["labels"]
        self.tasks = job_json["tasks"]

    def next_task(self):
        for i, task in enumerate(self.tasks):
            if "label" not in task:
                return i, task
        
        random_index = self.last_random_index
        while random_index == self.last_random_index:
            random_index = random.randrange(0, len(self.tasks))
        self.last_random_index = random_index
        return random_index, self.tasks[random_index]

    def remove_label(self, task_index: int):
        self.tasks[task_index]["label"] = None
        return task_index, self.tasks[task_index]

    def add_label(self, task_index: int, label_index: int):
        self.tasks[task_index]["label"] = self.labels[label_index]
        return task_index, self.tasks[task_index]

    def save(self):
        job_json = {
            "name": self.name,
            "type": self.type,
            "labels": self.labels,
            "tasks": self.tasks
        }
        with open(self.path, "w") as f:
            json.dump(job_json, f, indent=4)


class GUI:
    def __init__(self, screen: curses.window, labels):
        self.screen = screen
        self.labels = labels

    def init(self):
        self.init_screen()
        self.init_colors()
        self.init_windows()
        self.init_labels()

    def init_screen(self):
        self.screen.nodelay(1)
        self.height, self.width = self.screen.getmaxyx()

        curses.curs_set(0)

    def init_colors(self):
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(99, curses.COLOR_WHITE, COLOR.GREY)

    def init_windows(self):
        self.meta_window = curses.newwin(1, self.width, 0, 0)
        self.content_window = curses.newwin(self.height-3, self.width, 1, 0)
        self.labels_window = curses.newwin(1, self.width, self.height-3, 0)
        self.navigation_window = curses.newwin(1, self.width, self.height-2, 0)
        self.status_window = curses.newwin(1, self.width, self.height-1, 0)

        self.labels_window.bkgd(curses.color_pair(99))
        self.meta_window.bkgd(curses.color_pair(99))
        self.navigation_window.bkgd(curses.color_pair(99) | curses.A_BOLD)
        
        self.navigation_window.addstr(NAVIGATION_TEXT)

        self.meta_window.refresh()
        self.content_window.refresh()
        self.labels_window.refresh()
        self.navigation_window.refresh()
        self.status_window.refresh()

    def init_labels(self):
        i = 0
        ci = 1
        for i, label in enumerate(self.labels):
            self.labels_window.addstr(f"[{i+1}] {label} ", curses.color_pair(ci))
            ci += 1
            if ci == 6:
                ci = 0
        self.labels_window.refresh()

    def update_content(self, text: str):
        self.content_window.addstr(0, 0, text)
        self.content_window.refresh()

    def update_meta(self, task_index, task):
        meta_text = []
        meta_text.append(f"index: {task_index}")
        for k, v in task["meta"].items():
            meta_text.append(f"{k}: {v}")
        if "label" in task:
            if task["label"] is None:
                meta_text.append("label: *")
            else:
                meta_text.append(f"label: {task['label']}")
        else:
            meta_text.append("label: *")

        meta_text = " ".join(meta_text)
        self.meta_window.clear()
        self.meta_window.addstr(meta_text)
        self.meta_window.refresh()

    def update_status(self, text):
        self.status_window.clear()
        self.status_window.addstr(text)
        self.status_window.refresh()

    def get_key(self) -> str:
        key = self.navigation_window.getch()
        if key == curses.KEY_RESIZE:
            return "resize"
        else:
            return chr(key)

    def switch_to_quit_navigation(self):
        self.navigation_window.clear()
        self.navigation_window.addstr(QUIT_NAVIGATION_TEXT)
        self.navigation_window.refresh()


def random_text(n_words):
    words = []
    for i in range(n_words):
        n_chars = random.randint(3, 10)
        word = ""
        for j in range(n_chars):
            word += random.choice(string.ascii_lowercase)
        words.append(word)

    return " ".join(words)


def bootstrap_job():
    job = {
        "name": "Dummy Job",
        "type": "clf",
        "labels": ["short", "middle", "long"],
        "tasks": []
    }

    for _ in range(5):
        task = {
            "meta": {
                "foo": random.randint(0, 100),
                "baz": random.randint(0, 100)
            },
            "text": random_text(random.randint(10, 30))
        }
        job["tasks"].append(task)

    return job


def main(screen: curses.window, path: str):
    job = Job(path)
    job.load()

    gui = GUI(screen, job.labels)
    gui_is_init = False
    keep_task = False
    do_quit = False
    while True:
        if not gui_is_init:
            gui.init()
            gui_is_init = True

        if not keep_task:
            task_index, task = job.next_task()
        gui.update_content(task["text"])
        gui.update_meta(task_index, task)
        key = gui.get_key()
        
        if key == "q":
            status_text = ""
            gui.switch_to_quit_navigation()
            while True:
                key = gui.get_key()
                if key == "y":
                    job.save()
                    do_quit = True
                    break
                elif key == "n":
                    do_quit = True
                    break
                else:
                    gui.update_status(key)
        elif key == "s":
            job.save()
            status_text = f"Saved file {job.path}"
        elif key == "n":
            keep_task = False
            status_text = ""
        elif key == "r":
            task_index, task = job.remove_label(task_index)
            keep_task = True
            status_text = f"Removed label from task {task_index}"
        elif key.isdigit():
            label_index = int(key)-1
            task_index, task = job.add_label(task_index, label_index)
            keep_task = False
            status_text = ""
        elif key == "resize":
            status_text = key
            gui_is_init = False
            keep_task = True
        else:
            status_text = key
            keep_task = True
        gui.update_status(status_text)

        if do_quit:
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Text annotation tool.")
    parser.add_argument("--dummy", action="store_true")
    parser.add_argument("job_path", nargs="?", type=str)
    args = parser.parse_args()
    if args.job_path is None and not args.dummy:
        print("ERROR: No arguments given")
        parser.print_usage()
        raise SystemExit(1)
    elif args.job_path is not None and args.dummy:
        print("ERROR: job_path and --dummy can't be given at the same time")
        raise SystemExit(1)
    elif args.dummy:
        job_json = bootstrap_job()
        with open("./dummy.json", "w") as f:
            json.dump(job_json, f, indent=4)
    else:
        curses.wrapper(main, args.job_path)

    raise SystemExit(0)

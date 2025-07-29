import os
from datetime import date, datetime, timedelta
from collections import Counter
import math
import shutil

HISTORY_FILE = os.path.expanduser("~/.local/share/fish/fish_history")  # This tool only reads fish for now
TOP_N_COMMANDS = 10  # How many most used commands to show

class Command():
    def __init__(self, name):
        self.name = name
        self.count = 0
        self.uses = []
        self.most_recent_use = None
        self.calendar_usage = Counter()
        self.weekly_usage = Counter()
        self.hourly_usage = Counter()
        self.flags = Counter()

    def add_use(self, time, arguments):
        self.count += 1
        self.uses.append([time, arguments])
        self.calendar_usage[time.date()] += 1
        self.weekly_usage[time.weekday()] += 1
        self.hourly_usage[time.hour] += 1
        self.flags += self._get_flags(arguments)
        if self.most_recent_use is None or time > self.most_recent_use:
            self.most_recent_use = time

    def _get_flags(self, argument_list):
        flags = Counter()
        for argument in argument_list:
            if argument[0] == '-' and len(argument) > 1:
                flags[argument] += 1
        return flags

    def get_uses_from_date(self, date, stop_date=None):
        if stop_date is None:
            stop_date = datetime.now()
        new_cmd = Command(self.name)
        for use in self.uses:
            if use[0] >= date and use[0] <= stop_date:
                new_cmd.add_use(use[0], use[1])
        new_cmd.most_recent_use = self.most_recent_use
        return new_cmd

    def get_last_n_uses(self, n_uses):
        self._sort_uses()
        new_cmd = Command(self.name)
        uses = self.uses[-n_uses:]
        for use in uses:
            new_cmd.add_use(*use)
        new_cmd.most_recent_use = self.most_recent_use
        return new_cmd

    def _sort_uses(self):
        self.uses.sort(key = lambda x: x[0])


def get_terminal_dimensions():
    """
    Returns the current terminal size as a named tuple (columns, lines).
    """
    try:
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        # Fallback in case terminal size cannot be determined
        return 80, 24  # Default values

def read_history_file(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()
            print(f"Read {len(lines)} lines from {path}")
            return [line.strip() for line in lines if line.strip()]
    except FileNotFoundError:
        print(f"History file not found: {path}")
        return []

def parse_commands(lines):
    commands = {}
    for line_num, line in enumerate(lines):
        if line.startswith("- cmd: "):  # For fish_history other history files use different formats
            when = datetime.fromtimestamp(int(lines[line_num + 1][6:]))
            full_cmd = line[7:].split()
            cmd = full_cmd[0]
            arguments = full_cmd[1:]
            commands.setdefault(cmd, Command(cmd))
            commands[cmd].add_use(when, arguments)
    return commands

def color_strength(string, strength):
    colors = [
        "\033[38;2;38;38;38m",
        "\033[38;2;45;59;45m",
        "\033[38;2;51;81;52m",
        "\033[38;2;55;104;58m",
        "\033[38;2;57;127;69m",
        "\033[38;2;55;152;69m",
        "\033[38;2;55;176;73m",
        "\033[38;2;49;202;76m",
        "\033[38;2;36;228;79m",
        "\033[38;2;0;255;81m",
    ]
    reset = "\033[0m"
    strength = max(min(1, strength), 0)
    index = math.floor(strength * (len(colors) - 1))
    return colors[index] + string + reset

def analyze_commands(commands, start_datetime, end_datetime=None):
    if end_datetime is None:
        end_datetime = datetime.now()
    kept_commands = {}
    for cmd_name in commands:
        cmd = commands[cmd_name]
        cmd_in_range = cmd.get_uses_from_date(start_datetime, end_datetime)
        if len(cmd_in_range.uses) > 0:
            kept_commands[cmd_in_range.name] = cmd_in_range

    calendar_usage = Counter()
    weekly_usage = Counter()
    hourly_usage = Counter()

    for command in kept_commands:
        cmd = kept_commands[command]
        calendar_usage += cmd.calendar_usage
        weekly_usage += cmd.weekly_usage
        hourly_usage += cmd.hourly_usage

    print_calendar(calendar_usage, start_datetime, end_datetime)
    print_week_usage(weekly_usage)
    print_time_usage(hourly_usage)

    return kept_commands

def print_week_usage(weekly_usage):
    weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
    width, height = get_terminal_dimensions()
    most_frequent = weekly_usage.most_common(1)[0][1]
    for day in range(7):
        commands = weekly_usage[day]
        freq = commands / most_frequent
        cols = round((width * 0.7) - 3)
        bar = '■' * math.floor(cols * freq)
        print(f"{weekdays[day]}: {bar:<{cols}} {commands}")

def print_time_usage(hourly_usage):
    width, height = get_terminal_dimensions()
    most_frequent = hourly_usage.most_common(1)[0][1]
    hours = ["12AM", "1AM", "2AM", "3AM", "4AM", "5AM", "6AM", "7AM", "8AM", "9AM", "10AM", "11AM", "12PM", "1PM", "2PM", "3PM", "4PM", "5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM"]
    for hour in range(24):
        commands = hourly_usage[hour]
        freq = commands / most_frequent
        cols = round((width * 0.7) - 3)
        bar = '■' * math.floor(cols * freq)
        print(f"{hours[hour]:<5}: {bar:<{cols}} {commands}")

def print_calendar(calendar_usage, start_datetime, end_datetime):
    weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
    months = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
    most_busy = calendar_usage.most_common(1)[0][1]
    years = end_datetime.year - start_datetime.year + 1
    for y in range(years):
        year = start_datetime.year + y
        print(f"{year}:")
        days = 366 if year % 4 == 0 else 365;
        year_start = datetime(year, 1, 1)
        year_end = datetime(year, 12, 31)
        offset = year_start.weekday()
        first_row = "  "
        month_index = 0
        columns = math.ceil((days + offset) / 7)
        for week in range(columns):
            last_row = year_start + timedelta(days=(7 + (7 * week) - offset))
            if last_row.month > month_index:
                first_row += months[month_index]
                month_index += 1
            else:
                first_row += ' '
        print(first_row)

        for weekday in range(7):
            row = f"{weekdays[weekday]} "
            for week in range(columns):
                offset_delta = timedelta(days=weekday + (7 * week) - offset)
                day = year_start + offset_delta
                if day < year_start or day > year_end:
                    row += ' ';
                else:
                    row += color_strength('■', calendar_usage[day.date()] / most_busy)
            print(row)
        print(len(calendar_usage.keys()))

def main():
    print(f"Reading history from: {HISTORY_FILE}")
    lines = read_history_file(HISTORY_FILE)
    commands = parse_commands(lines)
    print(f"Found {len(commands)} used commands")
    recent_commands = analyze_commands(commands, datetime(2024, 7, 15))
    used_commands = list(recent_commands.keys())
    used_commands.sort(reverse=True, key = lambda cmd: recent_commands[cmd].count)
    for command in used_commands[:5]:
        cmd = recent_commands[command]
        print(f"{cmd.name}:\t{cmd.count}")
        print_time_usage(cmd.hourly_usage)
    # counter = Counter(commands)

    # print(f"\nTop {TOP_N_COMMANDS} most used commands:")
    # for cmd, count in counter.most_common(TOP_N_COMMANDS):
    #     print(f"{cmd:<15} {count}")

if __name__ == "__main__":
    main()


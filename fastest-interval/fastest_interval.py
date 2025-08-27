#!/opt/homebrew/bin/python3
'''Find the fastest interval of a given length in a Concept2 log CSV file.'''
import csv
import sys

# pylint: disable=redefined-outer-name
def find_fastest_interval(csv_file, target_distance):
    '''Returns position and duration of fastest interval of distance in file.'''
    # Read the CSV file
    with open(csv_file, mode='r', encoding="utf-8") as f:
        reader = csv.reader(f)
        data, header = [], True
        for row in reader:
            if header:
                header = False
                continue
            index = int(row[0])
            time = float(row[1])
            distance = float(row[2])
            data.append((index, time, distance))

    min_time, min_interval = float('inf'), (None, None)
    l = len(data)
    for i in range(l):
        for j in range(i + 1, l):
            distance_diff = data[j][2] - data[i][2]
            if distance_diff >= target_distance:
                time_diff = data[j][1] - data[i][1]
                if time_diff < min_time:
                    min_time = time_diff
                    min_interval = (data[i][2], data[j][2])
                break  # Move to the next starting point once we've found a valid interval
    return min_interval, min_time

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: fastest_interval.py <csv_file> <target_distance>")
        sys.exit(1)

    csv_file = sys.argv[1]
    target_distance = float(sys.argv[2])

    interval, elapsed = find_fastest_interval(csv_file, target_distance)
    if interval[0] is not None:
        pace = elapsed/(interval[1]-interval[0])*500
        pm = int(pace/60)
        ps = pace - pm * 60
        print(f"Fastest interval: {interval[0]:.1f}m - {interval[1]:.1f}m, "
              f"time={elapsed:.1f}s, pace={pm}:{ps:04.1f}")
    else:
        print("No valid interval found.")

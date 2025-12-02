from collections import deque
import json
import csv

class PriorityScheduler:
    """
    Priority Scheduling (non-preemptive).
    - Chooses the ready job with the highest priority (lowest numeric value).
    - Once assigned, job runs CPU burst until completion.
    """

    def __init__(self, num_cpus=1, num_ios=1, verbose=False):
        self.num_cpus = num_cpus
        self.num_ios = num_ios
        self.verbose = verbose

        # Queues
        # Ready processes
        self.ready_queue = deque()
        # Processes waiting for I/O
        self.wait_queue = deque()
        # Currently running processes on each CPU
        self.cpu_queue = [None] * num_cpus
        # Currently running processes on each I/O
        self.io_queue = [None] * num_ios
        # Completed processes
        self.finished = []


        self.clock = 0

    def add_process(self, process):
        """Add process with priority already assigned."""
        process.state = "new"
        process.wait_time = 0
        if not hasattr(process, "priority"):
            process.priority = 5  # default priority
        self.ready_queue.append(process)

    def step(self):
        """Advance one tick."""
        # Activate arrivals
        for p in self.ready_queue:
            if p.state == "new" and p.arrival_time <= self.clock:
                p.state = "ready"

        # Wait time increments
        for p in self.ready_queue:
            if p.state == "ready":
                p.wait_time += 1

        # Process currently running jobs on CPUs
        self._process_cpus()

        # Process currently running jobs on I/O devices
        self._process_io()
        
        # Dispatch ready processes to available CPUs
        self._dispatch_to_cpus()

        # Dispatch waiting processes to available I/O devices
        self._dispatch_to_io()

        self.clock += 1

    def _process_cpus(self):
        """Run CPU bursts, non-preemptive."""
        for i in range(self.num_cpus):
            proc = self.cpu_queue[i]
            if proc:
                # Advance the current burst
                burst_done = proc.advance_burst()
                if burst_done:
                    # Burst completed
                    self.cpu_queue[i] = None

                    if proc.is_complete():
                        # Process is completely finished
                        proc.state = "finished"
                        proc.end_time = self.clock
                        proc.turnaround_time = proc.end_time - proc.arrival_time
                        self.finished.append(proc)
                    else:
                        # Next burst is I/O, move to wait queue
                        proc.state = "waiting"
                        self.wait_queue.append(proc)

    def _process_io(self):
        """Run IO bursts."""
        for i in range(self.num_ios):
            proc = self.io_queue[i]
            if proc:
                # Advance the current I/O burst
                done = proc.advance_burst()
                if done:
                    # I/O burst completed
                    self.io_queue[i] = None

                    if proc.is_complete():
                        # Process is completely finished
                        proc.state = "finished"
                        proc.end_time = self.clock
                        proc.turnaround_time = proc.end_time - proc.arrival_time
                        self.finished.append(proc)
                    else:
                        # Next burst is CPU, move back to ready queue
                        proc.state = "ready"
                        self.ready_queue.append(proc)

    def _dispatch_to_cpus(self):
        """Assign highest-priority ready jobs."""
        ready = [p for p in self.ready_queue if p.state == "ready"]
        ready.sort(key=lambda p: p.priority)

        # Find an available CPU
        for i in range(self.num_cpus):
            if self.cpu_queue[i] is None and ready:
                proc = ready.pop(0)
                self.ready_queue.remove(proc)
                proc.state = "running"
                self.cpu_queue[i] = proc
                break

    def _dispatch_to_io(self):
        """Assign IO-waiting jobs to devices."""

        # Find an available I/O device
        for i in range(self.num_ios):
            if self.io_queue[i] is None and self.wait_queue:
                proc = self.wait_queue.popleft()
                proc.state = "io"
                self.io_queue[i] = proc

    def has_jobs(self):
        """Check if there are any jobs still being processed"""
        return (
            any(self.cpu_queue) or any(self.io_queue)
            or len(self.ready_queue) > 0 or len(self.wait_queue) > 0
        )

    def snapshot(self):
        """Return current state of all queues for visualization"""
        return {
            "clock": self.clock,
            "ready": [p.pid for p in self.ready_queue],
            "wait": [p.pid for p in self.wait_queue],
            "cpu": [p.pid if p else None for p in self.cpu_queue],
            "io": [p.pid if p else None for p in self.io_queue],
            "finished": [p.pid for p in self.finished],
        }

    def print_stats(self):
        """Print completion statistics"""
        if not self.finished:
            print("No processes have completed.")
            return
        
        print("\nPriority Scheduler Statistics:")
        print("-" * 60)
        
        total_turnaround = sum(p.turnaround_time for p in self.finished)
        total_waiting = sum(p.wait_time for p in self.finished)
        
        print(f"{'Process':<8} {'Arrival':<8} {'Completion':<10} {'Turnaround':<10} {'Waiting':<10}")
        print("-" * 60)
        
        for process in self.finished:
            print(f"{process.pid:<8} {process.arrival_time:<8} {process.end_time:<10} "
                  f"{process.turnaround_time:<10} {process.wait_time:<10}")
        
        print("-" * 60)
        print(f"Average Turnaround Time: {total_turnaround/len(self.finished):.2f}")
        print(f"Average Waiting Time:   {total_waiting/len(self.finished):.2f}")
        print(f"Total Context Switches: 0 (FCFS is non-preemptive)")
        print(f"Total Simulation Time: {self.clock}")

    def export_json(self, filename):
        """Export finished processes to JSON file."""
        timeline_data = {
            "algorithm": "Priority",
            "total_time": self.clock,
            "processes": []
        }
        
        for process in self.finished:
            process_data = {
                "pid": process.pid,
                "arrival_time": process.arrival_time,
                "end_time": process.end_time,
                "turnaround_time": process.turnaround_time,
                "wait_time": process.wait_time,
                "priority": process.priority
            }
            timeline_data["processes"].append(process_data)

        with open(filename, 'w') as f:
            json.dump(timeline_data, f, indent=4)

    def export_csv(self, filename):
        """Export simulation results to CSV file"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['pid', 'arrival_time', 'completion_time', 'turnaround_time', 'waiting_time', 'priority']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for process in self.finished:
                writer.writerow({
                    'pid': process.pid,
                    'arrival_time': process.arrival_time,
                    'completion_time': process.end_time,
                    'turnaround_time': process.turnaround_time,
                    'waiting_time': process.wait_time,
                    'priority': process.priority
                })
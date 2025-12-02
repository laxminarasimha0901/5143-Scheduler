# Priority Scheduling Algorithm Implementation
# schedulers/priority.py

from pkg import Scheduler
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
        # Initialize scheduler parameters
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

        # Simulation clock
        #self.clock = 0

    def add_process(self, process):
        """Add process with priority already assigned."""
        # Initialize process state
        process.state = "new"
        # Initialize wait time
        process.wait_time = 0
        # Ensure process has a priority attribute
        if not hasattr(process, "priority"):
            process.priority = 5  # default priority
        self.ready_queue.append(process)

    def step(self):
        """Advance one tick."""
        # Activate new arrivals
        for p in self.ready_queue:
            # If process has arrived, set to ready
            if p.state == "new" and p.arrival_time <= self.clock:
                p.state = "ready"

        # Wait time increments
        for p in self.ready_queue:
            # Only increment wait time for ready processes
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

        # Increment clock
        self.clock += 1

    def _process_cpus(self):
        """Process currently running jobs on all CPUs"""
        # Find an available CPU
        for i in range(self.num_cpus):
            # Get the current process on this CPU
            proc = self.cpu_queue[i]
            if proc:
                # Advance the current burst
                burst_done = proc.advance_burst()
                # If the burst is complete
                if burst_done:
                    # Burst completed
                    self.cpu_queue[i] = None

                    # If process is complete
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
        """Process currently running jobs on all I/O devices"""
        # Find an available I/O device
        for i in range(self.num_ios):
            # Get the current process on this I/O device
            proc = self.io_queue[i]
            # If there is a process on this I/O device
            if proc:
                # Advance the current I/O burst
                done = proc.advance_burst()
                # If the burst is complete
                if done:
                    # I/O burst completed
                    self.io_queue[i] = None

                    # If process is complete
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
        """Dispatch ready processes to available CPUs"""
        # Get list of ready processes sorted by priority
        ready = [p for p in self.ready_queue if p.state == "ready"]
        ready.sort(key=lambda p: p.priority)

        # Find an available CPU
        for i in range(self.num_cpus):
            # Assign highest-priority process to CPU
            if self.cpu_queue[i] is None and ready:
                # Pop highest-priority process
                proc = ready.pop(0)
                # Remove from ready queue
                self.ready_queue.remove(proc)
                # Change state and assign to CPU
                proc.state = "running"
                self.cpu_queue[i] = proc
                break

    def _dispatch_to_io(self):
        """Dispatch waiting processes to available I/O devices"""
        # Find an available I/O device
        for i in range(self.num_ios):
            # Assign next waiting process to I/O device
            if self.io_queue[i] is None and self.wait_queue:
                # Pop next waiting process
                proc = self.wait_queue.popleft()
                proc.state = "io_waiting"
                self.io_queue[i] = proc

    def has_jobs(self):
        """Check if there are any jobs still being processed"""
        # Returns True if there are jobs in any queue or running on CPUs/IOs
        return (
            any(self.cpu_queue) or any(self.io_queue)
            or len(self.ready_queue) > 0 or len(self.wait_queue) > 0
        )

    def snapshot(self):
        """Return current state of all queues for visualization"""
        # Returns a dictionary with the current state of the scheduler
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
        # If no processes have finished, print a message and return
        if not self.finished:
            print("No processes have completed.")
            return
        
        # Print header
        print("\nPriority Scheduler Statistics:")
        print("-" * 60)
        
        # Calculate totals for averages
        total_turnaround = sum(p.turnaround_time for p in self.finished)
        total_waiting = sum(p.wait_time for p in self.finished)
        
        # Print table header
        print(f"{'Process':<8} {'Arrival':<8} {'Completion':<10} {'Turnaround':<10} {'Waiting':<10}")
        print("-" * 60)
        
        # Print each process's stats
        for process in self.finished:
            print(f"{process.pid:<8} {process.arrival_time:<8} {process.end_time:<10} "
                  f"{process.turnaround_time:<10} {process.wait_time:<10}")
        
        # Print averages
        print("-" * 60)
        print(f"Average Turnaround Time: {total_turnaround/len(self.finished):.2f}")
        print(f"Average Waiting Time:   {total_waiting/len(self.finished):.2f}")
        print(f"Total Context Switches: 0")
        print(f"Total Simulation Time: {self.clock}")

    def export_json(self, filename):
        """Export simulation timeline to JSON file."""
        # Prepare timeline data
        timeline_data = {
            "algorithm": "Priority",
            "total_time": self.clock,
            "processes": []
        }
        
        # Add each finished process's data
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

        # Write to JSON file
        with open(filename, 'w') as f:
            json.dump(timeline_data, f, indent=4)

    def export_csv(self, filename):
        """Export simulation results to CSV file"""
        # Export simulation results to CSV file
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['pid', 'arrival_time', 'completion_time', 'turnaround_time', 'waiting_time', 'priority']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()

            # Write each finished process's data to CSV
            for process in self.finished:
                writer.writerow({
                    'pid': process.pid,
                    'arrival_time': process.arrival_time,
                    'completion_time': process.end_time,
                    'turnaround_time': process.turnaround_time,
                    'waiting_time': process.wait_time,
                    'priority': process.priority
                })
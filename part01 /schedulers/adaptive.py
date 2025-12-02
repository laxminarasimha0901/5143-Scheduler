from collections import deque

class AdaptiveScheduler:
    """
    Adaptive Priority Scheduler.
    - Uses dynamic priority adjustment (aging).
    - Every tick that a job waits => priority improves by 1.
    - Prevents starvation, adapts to workload.
    """

    def __init__(self, num_cpus=1, num_ios=1, verbose=False, aging_rate=1):
        self.num_cpus = num_cpus
        self.num_ios = num_ios
        self.verbose = verbose
        self.aging_rate = aging_rate

        self.ready_queue = deque()
        self.wait_queue = deque()

        self.cpu_queue = [None] * num_cpus
        self.io_queue = [None] * num_ios

        self.finished = []
        self.clock = 0

    def add_process(self, process):
        """Add process with initial priority."""
        process.state = "new"
        process.wait_time = 0
        if not hasattr(process, "priority"):
            process.priority = 10  # default starting priority
        self.ready_queue.append(process)

    def step(self):
        """Advance time by one tick."""
        # Activate new arrivals
        for p in self.ready_queue:
            if p.state == "new" and p.arrival_time <= self.clock:
                p.state = "ready"

        # Aging: ready processes get higher priority the longer they wait
        for p in self.ready_queue:
            if p.state == "ready":
                p.wait_time += 1
                p.priority = max(1, p.priority - self.aging_rate)

        # CPU and IO progress
        self._process_cpus()
        self._process_io()

        # Dispatch
        self._dispatch_to_cpus()
        self._dispatch_to_io()

        self.clock += 1

    def _process_cpus(self):
        """Advance CPU bursts."""
        for i in range(self.num_cpus):
            proc = self.cpu_queue[i]
            if proc:
                done = proc.advance_burst()
                if done:
                    self.cpu_queue[i] = None
                    if proc.is_complete():
                        proc.state = "finished"
                        proc.end_time = self.clock
                        proc.turnaround_time = proc.end_time - proc.arrival_time
                        self.finished.append(proc)
                    else:
                        proc.state = "waiting"
                        self.wait_queue.append(proc)

    def _process_io(self):
        """Advance IO bursts."""
        for i in range(self.num_ios):
            proc = self.io_queue[i]
            if proc:
                done = proc.advance_burst()
                if done:
                    self.io_queue[i] = None
                    if proc.is_complete():
                        proc.state = "finished"
                        proc.end_time = self.clock
                        proc.turnaround_time = proc.end_time - proc.arrival_time
                        self.finished.append(proc)
                    else:
                        proc.state = "ready"
                        self.ready_queue.append(proc)

    def _dispatch_to_cpus(self):
        """Select highest aged priority."""
        ready = [p for p in self.ready_queue if p.state == "ready"]
        ready.sort(key=lambda p: p.priority)  # smaller = higher priority

        for i in range(self.num_cpus):
            if self.cpu_queue[i] is None and ready:
                proc = ready.pop(0)
                self.ready_queue.remove(proc)
                proc.state = "running"
                self.cpu_queue[i] = proc

    def _dispatch_to_io(self):
        """Fill IO devices."""
        for i in range(self.num_ios):
            if self.io_queue[i] is None and self.wait_queue:
                proc = self.wait_queue.popleft()
                proc.state = "io"
                self.io_queue[i] = proc

    def has_jobs(self):
        return (
            any(self.cpu_queue) or any(self.io_queue)
            or len(self.ready_queue) > 0 or len(self.wait_queue) > 0
        )

    def snapshot(self):
        return {
            "clock": self.clock,
            "ready": [[p.pid, p.priority] for p in self.ready_queue],
            "wait": [p.pid for p in self.wait_queue],
            "cpu": [p.pid if p else None for p in self.cpu_queue],
            "io": [p.pid if p else None for p in self.io_queue],
            "finished": [p.pid for p in self.finished]
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


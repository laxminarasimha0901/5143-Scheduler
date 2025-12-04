# This is Dr. Griffin's version (I think) of scheduler.py.
from pkg.clock import Clock
from pkg.cpu import CPU
from pkg.iodevice import IODevice
import collections
import csv
import json


class Scheduler:
    """
    A simple CPU and I/O scheduler

    Attributes:
        clock: shared Clock instance
        ready_queue: deque of processes ready for CPU
        wait_queue: deque of processes waiting for I/O
        cpus: list of CPU instances
        io_devices: list of IODevice instances
        finished: list of completed processes
        log: human-readable log of events
        events: structured log of events for export
        verbose: if True, print log entries to console
    Methods:
        add_process(process): add a new process to the ready queue
        step(): advance the scheduler by one time unit
        run(): run the scheduler until all processes are finished
        timeline(): return the human-readable log as a string
        export_json(filename): export the structured log to a JSON file
        export_csv(filename): export the structured log to a CSV file"""

    def __init__(self, num_cpus=1, num_ios=1, verbose=True):

        self.clock = Clock()  # shared clock instance for all components Borg pattern

        # deque (double ended queue) for efficient pops from left
        self.ready_queue = collections.deque()

        # deque (double ended queue) for efficient pops from left
        self.wait_queue = collections.deque()

        # uses a list comprehension to create a list of CPU objects
        self.cpus = [CPU(cid=i, clock=self.clock) for i in range(num_cpus)]

        # uses a list comprehension to create a list of IODevice objects
        self.io_devices = [IODevice(did=i, clock=self.clock) for i in range(num_ios)]

        self.finished = []  # list of finished processes
        self.log = []  # human-readable + snapshots
        self.events = []  # structured log for export
        self.verbose = verbose  # if True, print log entries to console

    def on_state_change(self, callback):
        """Register a callback for state changes (e.g., for the View)."""
        self._callback = callback

    def add_process(self, process):
        """
        Add a new process to the ready queue
        Args:
            process: Process instance to add
        Returns: None
        """

        process.state = "ready"  # sets the current process state to ready
        
        # Set start_time to arrival_time if not already set
        if process.start_time == 0:
            process.start_time = process.arrival_time
        
        # Track first time entering ready queue (for wait time calculation)
        if not hasattr(process, 'first_ready_time'):
            process.first_ready_time = self.clock.now()

        # adds the process to the end of the ready queue
        self.ready_queue.append(process)

        # Log the event
        self._record(
            f"{process.pid} added to ready queue",
            event_type="enqueue",
            proc=process.pid,
        )

    def processes(self):
        """Return all processes known to the scheduler"""
        all = (
            list(self.ready_queue)
            + list(self.wait_queue)
            + self.finished
            + [cpu.current for cpu in self.cpus if cpu.current]
            + [dev.current for dev in self.io_devices if dev.current]
        )
        rdict = {p.pid: p for p in all}
        return rdict

    def _record(self, event, event_type="info", proc=None, device=None):
        """
        Record an event in the log and structured events list
        Args:
            event: description of the event
            event_type: type/category of the event (e.g., "dispatch", "enqueue", etc.)
            proc: process ID involved in the event (if any)
            device: device ID involved in the event (if any)
        Returns: None
        """
        entry = f"time={self.clock.now():<3} | {event}"
        self.log.append(entry)

        # Print to console if verbose
        if self.verbose:
            print(entry)

        # structured record for export as JSON/CSV
        self.events.append(
            {
                "time": self.clock.now(),
                "event": event,
                "event_type": event_type,
                "process": proc,
                "device": device,
                "ready_queue": [p.pid for p in self.ready_queue],
                "wait_queue": [p.pid for p in self.wait_queue],
                "cpus": [cpu.current.pid if cpu.current else None for cpu in self.cpus],
                "ios": [
                    dev.current.pid if dev.current else None for dev in self.io_devices
                ],
            }
        )

    def _snapshot(self):
        """Take a snapshot of the current state for logging"""
        # The join method is used to concatenate the process IDs in
        # the ready queue into a single string, separated by commas.
        # If the ready queue is empty, it defaults to the string "empty".
        rq = ", ".join([p.pid for p in self.ready_queue]) or "empty"
        # Same as above but for the wait queue
        wq = ", ".join([p.pid for p in self.wait_queue]) or "empty"
        # Join the status of each CPU and IO device into strings separated by " | "
        cpus = " | ".join([str(cpu) for cpu in self.cpus])
        # Same as above but for IO devices
        ios = " | ".join([str(dev) for dev in self.io_devices])
        # Creates a string snapshot of the current state of
        # the scheduler including ready queue, wait queue, CPUs, and IO devices
        snap = f"  [Ready: {rq}]  [Wait: {wq}]  Cpus:[{cpus}]  Ios:[{ios}]"
        # Append the snapshot to the log
        self.log.append(snap)
        if self.verbose:
            print(snap)

    # snapshot method strictly for the visualizer portion
    def snapshot(self):
        """Return current state for the visualizer"""
        return {
        'clock': self.clock.time,
        'ready_queue': [p.pid for p in self.ready_queue],
        'wait_queue': [p.pid for p in self.wait_queue],
        'cpu': [cpu.current.pid if cpu.current else None for cpu in self.cpus],
        'ios': [dev.current.pid if dev.current else None for dev in self.io_devices]
    }

    def _callback(self, pid, new_state):
        """Placeholder for state change callback"""
        pass

    def step(self):
        """
        Advance the scheduler by one time unit
        Returns: None
        """
        for p in self.ready_queue:
            p.wait_time += 1  # Increment wait time for processes in ready queue
        for p in self.wait_queue:
            p.io_time += 1  # Increment I/O time for processes in wait queue

        # Iterate over each CPU and tick (decrement burst time) by 1 if not idle
        for cpu in self.cpus:

            # proc is the process that just finished its CPU burst or None
            proc = cpu.tick()

            # If a process finished its CPU burst, handle it.
            # This means that proc is not None
            if proc:
                burst = proc.current_burst()

                # If the next burst is I/O, move to wait queue
                # If no more bursts, move to finished
                # If next burst is CPU, move to ready queue
                if burst and "io" in burst:
                    proc.state = "waiting"
                    self.wait_queue.append(proc)
                    # if self._callback:
                    #     self._callback(proc.pid, "waiting")
                    self._record(
                        f"{proc.pid} finished CPU → wait queue",
                        event_type="cpu_to_io",
                        proc=proc.pid,
                        device=f"CPU{cpu.cid}",
                    )

                # If the next burst is CPU, move to ready queue
                elif burst and "cpu" in burst:
                    self.ready_queue.append(proc)
                    # if self._callback:
                    #     self._callback(proc.pid, "ready")

                    # logs event of moving process to ready queue
                    self._record(
                        f"{proc.pid} finished CPU → ready queue",
                        event_type="cpu_to_ready",
                        proc=proc.pid,
                        device=f"CPU{cpu.cid}",
                    )
                # No more bursts, process is finished
                else:
                    proc.state = "finished"
                    proc.end_time = self.clock.now()
                    proc.turnaround_time = proc.end_time - proc.start_time
                    self.finished.append(proc)

                    # if self._callback:
                    #     self._callback(proc.pid, "finished")

                    # logs event of process finishing all bursts
                    self._record(
                        f"{proc.pid} finished all bursts",
                        event_type="finished",
                        proc=proc.pid,
                        device=f"CPU{cpu.cid}",
                    )

        # Tick IO devices
        for dev in self.io_devices:
            proc = dev.tick()
            if proc:
                burst = proc.current_burst()

                # If the next burst is I/O, move to wait queue
                # If no more bursts, move to finished
                # If next burst is CPU, move to ready queue
                if burst:
                    proc.state = "ready"
                    self.ready_queue.append(proc)
                    if self._callback:
                        self._callback(proc.pid, "ready")

                    # logs event of moving process to ready queue
                    self._record(
                        f"{proc.pid} finished I/O → ready queue",
                        event_type="io_to_ready",
                        proc=proc.pid,
                        device=f"IO{dev.did}",
                    )
                # else process is finished
                else:
                    proc.state = "finished"

                    proc.end_time = self.clock.now()
                    proc.turnaround_time = proc.end_time - proc.start_time
                    self.finished.append(proc)
                    if self._callback:
                        self._callback(proc.pid, "finished")

                    # logs event of process finishing all bursts
                    self._record(
                        f"{proc.pid} finished all bursts",
                        event_type="finished",
                        proc=proc.pid,
                        device=f"IO{dev.did}",
                    )

        # Dispatch to CPUs
        for cpu in self.cpus:

            # If CPU is free and there's a process in ready queue
            if not cpu.is_busy() and self.ready_queue:

                # Pop process from left of ready queue
                proc = self.ready_queue.popleft()
                
                # Track first dispatch time (when process first gets CPU)
                if not hasattr(proc, 'first_dispatch_time'):
                    proc.first_dispatch_time = self.clock.now()

                # Assign process to CPU
                cpu.assign(proc)

                # Log the dispatch event
                self._record(
                    f"{proc.pid} dispatched to CPU{cpu.cid}",
                    event_type="dispatch_cpu",
                    proc=proc.pid,
                    device=f"CPU{cpu.cid}",
                )

        # Dispatch to IO devices
        # Same logic as above but for IO devices and wait queue
        for dev in self.io_devices:
            if not dev.is_busy() and self.wait_queue:
                proc = self.wait_queue.popleft()
                dev.assign(proc)
                self._record(
                    f"{proc.pid} dispatched to IO{dev.did}",
                    event_type="dispatch_io",
                    proc=proc.pid,
                    device=f"IO{dev.did}",
                )

        if self.verbose:
            self._snapshot()
        self.clock.tick()
    
    def has_jobs(self):
        """Check if there are any jobs left to process (for visualizer compatibility)"""
        return (
            self.ready_queue
            or self.wait_queue
            or any(cpu.is_busy() for cpu in self.cpus)
            or any(dev.is_busy() for dev in self.io_devices)
        )

    def run(self):
        """
        Run the scheduler until all processes are finished
        Returns: None
        """

        # Continue stepping while there are processes in ready/wait queues
        # or any CPU/IO device is busy
        while self.has_jobs():
            self.step()

    def timeline(self):
        """Return the human-readable log as a single string"""
        return "\n".join(self.log)

    # ---- Exporters ----
    def export_json(self, filename="timeline.json"):
        """Export the timeline to a JSON file"""
        with open(filename, "w") as f:
            json.dump(self.events, f, indent=2)
        if self.verbose:
            print(f"✅ Timeline exported to {filename}")

    def export_csv(self, filename="timeline.csv"):
        """Export the timeline to a CSV file"""

        # If there are no events, do nothing
        if not self.events:
            return

        # Write CSV using DictWriter for structured data
        # .keys() returns a list of all the keys in a dictionary.
        keys = self.events[0].keys()

        # Open the file in write mode with newline='' to prevent extra blank lines on Windows
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.events)
        if self.verbose:
            print(f"✅ Timeline exported to {filename}")

    def print_stats(self):
        """Print statistics for all finished processes"""
        if not self.finished:
            print("\nNo processes have completed yet.")
            return
            
        print("\n" + "="*80)
        print("PROCESS STATISTICS")
        print("="*80)
        
        # Calculate totals for averages
        total_wait_time = 0
        total_turnaround_time = 0
        total_response_time = 0
        
        raw_data = []
        for p in self.finished:
            # FIX: Use the accumulated wait_time from the step() function
            actual_wait_time = p.wait_time
            
            # Turnaround time = completion - arrival
            turnaround_time = p.end_time - p.arrival_time
            
            # Response time = Time from arrival until FIRST CPU touch
            # If we missed capturing first_dispatch_time, assume it was immediate (wait_time)
            if hasattr(p, 'first_dispatch_time'):
                response_time = p.first_dispatch_time - p.arrival_time
            else:
                response_time = actual_wait_time
            
            total_wait_time += actual_wait_time
            total_turnaround_time += turnaround_time
            total_response_time += response_time
            
            raw_data.append(
                f"[{p.pid}: Arrival={p.arrival_time} FirstCPU={getattr(p, 'first_dispatch_time', '?')} Wait={actual_wait_time}, Turnaround={turnaround_time}, Response={response_time}, Run={p.runtime}, I/O={p.io_time}, InitCpuBurst={p.init_cpu_bursts}, InitIoBurst={p.init_io_bursts}, TotalBursts={p.TotalBursts}]"
            )
        
        # Calculate averages
        num_processes = len(self.finished)
        avg_wait_time = total_wait_time / num_processes
        avg_turnaround_time = total_turnaround_time / num_processes
        avg_response_time = total_response_time / num_processes
        
        try:
            from rich.console import Console
            from rich.table import Table
            import re

            # Parse function
            def parse_job(job_str):
                job_str = job_str.strip("[]")
                job_id, rest = job_str.split(":", 1)
                job_id = job_id.strip()
                pairs = re.findall(r"(\w+/?.*?)=([\d]+)", rest)
                return {"ID": job_id, **{k: v for k, v in pairs}}

            # Convert to list of dicts
            jobs = [parse_job(entry) for entry in raw_data]

            # Build Rich table
            table = Table(title="Process Details")
            for col in jobs[0].keys():
                table.add_column(col, justify="center")

            for job in jobs:
                table.add_row(*[str(job[col]) for col in job])

            # Print it
            console = Console()
            console.print(table)
            
        except ImportError:
            # Fallback if rich is not available
            print("\nProcess Details:")
            for entry in raw_data:
                print(f"  {entry}")
        
        # Print summary statistics
        print("\n" + "-"*80)
        print("SUMMARY STATISTICS")
        print("-"*80)
        print(f"Total Processes Completed:  {num_processes}")
        print(f"Total Simulation Time:      {self.clock.now()}")
        print(f"\nAverage Wait Time:          {avg_wait_time:.2f}")
        print(f"Average Turnaround Time:    {avg_turnaround_time:.2f}")
        print(f"Average Response Time:      {avg_response_time:.2f}")
        print("="*80 + "\n")